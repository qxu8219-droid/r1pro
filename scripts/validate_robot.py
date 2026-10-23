"""Run reproducible 5.1 physics checks and capture; uses actual physics readback."""
import argparse,json,math
from pathlib import Path
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--asset',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--mode',choices=['fixed','mobile'],default='fixed');ap.add_argument('--config',type=Path,default=Path('configs/validation.json'));ap.add_argument('--common',type=Path,default=Path('configs/r1pro_2026_common.json'));ap.add_argument('--render',action='store_true')
a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);cfg=json.loads(a.config.read_text());common=json.loads(a.common.read_text())
import sys
sys.argv+=['--/exts/isaacsim.physics.newton/auto_switch_on_startup=false','--/exts/isaacsim.core.simulation_manager/default_engine=physx']
import faulthandler
faulthandler.enable()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'width':1280,'height':960,'renderer':'RayTracedLighting','limit_cpu_threads':12})
result={'mode':a.mode,'status':'fail','checks':[],'config':cfg,'asset':str(a.asset.resolve())}
try:
    from isaacsim.core.api import World
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction
    from isaacsim.core.version import get_version
    from pxr import UsdGeom,UsdPhysics,UsdLux,Gf,PhysicsSchemaTools,PhysxSchema
    import omni.usd
    world=World(stage_units_in_meters=1,physics_dt=cfg['physics_dt'],rendering_dt=1/60,backend='numpy')
    stage=omni.usd.get_context().get_stage()
    prim=stage.DefinePrim('/World/Robot','Xform');prim.GetReferences().AddReference(str(a.asset.resolve()))
    translate=prim.GetAttribute('xformOp:translate')
    if not translate: translate=UsdGeom.Xformable(prim).AddTranslateOp().GetAttr()
    translate.Set(Gf.Vec3d(0,0,0.015 if a.mode=='mobile' else 0.15))
    roots=[p for p in stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
    assert len(roots)==1
    articulation_path=str(roots[0].GetPath())
    scene=stage.GetPrimAtPath(world.get_physics_context().prim_path)
    PhysxSchema.PhysxSceneAPI(scene).CreateSolverTypeAttr('TGS')
    if a.mode=='fixed':
        joint=UsdPhysics.FixedJoint.Define(stage,'/World/Robot/test_fixture')
        joint.CreateBody1Rel().SetTargets([articulation_path])
        joint.CreateLocalPos0Attr(Gf.Vec3f(0,0,0.15))
    else:
        PhysicsSchemaTools.addGroundPlane(stage,'/World/Ground','Z',20,Gf.Vec3f(0),Gf.Vec3f(.35))
    UsdLux.DomeLight.Define(stage,'/World/DomeLight').CreateIntensityAttr(600)
    sun=UsdLux.DistantLight.Define(stage,'/World/DistantLight');sun.CreateIntensityAttr(1800)
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-35,25,25))
    robot=world.scene.add(SingleArticulation(articulation_path,name='robot'))
    print('RESET_BEGIN',flush=True);world.reset();print('RESET_DONE',flush=True)
    names=robot.dof_names;result['version']=get_version();result['dof_names']=names
    from isaacsim.core.simulation_manager import SimulationManager
    if hasattr(SimulationManager,'get_active_physics_engine'):
        result['physics_backend']=SimulationManager.get_active_physics_engine()
        assert result['physics_backend']=='physx',result['physics_backend']
    else:result['physics_backend']='physx (5.1 PhysicsContext)'
    assert set(names)==set(common['joints']),names
    indices={n:i for i,n in enumerate(names)};zero=np.zeros(len(names));targets=zero.copy();vel=zero.copy()
    robot.set_joint_positions(zero);robot.set_joint_velocities(zero)
    controller=robot.get_articulation_controller()
    def step(count):
        for _ in range(count):
            controller.apply_action(ArticulationAction(joint_positions=targets,joint_velocities=vel))
            world.step(render=False)
        q=robot.get_joint_positions();qd=robot.get_joint_velocities()
        assert np.isfinite(q).all() and np.isfinite(qd).all(),'nonfinite joint state'
        for name,i in indices.items():
            j=common['joints'][name]
            if j['type']!='continuous':
                assert j['limit']['lower']-cfg['joint_limit_tolerance']<=q[i]<=j['limit']['upper']+cfg['joint_limit_tolerance'],f'joint limit violated: {name}'
        return q,qd
    step(cfg['settle_steps'])
    result['settled_root_position']=robot.get_world_pose()[0].tolist()
    if a.mode=='fixed':
        for name in names:
            i=indices[name];j=common['joints'][name];typ=j['type'];targets[:]=0;vel[:]=0
            if typ=='continuous':vel[i]=cfg['wheel_test_velocity_rad_s']
            else:
                amp=cfg['linear_amplitude_m'] if typ=='prismatic' else cfg['angular_amplitude_rad']
                lo=j['limit']['lower'];hi=j['limit']['upper']
                targets[i]=min(amp,hi*0.5) if hi>amp else max(-amp,lo*0.5)
            q,qd=step(cfg['joint_steps'])
            actual=float(qd[i] if typ=='continuous' else q[i]);desired=float(vel[i] if typ=='continuous' else targets[i])
            tol=cfg['wheel_velocity_tolerance_rad_s'] if typ=='continuous' else cfg['linear_tolerance_m'] if typ=='prismatic' else cfg['angular_tolerance_rad']
            check=dict(joint=name,target=desired,actual=actual,error=abs(actual-desired),tolerance=tol,pass_=abs(actual-desired)<=tol)
            result['checks'].append(check);print('JOINT',json.dumps(check),flush=True)
        targets[:]=0;vel[:]=0;step(cfg['settle_steps'])
    else:
        pos0,quat0=robot.get_world_pose();q,qd=step(cfg['settle_steps']);pos1,quat1=robot.get_world_pose()
        def tilt(q):return math.acos(float(np.clip(1-2*(q[1]**2+q[2]**2),-1,1)))
        result['checks'].append(dict(name='rest_contact',pass_=abs(float(pos1[2]))<cfg['root_height_tolerance_m'] and tilt(quat1)<cfg['root_tilt_limit_rad'],height=float(pos1[2]),tilt_rad=tilt(quat1)))
        for name,i in indices.items():
            if name.startswith('steer'): targets[i]=0.12
        step(cfg['settle_steps'])
        steering={n:float(robot.get_joint_positions()[i]) for n,i in indices.items() if n.startswith('steer')}
        result['checks'].append(dict(name='steering',pass_=all(abs(v-.12)<cfg['angular_tolerance_rad'] for v in steering.values()),positions=steering))
        rolling_pos0=robot.get_world_pose()[0].copy()
        rolling_q0=robot.get_joint_positions().copy()
        for name,i in indices.items():
            if name.startswith('wheel'):vel[i]=cfg['wheel_test_velocity_rad_s']
        q,qd=step(cfg['settle_steps']);pos2,quat2=robot.get_world_pose();distance=float(np.linalg.norm((pos2-rolling_pos0)[:2]))
        wheel_actual={n:float(qd[i]) for n,i in indices.items() if n.startswith('wheel')}
        wheel_mean={n:float((q[i]-rolling_q0[i])/(cfg['settle_steps']*cfg['physics_dt'])) for n,i in indices.items() if n.startswith('wheel')}
        wheel_tracking=all(abs(v-cfg['wheel_test_velocity_rad_s'])<=cfg['wheel_velocity_tolerance_rad_s'] for v in wheel_mean.values())
        result['checks'].append(dict(name='rolling',pass_=wheel_tracking and distance>.01 and abs(float(pos2[2]))<cfg['root_height_tolerance_m'] and tilt(quat2)<cfg['root_tilt_limit_rad'],distance_m=distance,height=float(pos2[2]),tilt_rad=tilt(quat2),wheel_velocities=wheel_actual,mean_wheel_velocities=wheel_mean))
        vel[:]=0;step(cfg['settle_steps'])
    if a.render:
        from isaacsim.core.utils.viewports import set_camera_view
        import omni.replicator.core as rep
        from PIL import Image
        cam=UsdGeom.Camera.Define(stage,'/World/Camera');cam.CreateClippingRangeAttr(Gf.Vec2f(.01,100));cam.CreateFocalLengthAttr(35);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(27)
        render_product=rep.create.render_product('/World/Camera',(1280,960));rgb=rep.AnnotatorRegistry.get_annotator('rgb');rgb.attach([render_product])
        result['images']=[]
        for label,eye in [('front',(3,2,2.0)),('back',(-3,-2,2.0))]:
            set_camera_view(eye=np.array(eye),target=np.array([0,0,.85]),camera_prim_path='/World/Camera')
            for _ in range(10):world.render()
            rep.orchestrator.step(rt_subframes=8)
            frame=rgb.get_data();assert frame.size>0
            Image.fromarray(frame).save(a.output/(label+'.png'))
            result['images'].append(dict(file=label+'.png',mean=float(frame[:,:,:3].mean()),std=float(frame[:,:,:3].std())))
    result['status']='pass' if all(c['pass_'] for c in result['checks']) else 'fail'
    result['physics_steps']=world.current_time_step_index
    result['physics_seconds']=world.current_time
    stage.GetRootLayer().Export(str((a.output/'test_scene.usda').resolve()))
except Exception as exc:
    import traceback
    traceback.print_exc()
    result['error']=str(exc)
finally:
    (a.output/'results.json').write_text(json.dumps(result,indent=2))
    print('VALIDATION_RESULT',result['status'],flush=True)
    app.close(wait_for_replicator=False)
if result['status']!='pass':raise SystemExit(1)
