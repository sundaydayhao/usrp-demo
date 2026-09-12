"""Bind project-local 3D models without changing electrical or mechanical CAD data."""
from pathlib import Path
import sys,json,copy,math,shutil,subprocess,hashlib,collections,zipfile,io
sys.path.insert(0,r'C:\projects\kicad-projects\tools\KiSkill-main')
from kicad_lib import sexp
Q=sexp.QStr.of
S=sexp.Sym
ROOT=Path(__file__).resolve().parents[1];LIB=Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints');MODELS=Path(r'C:\Program Files\KiCad\10.0\share\kicad\3dmodels');EE=ROOT/'tmp/3d-source';BASE='45f46ab'
baseline_zip=zipfile.ZipFile(io.BytesIO(subprocess.check_output(['git','archive','--format=zip',BASE,'projects'],cwd=ROOT)))
def original(path):return sexp.parse(baseline_zip.read(path.relative_to(ROOT).as_posix()).decode())
def children(n,k):return [x for x in n if isinstance(x,list) and str(x[0])==k]
def one(n,k):return next(iter(children(n,k)),None)
def val(n,k):
 q=one(n,k);return str(q[1]) if q else ''
def props(f):return {str(q[1]):str(q[2]) for q in children(f,'property')}
def pads(f):
 out={}
 for a in children(f,'pad'):
  if str(a[1]):out.setdefault(str(a[1]),tuple(map(float,one(a,'at')[1:3])))
 return out
def strip_models(n):
 return [strip_models(x) if isinstance(x,list) else x for x in n if not(isinstance(x,list) and str(x[0])=='model')]
def fingerprint(n):return hashlib.sha256(repr(strip_models(n)).encode()).hexdigest()
def load_stock(group,name):return sexp.load_file(LIB/(group+'.pretty')/(name+'.kicad_mod'))
def visual_model(f,group,name):
 f=copy.deepcopy(f)
 if not children(f,'model'):f.append(sexp.parse('(model "" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'))
 children(f,'model')[0][1]=Q('${KICAD10_3DMODEL_DIR}/'+group+'.3dshapes/'+name+'.step');return f
def fit(a,c):
 aa,cc=pads(a),pads(c);keys=set(aa)&set(cc);assert keys
 ax=sum(aa[k][0] for k in keys)/len(keys);ay=sum(aa[k][1] for k in keys)/len(keys);cx=sum(cc[k][0] for k in keys)/len(keys);cy=sum(cc[k][1] for k in keys)/len(keys)
 choices=[]
 for ang in [0,90,180,270]:
  th=math.radians(ang);co,si=round(math.cos(th)),round(math.sin(th));dx=cx-(co*ax-si*ay);dy=cy-(si*ax+co*ay)
  rms=math.sqrt(sum((co*aa[k][0]-si*aa[k][1]+dx-cc[k][0])**2+(si*aa[k][0]+co*aa[k][1]+dy-cc[k][1])**2 for k in keys)/len(keys));choices.append((rms,ang,dx,dy))
 return min(choices)
