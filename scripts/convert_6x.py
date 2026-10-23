"""Native Isaac Sim 6.x URDF conversion; requires the version-pinned 6.2 runtime."""
import argparse,json,os,sys,traceback
from pathlib import Path
import xml.etree.ElementTree as ET
from source_contract import verify_source, require_fresh_output
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--config',type=Path,default=Path('configs/import_6x.json'))
a=ap.parse_args();a.source=a.source.resolve();a.output=a.output.resolve();require_fresh_output(a.output,a.source)
selected=verify_source(a.source);source=a.source/selected['selected_model'];settings=json.loads(a.config.read_text())
a.output.mkdir(parents=True,exist_ok=True)
tree=ET.parse(source);tree.getroot().set('name','r1pro_2026')
work=a.output/'resolved_source.urdf'
for m in tree.findall('.//mesh'):
    uri=m.get('filename');prefix='package://r1pro_urdf/'
    assert uri.startswith(prefix)
    m.set('filename',str(a.source/'sdk/r1pro_urdf/share/r1pro_urdf'/uri[len(prefix):]))
tree.write(work,encoding='utf-8',xml_declaration=True)
sys.argv+=['--/exts/isaacsim.physics.newton/auto_switch_on_startup=false','--/exts/isaacsim.core.simulation_manager/default_engine=physx']
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'width':960,'height':720,'renderer':'RayTracedLighting','limit_cpu_threads':12})
report={'status':'fail','source_sha256':selected['selected_model_sha256'],'config':settings}
try:
    import omni.kit.app
    manager=omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate('isaacsim.asset.importer.urdf',True)
    manager.set_extension_enabled_immediate('isaacsim.robot.schema',True)
    from isaacsim.asset.importer.urdf import URDFImporter,URDFImporterConfig
    from isaacsim.core.version import get_version
    from pxr import Usd,UsdGeom
    report['isaac_version']=get_version()
    cfg=URDFImporterConfig(urdf_path=str(work),usd_path=str(a.output/'native'),**settings)
    print('IMPORT_BEGIN',flush=True);native=Path(URDFImporter(cfg).import_urdf());print('NATIVE',native,flush=True)
    raw=Usd.Stage.Open(str(native));assert raw and raw.GetDefaultPrim()
    root_name=raw.GetDefaultPrim().GetName()
    entry=a.output/'r1pro_2026.usd';stage=Usd.Stage.CreateNew(str(entry))
    root=stage.DefinePrim('/'+root_name,'Xform');root.GetReferences().AddReference(os.path.relpath(native,a.output))
    stage.SetDefaultPrim(root);UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    for name in root.GetVariantSets().GetNames():
        variants=root.GetVariantSet(name)
        for value in variants.GetVariantNames():
            if value.lower()=='physx':variants.SetVariantSelection(value)
    stage.GetRootLayer().Save()
    report.update(status='imported',native_entry=str(native.relative_to(a.output)),root=str(root.GetPath()))
except Exception as e:
    report['error']=str(e);traceback.print_exc()
finally:
    (a.output/'conversion.json').write_text(json.dumps(report,indent=2));print('IMPORT_RESULT',report['status'],flush=True)
    app.close(wait_for_replicator=False,exit_code=0 if report['status']=='imported' else 1)
