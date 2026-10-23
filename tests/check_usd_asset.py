"""Integration gate for exported robot; accepts an entry USD and source audit."""
import argparse,json,math
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics,UsdUtils,UsdShade,Gf
import numpy as np
from scipy.spatial.transform import Rotation

def check(asset,audit):
    assert asset.is_file(),f'Asset not generated: {asset}'
    stage=Usd.Stage.Open(str(asset)); assert stage
    assert stage.GetDefaultPrim(), 'missing defaultPrim'
    assert UsdGeom.GetStageMetersPerUnit(stage)==1
    assert UsdGeom.GetStageUpAxis(stage)=='Z'
    prims=list(stage.Traverse())
    roots=[str(p.GetPath()) for p in prims if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
    assert len(roots)==1,roots
    bodies={p.GetName():p for p in prims if p.HasAPI(UsdPhysics.RigidBodyAPI)}
    assert set(bodies)=={x['name'] for x in audit['links']},'link/body mapping mismatch'
    poses={'base_link':np.eye(4)}; pending=list(audit['joints'])
    while pending:
        ready=[j for j in pending if j['parent'] in poses]
        assert ready,'invalid source topology'
        for j in ready:
            T=np.eye(4);T[:3,3]=np.fromstring(j['origin'].get('xyz','0 0 0'),sep=' ')
            T[:3,:3]=Rotation.from_euler('xyz',np.fromstring(j['origin'].get('rpy','0 0 0'),sep=' ')).as_matrix()
            poses[j['child']]=poses[j['parent']]@T;pending.remove(j)
    cache=UsdGeom.XformCache();max_frame_error=0
    for link in audit['links']:
        p=bodies[link['name']];mass=UsdPhysics.MassAPI(p)
        assert np.isclose(mass.GetMassAttr().Get(),link['mass_kg'],rtol=1e-5),link['name']
        expected_com=np.fromstring(link['origin'].get('xyz','0 0 0'),sep=' ')
        assert np.allclose(mass.GetCenterOfMassAttr().Get(),expected_com,rtol=1e-5,atol=1e-7),(link['name'],'COM mismatch')
        actual=np.asarray(cache.GetLocalToWorldTransform(p)).T
        error=float(np.max(abs(actual-poses[link['name']])))
        max_frame_error=max(max_frame_error,error);assert error<1e-5,(link['name'],error)
        diagonal=np.array(mass.GetDiagonalInertiaAttr().Get());q=mass.GetPrincipalAxesAttr().Get()
        rot=np.asarray(Gf.Matrix3d(Gf.Rotation(q))).T
        inertia=rot@np.diag(diagonal)@rot.T
        expected=np.array(link['inertia'])
        inertia_rot=Rotation.from_euler('xyz',np.fromstring(link['origin'].get('rpy','0 0 0'),sep=' ')).as_matrix()
        expected=inertia_rot@expected@inertia_rot.T
        assert np.allclose(inertia,expected,rtol=1e-4,atol=1e-7),(link['name'],'inertia mismatch')
    all_joints={p.GetName():p for p in prims if p.IsA(UsdPhysics.Joint)}
    assert set(all_joints)=={j['name'] for j in audit['joints']},'joint topology mismatch'
    for j in audit['joints']:
        joint=UsdPhysics.Joint(all_joints[j['name']])
        for side,link in [('body0','parent'),('body1','child')]:
            targets=joint.GetPrim().GetRelationship('physics:'+side).GetTargets()
            assert len(targets)==1 and targets[0]==bodies[j[link]].GetPath(),(j['name'],side)
    colliders=[p for p in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies()) if p.HasAPI(UsdPhysics.CollisionAPI)]
    assert len(colliders)==len(audit['links']),'collision shape count mismatch'
    assert all(UsdPhysics.MeshCollisionAPI(p).GetApproximationAttr().Get()=='convexHull' for p in colliders)
    joint_prims={p.GetName():p for p in prims if p.IsA(UsdPhysics.RevoluteJoint) or p.IsA(UsdPhysics.PrismaticJoint)}
    assert set(joint_prims)=={j['name'] for j in audit['moving_joints']}
    for j in audit['moving_joints']:
        p=joint_prims[j['name']]; angular=j['type']!='prismatic'
        drive=UsdPhysics.DriveAPI.Get(p,'angular' if angular else 'linear')
        assert drive and drive.GetMaxForceAttr().Get()>0,j['name']
        assert drive.GetDampingAttr().Get()>0,j['name']
        for side in ('body0','body1'):
            targets=p.GetRelationship('physics:'+side).GetTargets()
            assert len(targets)==1 and stage.GetPrimAtPath(targets[0]),(j['name'],side)
        if j['type']!='continuous':
            factor=180/math.pi if angular else 1
            for side,key in [('lower','lowerLimit'),('upper','upperLimit')]:
                assert abs(p.GetAttribute('physics:'+key).Get()-j['limit'][side]*factor)<1e-3,(j['name'],key)
    appearance=asset.parent/'appearance_report.json'
    if appearance.exists():
        for entry in json.loads(appearance.read_text()):
            material=UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(entry['mesh'])).ComputeBoundMaterial()[0]
            expected='FactoryTexture' if entry['mode'].startswith('matched_uv') else 'Reference'
            assert expected in material.GetPrim().GetName(),(entry['mesh'],str(material.GetPath()))
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(asset))
    external=[x for x in unresolved if x not in {'OmniPBR.mdl'}]
    assert not external,external
    package=asset.parent.resolve()
    for dependency in [layer.realPath for layer in layers]+list(assets):
        assert Path(dependency).resolve().is_relative_to(package),f'External dependency: {dependency}'
    return dict(status='pass',roots=roots,moving_joints=len(joint_prims),fixed_joints=len(all_joints)-len(joint_prims),collision_shapes=len(colliders),rigid_bodies=len(bodies),max_frame_matrix_error=max_frame_error,layers=len(layers),assets=len(assets))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('asset',type=Path);ap.add_argument('--audit',type=Path,default=Path('reports/source_audit.json'));ap.add_argument('--output',type=Path)
    a=ap.parse_args();r=check(a.asset,json.loads(a.audit.read_text()));print(json.dumps(r,indent=2))
    if a.output:a.output.write_text(json.dumps(r,indent=2))