def choose(f,ref,value):
 desc=val(f,'descr')
 if children(f,'model'):
  s=str(children(f,'model')[0][1])
  if s.endswith('HVQFN-40-1EP_6x6mm_P0.5mm_EP4.1x4.1mm.step'):return visual_model(f,'Package_DFN_QFN','QFN-40-1EP_6x6mm_P0.5mm'),'KiCad QFN40 6x6 pitch 0.5 visual package; exposed pad differs',False
  if s.endswith('LFCSP-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm.step'):return load_stock('Package_DFN_QFN','QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm'),'KiCad QFN32 5x5 pitch 0.5 visual package; exposed pad differs',False
  return f,'existing KiCad package model',False
 if value in ['NPTH','M2.5 GND','TestPoint'] or ref.startswith('H'):return None,'bare hole or etched test pad',False
 if 'PMC' in value or desc=='PMC-REVERSE':return sexp.load_file(EE/'envelopes/PMC64_APPROX_DISPLAY.kicad_mod'),'APPROXIMATE PMC socket display envelope; see model JSON',False
 if value=='MT4937DI5':return sexp.load_file(EE/'envelopes/MT4937DI5_APPROX_DISPLAY.kicad_mod'),'APPROXIMATE tuner display envelope; 15 mm height assumed; F connector omitted',False
 if value.startswith('QTE'):return sexp.load_file(EE/'easyeda.pretty/CONN-SMD_QTE-020-01-F-D.kicad_mod'),'EasyEDA C3640849, QTE-020-01 package (plating/packing variant)',False
 if value=='TC1-1-13M+':return sexp.load_file(EE/'easyeda.pretty/XFMR-SMD_TC1-1TX.kicad_mod'),'EasyEDA C879854 (AT224 package)',False
 if value=='ADT1-1WT+':return sexp.load_file(EE/'easyeda.pretty/XFMR-SMD_6P-L7.9-W5.6-P2.54-LS7.0-BL.kicad_mod'),'EasyEDA C6835853',False
 if 'SMA' in value or desc=='SMA_VERT':return load_stock('Connector_Coaxial','SMA_Amphenol_132134-11_Vertical'),'KiCad: matching 5.08 mm square PTH SMA geometry',False
 if desc in ['0603','1206']:
  size='0603_1608Metric' if desc=='0603' else '1206_3216Metric';code='C' if ref.startswith('C') else 'L' if ref.startswith(('L','FB')) else 'R';group={'R':'Resistor_SMD','C':'Capacitor_SMD','L':'Inductor_SMD'}[code]
  return load_stock(group,code+'_'+size),'KiCad generic '+desc+' package',False
 if desc=='SO8':return load_stock('Package_SO','SOIC-8_3.9x4.9mm_P1.27mm'),'KiCad SOIC-8 package',False
 if desc.startswith('CONNECTOR-'):
  parts=desc.split('-');columns,rows=int(parts[1]),int(parts[2]);return load_stock('Connector_PinHeader_2.54mm',f'PinHeader_{rows}x{columns:02d}_P2.54mm_Vertical'),'KiCad 2.54 mm vertical pin header',False
 if desc=='EIA6032':return load_stock('Capacitor_Tantalum_SMD','CP_EIA-6032-28_Kemet-C'),'KiCad EIA6032 package; height class representative',False
 if desc=='SOT23':return load_stock('Package_TO_SOT_SMD','SOT-23'),'KiCad SOT23',False
 if desc=='SOT223':
  s=load_stock('Package_TO_SOT_SMD','SOT-223-3_TabPin2');largest=max([q for q in children(s,'pad') if str(q[1])=='2'],key=lambda a:float(one(a,'size')[1])*float(one(a,'size')[2]));largest[1]=Q('4');return s,'KiCad SOT223 package',False
 if desc.startswith('TSOT23'):return load_stock('Package_TO_SOT_SMD','TSOT-23-6'),'KiCad TSOT23-6',False
 qfn={'ADL5387ACPZ':('Package_CSP','LFCSP-24-1EP_4x4mm_P0.5mm_EP2.3x2.3mm'),'ADA4937-2YCPZ':('Package_DFN_QFN','HVQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm'),'HMC472LP4E':('Package_DFN_QFN','QFN-24_4x4mm_P0.5mm'),'ADL5386ACPZ':('Package_DFN_QFN','QFN-40-1EP_6x6mm_P0.5mm'),'XC2C32A-6QFG32C':('Package_DFN_QFN','QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm')}
 qfn['ADL5387ACPZ']=('Package_CSP','LFCSP-24-1EP_4x4mm_P0.5mm_EP2.3x2.3mm')
 if value in qfn:return visual_model(f,*qfn[value]),'KiCad matching body/pitch package; not vendor-specific appearance; exposed pad may differ',False
 raise ValueError((ref,value,desc))
