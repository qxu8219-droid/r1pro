"""Open the packaged demo and advance 3 seconds without external scene assets."""
import argparse,json,sys,traceback
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--scene',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
sys.argv+=['--/exts/isaacsim.physics.newton/auto_switch_on_startup=false','--/exts/isaacsim.core.simulation_manager/default_engine=physx']
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'width':640,'height':480,'renderer':'RayTracedLighting','limit_cpu_threads':12})
r={'status':'fail','scene':str(a.scene.resolve())}
try:
    import omni.usd
    import numpy as np
    from pxr import UsdPhysics
    from isaacsim.core.api import World
    from isaacsim.core.prims import SingleArticulation
    assert omni.usd.get_context().open_stage(str(a.scene.resolve()))
    stage=omni.usd.get_context().get_stage()
    roots=[str(p.GetPath()) for p in stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)];assert len(roots)==1
    world=World(stage_units_in_meters=1,physics_dt=1/240,rendering_dt=1/60)
    robot=world.scene.add(SingleArticulation(roots[0],name='robot'));world.reset()
    for _ in range(720):world.step(render=False)
    q=robot.get_joint_positions();position,rotation=robot.get_world_pose()
    assert len(q)==28 and np.isfinite(q).all() and np.isfinite(position).all()
    assert abs(float(position[2]))<.06
    r.update(status='pass',dofs=len(q),physics_seconds=3,root_position=position.tolist())
except Exception as e:r['error']=str(e);traceback.print_exc()
finally:
    a.output.write_text(json.dumps(r,indent=2));print('DEMO_RESULT',r['status'],flush=True);app.close(wait_for_replicator=False)
