"""Read-only vendor URDF and package integrity audit; run with NumPy available."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def audit_urdf(path, package):
    path,package=Path(path),Path(package)
    root=ET.parse(path).getroot()
    out={'source_sha256':digest(path),'links':[], 'joints':[], 'moving_joints':[], 'meshes':[], 'errors':[], 'warnings':[]}
    def issue(level,code,name,**detail): out[level].append(dict(code=code,name=name,**detail))
    for link in root.findall('link'):
        name=link.get('name'); inert=link.find('inertial')
        data={'name':name}
        if inert is None: issue('errors','missing_inertial',name)
        else:
            mass=float(inert.find('mass').get('value')); q=inert.find('inertia').attrib
            a,b,c,d,e,f=(float(q[k]) for k in ['ixx','ixy','ixz','iyy','iyz','izz'])
            mat=np.array([[a,b,c],[b,d,e],[c,e,f]])
            eig=np.linalg.eigvalsh(mat)
            data.update(mass_kg=mass,inertia=mat.tolist(),principal_inertia=eig.tolist(),origin=inert.find('origin').attrib)
            if not np.isfinite(mat).all() or eig.min()<=0: issue('errors','invalid_inertia',name)
            elif eig[-1]>eig[0]+eig[1]+1e-7: issue('warnings','inertia_triangle_inequality',name)
            if not np.isfinite(mass) or mass<=0: issue('errors','invalid_mass',name)
        for kind in ('visual','collision'):
            if link.find(kind) is None: issue('warnings','missing_'+kind,name)
        out['links'].append(data)
    names=[x['name'] for x in out['links']]; known=set(names)
    if len(known)!=len(names): issue('errors','duplicate_links','robot')
    children=[]; graph={n:[] for n in known}
    for j in root.findall('joint'):
        name=j.get('name'); kind=j.get('type'); p=j.find('parent').get('link'); c=j.find('child').get('link')
        data=dict(name=name,type=kind,parent=p,child=c,origin=j.find('origin').attrib if j.find('origin') is not None else {},axis=j.find('axis').get('xyz') if j.find('axis') is not None else None,limit={k:float(v) for k,v in j.find('limit').attrib.items()} if j.find('limit') is not None else {})
        if p not in known or c not in known: issue('errors','unknown_link',name)
        else: graph[p].append(c)
        children.append(c)
        if kind!='fixed':
            out['moving_joints'].append(data)
            axis=np.array([float(v) for v in (data['axis'] or '1 0 0').split()])
            if not np.isfinite(axis).all() or not np.isclose(np.linalg.norm(axis),1): issue('errors','invalid_axis',name)
            limits=data['limit']
            if kind!='continuous' and (not {'lower','upper'}<=limits.keys() or limits['lower']>=limits['upper']): issue('errors','invalid_limits',name)
            if not {'effort','velocity'}<=limits.keys(): issue('warnings','missing_effort_velocity',name)
        if j.find('mimic') is not None: data['mimic']=j.find('mimic').attrib
        out['joints'].append(data)
    out['root_links']=sorted(known-set(children))
    if len(out['root_links'])!=1 or len(children)!=len(set(children)): issue('errors','invalid_tree','robot')
    visited=set(); pending=list(out['root_links'])
    while pending:
        n=pending.pop()
        if n in visited: issue('errors','cycle',n); break
        visited.add(n); pending.extend(graph[n])
    if visited!=known: issue('errors','disconnected_tree','robot')
    for uri in sorted({m.get('filename') for m in root.findall('.//mesh')}):
        prefix='package://r1pro_urdf/'
        resolved=package/uri[len(prefix):] if uri.startswith(prefix) else path.parent/uri
        exists=resolved.is_file()
        out['meshes'].append(dict(uri=uri,exists=exists,sha256=digest(resolved) if exists else None))
        if not exists: issue('errors','missing_mesh',uri)
    out['total_mass_kg']=sum(x.get('mass_kg',0) for x in out['links'])
    out['joint_types']=dict(Counter(j['type'] for j in out['joints']))
    out['status']='pass' if not out['errors'] else 'fail'
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); selected=json.loads((args.source/'SELECTED_MODEL.json').read_text())
    result=audit_urdf(args.source/selected['selected_model'],args.source/'sdk/r1pro_urdf/share/r1pro_urdf')
    result['selected_hash_matches']=result['source_sha256']==selected['selected_model_sha256']
    checks=[]
    for line in (args.source/'CHECKSUMS.sha256').read_text().splitlines():
        if not line.strip(): continue
        expected,rel=line.split(None,1); rel=rel.lstrip('* ')
        p=(args.source/rel).resolve()
        if not p.is_relative_to(args.source.resolve()): raise ValueError('checksum path escapes source root')
        checks.append(dict(path=rel,match=p.is_file() and digest(p)==expected))
    result['package_integrity']={'files_checked':len(checks),'mismatches':[x for x in checks if not x['match']]}
    if not result['selected_hash_matches'] or result['package_integrity']['mismatches']: result['status']='fail'
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ['status','total_mass_kg','joint_types','errors','warnings','package_integrity']},indent=2))
    return 0 if result['status']=='pass' else 1

if __name__=='__main__': raise SystemExit(main())