def apply(name):
 d=ROOT/'projects'/name;bp=d/(name+'.kicad_pcb');b=sexp.load_file(bp);before=fingerprint(b);modeldir=d/'3dmodels';modeldir.mkdir(exist_ok=True);audit=[];sources=json.loads((modeldir/'SOURCES.json').read_text()) if (modeldir/'SOURCES.json').exists() else {}
 for f in children(b,'footprint'):
  pr=props(f);ref=pr['Reference'];value=pr['Value'];lib=d/'USRP.pretty'/(ref+'.kicad_mod')
  if not lib.exists():audit.append({'ref':ref,'status':'bare mounting hole'});continue
  lf=sexp.load_file(lib);oldlf=fingerprint(lf);orig=original(lib);assert fingerprint(orig)==oldlf,('Non-model library changes since baseline',lib)
  src,source,pending=choose(orig,ref,value)
  if src is None:audit.append({'ref':ref,'value':value,'status':'pending' if pending else 'bare pad/hole','source':source});continue
  match=copy.deepcopy(lf);bottom_in_front=all('B.Cu' in [str(x) for x in one(p,'layers')[1:]] and 'F.Cu' not in [str(x) for x in one(p,'layers')[1:]] for p in children(lf,'pad'))
  if name=='TVRX' and ref=='J2':bottom_in_front=True
  if bottom_in_front:
   for p in children(match,'pad'):one(p,'at')[2]=S(str(-float(one(p,'at')[2])))
  rms,angle,dx,dy=fit(src,match)
  if 'SMA' in value:angle=0;dx,dy=pads(lf)['1'];rms=0
  assert rms<1.4,(name,ref,'alignment mismatch',rms)
  models=[]
  for md in children(src,'model'):
   mm=copy.deepcopy(md);fn=str(mm[1]);sourcefile=MODELS/fn.split('}/',1)[1] if fn.startswith('${KICAD') else d/fn.split('}/',1)[1] if fn.startswith('${KIPRJMOD}') else ROOT/fn
   assert sourcefile.exists(),sourcefile
   prefix='EasyEDA_' if 'easyeda.3dshapes' in str(sourcefile) else '';target=modeldir/(prefix+sourcefile.name)
   if sourcefile.resolve()!=target.resolve():shutil.copy2(sourcefile,target)
   # Preserve companion STEP geometry when the imported display model is VRML.
   if sourcefile.suffix=='.wrl' and sourcefile.with_suffix('.step').exists() and sourcefile.resolve()!=target.resolve():shutil.copy2(sourcefile.with_suffix('.step'),target.with_suffix('.step'))
   if sourcefile.with_suffix('.json').exists():shutil.copy2(sourcefile.with_suffix('.json'),target.with_suffix('.json'))
   mm[1]=Q('${KIPRJMOD}/3dmodels/'+target.name)
   off=one(one(mm,'offset'),'xyz');ox,oy,oz=map(float,off[1:]);rad=math.radians(-angle);xx=math.cos(rad)*ox-math.sin(rad)*oy+dx;yy=math.sin(rad)*ox+math.cos(rad)*oy-dy;off[1:]=[S(f'{xx:.6f}'),S(f'{yy:.6f}'),S(str(oz))]
   rot=one(one(mm,'rotate'),'xyz');rot[3]=S(str(float(rot[3])+angle))
   if bottom_in_front:
    rot[1]=S('180');rot[3]=S(str(-float(rot[3])));off[2]=S(str(-float(off[2])));off[3]=S('-1.6')
   models.append(mm)
   if target.name not in sources:sources[target.name]={'source':source,'origin':str(sourcefile.relative_to(MODELS)) if sourcefile.is_relative_to(MODELS) else str(sourcefile.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
  for node in [lf,f]:node[:]=[x for x in node if not(isinstance(x,list) and str(x[0])=='model')];node.extend(copy.deepcopy(models))
  assert fingerprint(lf)==oldlf
  sexp.save_file(lib,lf);audit.append({'ref':ref,'value':value,'status':'bound','model':str(models[0][1]),'source':source,'alignment_rms_mm':rms,'rotation_xyz':[float(x) for x in one(one(models[0],'rotate'),'xyz')[1:]],'offset_mm':[float(x) for x in one(one(models[0],'offset'),'xyz')[1:]],'legacy_bottom_pads_in_front_footprint':bottom_in_front})
 assert before==fingerprint(b),'Non-model PCB data changed'
 sexp.save_file(bp,b);assert fingerprint(sexp.load_file(bp))==before
 out=ROOT/'verification'/name/'3d-models.json';out.write_text(json.dumps({'project':name,'non_model_PCB_data_unchanged':True,'non_model_sha256':before,'models':audit},indent=2));(modeldir/'SOURCES.json').write_text(json.dumps(sources,indent=2))
 print(name,dict(collections.Counter(q['status'] for q in audit)),flush=True)
if __name__=='__main__':
 for name in sys.argv[1:] or ['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']:apply(name)
