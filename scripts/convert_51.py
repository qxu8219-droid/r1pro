"""Convert pinned vendor URDF with Isaac Sim 5.1's native importer.
Run with the 5.1 installation's python.sh. Vendor inputs are never modified.
"""
import argparse,json
from pathlib import Path
import xml.etree.ElementTree as ET
from source_contract import verify_source, require_fresh_output

ap=argparse.ArgumentParser()
ap.add_argument('--source',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--config',type=Path,default=Path('configs/import_51.json'))
a=ap.parse_args(); a.source=a.source.resolve(); a.output=a.output.resolve()
settings=json.loads(a.config.read_text())
selected=verify_source(a.source)
require_fresh_output(a.output,a.source)
urdf=a.source/selected['selected_model']
a.output.mkdir(parents=True,exist_ok=True)
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'width':960,'height':720,'renderer':'RayTracedLighting','limit_cpu_threads':12})
try:
    import omni.kit.commands
    from isaacsim.core.utils.extensions import enable_extension
    from isaacsim.core.version import get_version
    enable_extension('isaacsim.asset.importer.urdf')
    import omni.usd
    from pxr import Usd,UsdGeom
    print('VERSION',get_version(),flush=True)
    ok,config=omni.kit.commands.execute('URDFCreateImportConfig')
    assert ok
    for k,v in settings.items():
        if k!='description': setattr(config,k,v)
    # Derived working URDF resolves packages without altering the vendor package.
    tree=ET.parse(urdf); tree.getroot().set('name','r1pro_2026')
    for m in tree.findall('.//mesh'):
        uri=m.get('filename'); prefix='package://r1pro_urdf/'
        if not uri.startswith(prefix): raise ValueError(f'Unsupported resource {uri}')
        mesh=a.source/'sdk/r1pro_urdf/share/r1pro_urdf'/uri[len(prefix):]
        assert mesh.is_file(); m.set('filename',str(mesh))
    work=a.output/'resolved_source.urdf'; tree.write(work,encoding='utf-8',xml_declaration=True)
    dest=a.output/'r1pro_2026.usd'
    print('IMPORT_BEGIN',flush=True)
    ok,root=omni.kit.commands.execute('URDFParseAndImportFile',urdf_path=str(work),import_config=config,dest_path=str(dest))
    if not ok: raise RuntimeError('URDF import failed')
    stage=Usd.Stage.Open(str(dest))
    UsdGeom.SetStageMetersPerUnit(stage,1); UsdGeom.SetStageUpAxis(stage,'Z')
    stage.GetRootLayer().Save()
    print('IMPORT_PASS',str(dest),root,flush=True)
    (a.output/'conversion.json').write_text(json.dumps({'status':'imported','isaac_version':get_version(),'source_sha256':selected['selected_model_sha256'],'root':root,'config':settings},indent=2))
finally:
    app.close()
