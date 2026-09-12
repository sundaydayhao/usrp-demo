"""Check portable model references and prove the 3D-only migration preserved CAD."""
from pathlib import Path
import sys,json,hashlib,collections,subprocess,zipfile,io,copy,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,r'C:\projects\kicad-projects\tools\KiSkill-main')
from kicad_lib import sexp
BASE='45f46ab';NAMES=['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']
def children(n,k):return [x for x in n if isinstance(x,list) and str(x[0])==k]
def sans(n):return [sans(x) if isinstance(x,list) else str(x) for x in n if not(isinstance(x,list) and str(x[0])=='model')]
def digest(n):return hashlib.sha256(repr(sans(n)).encode()).hexdigest()
z=zipfile.ZipFile(io.BytesIO(subprocess.check_output(['git','archive','--format=zip',BASE,'projects','verification'],cwd=ROOT)))
reports=[]
def refs(m):return {str(x[1]):str(x[2]) for x in children(m,'property')}
def violations(j,erc=False):
 vs=[v for s in j['sheets'] for v in s['violations']] if erc else j['violations']
 return {json.dumps(v,sort_keys=True) for v in vs}
for n in NAMES:
 d=ROOT/'projects'/n;p=d/(n+'.kicad_pcb');rel=p.relative_to(ROOT).as_posix();b=sexp.load_file(p);old=sexp.parse(z.read(rel).decode());assert sans(b)==sans(old),(n,'non-model PCB change')
 libcount=0
 for f in (d/'USRP.pretty').glob('*.kicad_mod'):
  assert sans(sexp.load_file(f))==sans(sexp.parse(z.read(f.relative_to(ROOT).as_posix()).decode())),f
  libcount+=1
 for suffix in ['.kicad_sch','.kicad_pro']:
  f=d/(n+suffix);baseline=subprocess.check_output(['git','show',BASE+':'+f.relative_to(ROOT).as_posix()],cwd=ROOT);assert f.read_bytes().replace(b'\r\n',b'\n')==baseline.replace(b'\r\n',b'\n'),f
 model_files=set();bmodels=0;oldmodels=sum(bool(children(f,'model')) for f in children(old,'footprint'));missing_old_paths=[]
 for f in children(b,'footprint'):
  pr=refs(f);ref=pr['Reference'];models=children(f,'model');lf=d/'USRP.pretty'/(ref+'.kicad_mod')
  if lf.exists():assert models==children(sexp.load_file(lf),'model'),(n,ref,'PCB/library model mismatch')
  if models:bmodels+=1
  for m in models:
   s=str(m[1]);assert s.startswith('${KIPRJMOD}/3dmodels/'),(n,ref,s)
   file=d/s.split('}/',1)[1];assert file.is_file() and file.stat().st_size>100,(n,ref,s)
   for key in ['offset','scale','rotate']:assert children(m,key),(n,ref,key)
   model_files.add(file)
   if file.suffix=='.wrl':assert file.with_suffix('.step').exists(),file
 audit=json.loads((ROOT/'verification'/n/'3d-models.json').read_text());assert all(a['status']!='pending' for a in audit['models'])
 delta={}
 for kind in ['erc','drc']:
  rel='verification/'+n+'/'+kind+'.json';new=json.loads((ROOT/rel).read_text());prev=json.loads(z.read(rel));a,c=violations(prev,kind=='erc'),violations(new,kind=='erc');delta[kind]={'added':len(c-a),'removed':len(a-c)};assert not(c-a or a-c),(n,kind,'violation delta')
  if kind=='drc':assert new['unconnected_items']==prev['unconnected_items']
 report={'project':n,'baseline_commit':BASE,'PCB_non_model_semantic_equal':True,'local_footprint_non_model_semantic_equal':True,'schematic_equal_ignoring_line_endings':True,'project_settings_equal_ignoring_line_endings':True,'PCB_non_model_sha256':digest(b),'pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'local_footprints_checked':libcount,'footprints_with_models_before':oldmodels,'footprints_with_models_after':bmodels,'new_model_bindings':bmodels-oldmodels,'distinct_bound_model_files':len(model_files),'all_model_paths_project_relative_and_resolved':True,'PCB_and_library_model_bindings_equal':True,'approximate_envelope_instances':sum('APPROX' in str(a) for a in [m[1] for f in children(b,'footprint') for m in children(f,'model')]),'electrical_check_set_diff':delta}
 (ROOT/'verification'/n/'3d-review.json').write_text(json.dumps(report,indent=2));reports.append(report);print(n,bmodels,'models; non-model CAD identical; ERC/DRC delta empty',flush=True)
(ROOT/'verification/3d-review-summary.json').write_text(json.dumps({'baseline_commit':BASE,'projects':reports,'new_bindings':sum(r['new_model_bindings'] for r in reports),'total_bound_instances':sum(r['footprints_with_models_after'] for r in reports)},indent=2))
