"""Immutable identity and safe output contract for the approved vendor package."""
import hashlib,json
from pathlib import Path
EXPECTED_URDF_SHA256='197091db1515a7326ad363b7f9894b3d847518120397f306d001c6ef1218d2e9'
EXPECTED_SELECTION_SHA256='f28a3b492f2854be4dbf7458726303059bbb526e188a91f2118c5baacf1914c7'
EXPECTED_URDF='sdk/r1pro_urdf/share/r1pro_urdf/urdf/r1pro_2026.urdf'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def verify_source(source):
    source=Path(source).resolve();selection=source/'SELECTED_MODEL.json'
    if digest(selection)!=EXPECTED_SELECTION_SHA256:raise ValueError('Unapproved selection manifest')
    selected=json.loads(selection.read_text())
    if selected['selected_model']!=EXPECTED_URDF or digest(source/EXPECTED_URDF)!=EXPECTED_URDF_SHA256:raise ValueError('Unapproved URDF identity')
    for item in selected['mesh_dependencies']:
        path=(source/item['path']).resolve()
        if not path.is_relative_to(source) or digest(path)!=item['sha256']:raise ValueError(f'Mesh identity mismatch: {item["path"]}')
    return selected

def require_fresh_output(output,source):
    output=Path(output).resolve();source=Path(source).resolve()
    if output.is_relative_to(source):raise ValueError('Output must be outside vendor source')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Output must be an empty directory; choose a new versioned path')
