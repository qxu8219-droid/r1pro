"""Conservative vendor UV transfer by matching triangles in link-local coordinates.
Unmatched geometry receives explicitly labelled neutral reference styling.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf,Vt,UsdPhysics


def match_triangle_uv(source_triangles,source_uv,target_triangles,tolerance=1e-6):
    lookup={}
    def corners(tri):return [tuple(v) for v in np.rint(tri/tolerance).astype(np.int64)]
    for tri,uv in zip(source_triangles,source_uv):
        pts=corners(tri);key=tuple(sorted(pts))
        if len(set(pts))<3:lookup[key]=None;continue
        mapping=dict(zip(pts,uv))
        if key in lookup:
            old=lookup[key]
            if old is None or any(not np.allclose(old[k],mapping[k],atol=1e-5) for k in pts):lookup[key]=None
        else:lookup[key]=mapping
    mapped=np.tile(np.array([.75,.5]),(len(target_triangles),3,1));valid=np.zeros(len(target_triangles),bool)
    for i,tri in enumerate(target_triangles):
        pts=corners(tri);mapping=lookup.get(tuple(sorted(pts)))
        if mapping is not None:
            mapped[i]=[mapping[k] for k in pts];valid[i]=True
    return mapped,valid


def mesh_triangles(mesh,link):
    points=np.asarray(mesh.GetPointsAttr().Get(),dtype=float)
    cache=UsdGeom.XformCache();matrix=cache.GetLocalToWorldTransform(mesh.GetPrim())*cache.GetLocalToWorldTransform(link).GetInverse()
    transformed=np.c_[points,np.ones(len(points))]@np.asarray(matrix)
    counts=np.asarray(mesh.GetFaceVertexCountsAttr().Get());assert np.all(counts==3),'Only triangular vendor meshes supported'
    indices=np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1,3)
    return transformed[:,:3][indices]


def material(stage,path,texture=False,color=(.15,.15,.17)):
    mat=UsdShade.Material.Define(stage,path)
    surf=UsdShade.Shader.Define(stage,path+'/Surface');surf.CreateIdAttr('UsdPreviewSurface')
    surf.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    surf.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(0)
    surf.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.5)
    mat.CreateSurfaceOutput().ConnectToSource(surf.ConnectableAPI(),'surface')
    if texture:
        reader=UsdShade.Shader.Define(stage,path+'/UV');reader.CreateIdAttr('UsdPrimvarReader_float2');reader.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
        tex=UsdShade.Shader.Define(stage,path+'/Texture');tex.CreateIdAttr('UsdUVTexture')
        tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('textures/output.jpg'))
        tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
        tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),'result')
        surf.GetInput('diffuseColor').ConnectToSource(tex.ConnectableAPI(),'rgb')
    return mat


def apply(folder,source):
    folder=Path(folder).resolve();source=Path(source).resolve();selection=json.loads((source/'SELECTED_MODEL.json').read_text())
    donor=Usd.Stage.Open(str(source/selection['appearance_donor']));stage=Usd.Stage.Open(str(folder/'r1pro_2026.usd'))
    root=stage.GetDefaultPrim();donor_root=donor.GetDefaultPrim()
    out=folder/'appearance.usdc'
    layer=Sdf.Layer.FindOrOpen(str(out)) if out.exists() else Sdf.Layer.CreateNew(str(out))
    layer.Clear()
    sub=[x for x in stage.GetRootLayer().subLayerPaths if x!='appearance.usdc']
    stage.GetRootLayer().subLayerPaths=['appearance.usdc']+sub;stage.SetEditTarget(layer)
    texmat=material(stage,str(root.GetPath())+'/Looks/FactoryTexture',True)
    neutral=material(stage,str(root.GetPath())+'/Looks/ReferenceNeutral')
    dark=material(stage,str(root.GetPath())+'/Looks/ReferenceDark',color=(.025,.025,.03))
    (folder/'textures').mkdir(exist_ok=True);shutil.copyfile(source/selection['appearance_texture'],folder/'textures/output.jpg')
    report=[]
    # Only visual instance roots are de-instanced; physics/collision data remains intact.
    for link in [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]:
        visual_containers=[]
        for child in link.GetChildren():
            if child.HasAPI(UsdPhysics.RigidBodyAPI): continue
            candidate=[p for p in Usd.PrimRange(child,Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh)]
            if not candidate: continue
            if all(p.HasAPI(UsdPhysics.CollisionAPI) for p in candidate):
                UsdGeom.Imageable(child).CreatePurposeAttr('guide')
                continue
            if any(p.HasAPI(UsdPhysics.CollisionAPI) for p in candidate):
                raise ValueError(f'Mixed visual/collision subtree: {child.GetPath()}')
            visual_containers.append(child)
            # Iteratively reveal nested instance children before authoring UVs.
            while True:
                instances=[p for p in Usd.PrimRange(child) if p.IsInstance()]
                if not instances:break
                for p in instances:p.SetInstanceable(False)
        meshes=[UsdGeom.Mesh(p) for vis in visual_containers for p in Usd.PrimRange(vis) if p.IsA(UsdGeom.Mesh)]
        src_link=donor_root.GetChild(link.GetName());src_vis=src_link.GetChild('visuals') if src_link else None
        src_meshes=[UsdGeom.Mesh(p) for p in Usd.PrimRange(src_vis) if p.IsA(UsdGeom.Mesh)] if src_vis else []
        for target in meshes:
            info={'link':link.GetName(),'mesh':str(target.GetPath()),'mode':'reference_style_fallback'}
            chosen=dark if ('wheel' in link.GetName() or link.GetName()=='base_link' or 'camera' in link.GetName()) else neutral
            if len(src_meshes)==1:
                src=src_meshes[0];uv=UsdGeom.PrimvarsAPI(src).GetPrimvar('st')
                bound=UsdShade.MaterialBindingAPI(src).ComputeBoundMaterial()[0]
                files=[a.Get() for p in Usd.PrimRange(bound.GetPrim()) for a in p.GetAttributes() if a.GetTypeName()==Sdf.ValueTypeNames.Asset] if bound else []
                supported=any(x and Path(x.path.replace('\\','/')).name=='output.jpg' for x in files)
                if uv and uv.HasValue() and uv.GetInterpolation()=='faceVarying' and supported:
                    tri=mesh_triangles(src,src_link);uvs=np.asarray(uv.ComputeFlattened()).reshape(-1,3,2)
                    mapped,valid=match_triangle_uv(tri,uvs,mesh_triangles(target,link))
                    info.update(matched_faces=int(valid.sum()),total_faces=len(valid),matched_fraction=float(valid.mean()))
                    if valid.mean()>=.98:
                        primvar=UsdGeom.PrimvarsAPI(target).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'faceVarying')
                        primvar.Set(Vt.Vec2fArray.FromNumpy(mapped.reshape(-1,2).astype(np.float32)));primvar.BlockIndices()
                        chosen=texmat;info['mode']='matched_uv' if valid.all() else 'matched_uv_with_explicit_face_fallback'
                    else:info['reason']='geometry match below 98%; neutral styling retained'
                else:info['reason']='missing valid face-corner UV or confirmed output.jpg material'
            else:info['reason']='no unique donor mesh for this link'
            container=next(v for v in visual_containers if target.GetPath().HasPrefix(v.GetPath()))
            UsdShade.MaterialBindingAPI.Apply(container).Bind(chosen,bindingStrength=UsdShade.Tokens.strongerThanDescendants)
            UsdShade.MaterialBindingAPI.Apply(target.GetPrim()).Bind(chosen,bindingStrength=UsdShade.Tokens.strongerThanDescendants)
            report.append(info)
    layer.Save();stage.GetRootLayer().Save()
    (folder/'appearance_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({mode:sum(x['mode']==mode for x in report) for mode in sorted({x['mode'] for x in report})}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--source',required=True,type=Path)
    a=ap.parse_args();apply(a.folder,a.source)
