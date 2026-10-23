"""Author simulation overrides as a separate USD layer, preserving importer output."""
import argparse,json,math
import numpy as np
from scipy.spatial.transform import Rotation
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics,UsdShade,Sdf,Gf


def configure(folder,config):
    folder=Path(folder).resolve(); entry=folder/'r1pro_2026.usd'; imported=folder/'imported.usd'
    if not imported.exists(): entry.rename(imported)
    # Rebuild only generated overrides; no vendor files are edited.
    physics=Usd.Stage.CreateNew(str(folder/'physics.usda')) if not (folder/'physics.usda').exists() else Usd.Stage.Open(str(folder/'physics.usda'))
    physics.GetRootLayer().Clear(); physics.GetRootLayer().Save()
    stage=Usd.Stage.CreateNew(str(entry)) if not entry.exists() else Usd.Stage.Open(str(entry))
    stage.GetRootLayer().Clear(); stage.GetRootLayer().subLayerPaths=(['appearance.usdc'] if (folder/'appearance.usdc').exists() else [])+['physics.usda','imported.usd']
    raw=Usd.Stage.Open(str(imported)); root_path=raw.GetDefaultPrim().GetPath()
    stage.SetDefaultPrim(stage.GetPrimAtPath(root_path)); UsdGeom.SetStageMetersPerUnit(stage,1); UsdGeom.SetStageUpAxis(stage,'Z')
    root=stage.GetPrimAtPath(root_path)
    for name in root.GetVariantSets().GetNames():
        variants=root.GetVariantSet(name)
        for value in variants.GetVariantNames():
            if value.lower()=='physx': variants.SetVariantSelection(value)
    stage.SetEditTarget(physics.GetRootLayer())
    material=UsdShade.Material.Define(stage,str(root_path)+'/Looks/ContactMaterial')
    mat=UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    for k,v in [('StaticFriction','static_friction'),('DynamicFriction','dynamic_friction'),('Restitution','restitution')]:
        getattr(mat,'Create'+k+'Attr')().Set(config['contact_material'][v])
    joint_paths={}; bodies=[]
    def attr(p,name,typ,val): p.CreateAttribute(name,typ,custom=False).Set(val)
    for p in list(stage.Traverse()):
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            bodies.append(str(p.GetPath()))
            data=config['links'][p.GetName()]
            eigenvalues,eigenvectors=np.linalg.eigh(np.array(data['inertia']))
            if np.linalg.det(eigenvectors)<0:eigenvectors[:,0]*=-1
            source_rotation=Rotation.from_euler('xyz',np.fromstring(data['origin'].get('rpy','0 0 0'),sep=' ')).as_matrix()
            q=Rotation.from_matrix(source_rotation@eigenvectors).as_quat()
            mass=UsdPhysics.MassAPI.Apply(p)
            mass.CreateMassAttr(float(data['mass_kg']))
            mass.CreateCenterOfMassAttr(Gf.Vec3f(*np.fromstring(data['origin'].get('xyz','0 0 0'),sep=' ')))
            mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*eigenvalues))
            mass.CreatePrincipalAxesAttr(Gf.Quatf(float(q[3]),Gf.Vec3f(*q[:3])))
            UsdShade.MaterialBindingAPI.Apply(p).Bind(material,materialPurpose='physics')
        if p.HasAPI(UsdPhysics.ArticulationRootAPI):
            p.AddAppliedSchema('PhysxArticulationAPI')
            attr(p,'physxArticulation:solverPositionIterationCount',Sdf.ValueTypeNames.Int,32)
            attr(p,'physxArticulation:solverVelocityIterationCount',Sdf.ValueTypeNames.Int,8)
            attr(p,'physxArticulation:enabledSelfCollisions',Sdf.ValueTypeNames.Bool,config['self_collision'])
        if p.GetName() not in config['joints'] or not p.IsA(UsdPhysics.Joint): continue
        j=config['joints'][p.GetName()]; linear=j['type']=='prismatic'; key='linear' if linear else 'angular'
        drive=UsdPhysics.DriveAPI.Apply(p,key)
        drive.CreateTypeAttr('force'); drive.CreateStiffnessAttr(j['stiffness']); drive.CreateDampingAttr(j['damping'])
        drive.CreateMaxForceAttr(j['max_force']); drive.CreateTargetPositionAttr(0); drive.CreateTargetVelocityAttr(0)
        p.AddAppliedSchema('PhysxJointAPI')
        attr(p,'physxJoint:maxJointVelocity',Sdf.ValueTypeNames.Float,j['max_velocity'] if linear else math.degrees(j['max_velocity']))
        joint_paths[p.GetName()]=str(p.GetPath())
    assert set(joint_paths)==set(config['joints'])
    physics.GetRootLayer().Save(); stage.GetRootLayer().Save()
    report={'root':str(root_path),'joints':joint_paths,'bodies':bodies,'config':config}
    (folder/'asset_configuration.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--config',type=Path,default=Path('configs/r1pro_2026_common.json'))
    a=ap.parse_args();r=configure(a.folder,json.loads(a.config.read_text()));print('CONFIGURED',r['root'],len(r['joints']))
