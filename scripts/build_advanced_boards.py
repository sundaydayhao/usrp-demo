"""Stage audited footprints, USRP1 geometry and electrical placement for PDF boards.

Run with KiCad's Python. Placement is a design input; routing/DRC is a separate gate.
"""
from pathlib import Path
import pcbnew as p
import json,math,sys,copy,collections,random,re
ROOT=Path(__file__).resolve().parents[1]
LIB=Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
def v(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def xy(o):q=o.GetPosition();return (p.ToMM(q.x),p.ToMM(q.y))
def lset(*ls):
 s=p.LSET()
 for l in ls:s.AddLayer(l)
 return s
def stock(lib,name):
 f=p.FootprintLoad(str(LIB/(lib+'.pretty')),name)
 if not f:raise ValueError((lib,name))
 return f
def rect(f,bb,layer=p.F_CrtYd,width=.05):
 x1,y1,x2,y2=bb
 for a,c in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]:
  s=p.PCB_SHAPE(f);s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*c));s.SetLayer(layer);s.SetWidth(p.FromMM(width));f.Add(s)
def pad(f,num,x,y,w,h,drill=None,layers=None):
 a=p.PAD(f);a.SetNumber(str(num));a.SetPosition(v(x,y));a.SetSize(v(w,h));a.SetShape(p.PAD_SHAPE_RECT if drill is None else p.PAD_SHAPE_CIRCLE)
 if drill is not None:
  a.SetAttribute(p.PAD_ATTRIB_PTH if num else p.PAD_ATTRIB_NPTH);a.SetDrillSize(v(drill,drill));ls=p.LSET.AllCuMask();ls.AddLayer(p.F_Mask);ls.AddLayer(p.B_Mask);a.SetLayerSet(ls)
 else:a.SetAttribute(p.PAD_ATTRIB_SMD);a.SetLayerSet(layers or lset(p.F_Cu,p.F_Paste,p.F_Mask))
 f.Add(a);return a
def transformer():
 f=p.FOOTPRINT(None)
 for num,x,y in [(1,-1.27,-1.59),(2,0,-1.59),(3,1.27,-1.59),(6,-1.27,1.59),(4,1.27,1.59)]:pad(f,num,x,y,.76,1.65)
 rect(f,(-2.16,-2.665,2.16,2.665));rect(f,(-1.905,-1.905,1.905,1.905),p.F_Fab,.1)
 f.SetLibDescription('Mini-Circuits TC1-1-13M+ AT224-1A; datasheet land pattern; dotted primary 6, dotted secondary 1')
 return f
def qte():
 f=p.FOOTPRINT(None)
 for i in range(20):
  for row in (0,1):pad(f,2*i+row+1,-7.6+.8*i,(-1 if row==0 else 1)*3.085,.46,1.45)
 for x,w in [(-8.445,2.54),(-3.175,4.7),(3.175,4.7),(8.445,2.54)]:pad(f,41,x,0,w,.64)
 for x in [-9.24,9.24]:pad(f,'',x,-2.035,1.02,1.02,1.02)
 rect(f,(-10.2,-4.05,10.2,4.05));rect(f,(-10,-3.5,10,3.5),p.F_Fab,.1)
 f.SetLibDescription('Samtec QTE-020-01-L-D-A, official footprint rev K; ground blade pads numbered 41')
 return f
def qfn(count,size,ep,base=None):
 if base:f=stock(*base)
 else:
  f=p.FOOTPRINT(None);per=count//4
  for i in range(per):
   z=-(per-1)*.25+i*.5
   pad(f,i+1,-size/2,z,.7,.25);pad(f,per+i+1,z,size/2,.25,.7)
   pad(f,2*per+i+1,size/2,-z,.7,.25);pad(f,3*per+i+1,-z,-size/2,.25,.7)
  pad(f,count+1,0,0,ep,ep,layers=lset(p.F_Cu,p.F_Mask))
  rect(f,(-size/2-.6,-size/2-.6,size/2+.6,size/2+.6));rect(f,(-size/2,-size/2,size/2,size/2),p.F_Fab,.1)
 # Retain exposed copper but give paste a window pattern (about 65% area).
 old=list(f.Pads())
 for a in old:
  if not a.GetNumber() and a.GetAttribute()==p.PAD_ATTRIB_SMD:f.Remove(a)
  elif a.GetNumber()==str(count+1):a.SetSize(v(ep,ep));a.SetLayerSet(lset(p.F_Cu,p.F_Mask))
 for x in [-ep/4,ep/4]:
  for y in [-ep/4,ep/4]:pad(f,'',x,y,ep*.4,ep*.4,layers=lset(p.F_Paste))
 return f
def choose(ref,c,legacy):
 value=c['value'];nums=c['pins']
 if 'PMC-64' in value:
  src=legacy['BasicTX'] if ref=='J402' else legacy['BasicRX'];rr='J44' if ref=='J402' else 'J2'
  f=p.FOOTPRINT(next(x for x in src.GetFootprints() if x.GetReference()==rr));return f,'Original gEDA PMC64 land pattern'
 if 'SMA' in value:return p.FOOTPRINT(next(x for x in legacy['BasicRX'].GetFootprints() if x.GetReference()=='J18')),'Original gEDA SMA 5-pin PTH'
 if value=='TC1-1-13M+':return transformer(),'Mini-Circuits AT224-1A'
 if value=='QTE-020':return qte(),'Samtec QTE-020-01-L-D-A footprint rev K'
 if ref.startswith('M'):return stock('MountingHole','MountingHole_2.7mm_M2.5_Pad'),'M2.5 plated mounting hole'
 if value=='TestPoint':return stock('TestPoint','TestPoint_Pad_D1.0mm'),'1.0 mm probe pad'
 if ref.startswith('J'):
  count=len(nums);pitch=2.0 if ref=='J280' else 1.27 if count>=8 else 2.54;rows=2 if count>=8 else 1
  pkg=f'PinHeader_{rows}x{count//rows:02d}_P{pitch:.2f}mm_Vertical'
  return stock(f'Connector_PinHeader_{pitch:.2f}mm',pkg),pkg
 if value.startswith('TDA18272'):return qfn(40,6,4.1,('Package_DFN_QFN','HVQFN-40-1EP_6x6mm_P0.5mm_EP4.1x4.1mm')),'NXP SOT618-1 HVQFN40 EP4.1'
 if value.startswith('XC2C32'):return qfn(32,5,3.63),'AMD QFG32 5x5, pitch0.5, EP3.63, UG112'
 if value.startswith('ADF4350'):return qfn(32,5,3.1,('Package_CSP','LFCSP-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm')),'ADI CP-32-7'
 if value.startswith('ADL5387'):return qfn(24,4,2.3),'ADI CP-24-14, EP2.3'
 if value.startswith('ADL5386'):return qfn(40,6,4.1),'ADI CP-40-1, EP4.1'
 if value.startswith('ADA4937'):return qfn(24,4,2.1),'ADI CP-24-10, EP2.1'
 if value.startswith('HMC472'):return qfn(24,4,2.5),'Hittite LP4 4x4 QFN, EP2.5; retain original HMC472LP4E'
 if value.startswith('ADP3336'):return stock('Package_SO','MSOP-8_3x3mm_P0.65mm'),'ADI RM-8 MSOP8'
 if value.startswith('24LC'):return stock('Package_SO','SOIC-8_3.9x4.9mm_P1.27mm'),'SOIC8 /SN'
 if value.startswith('LT1085'):
  f=stock('Package_TO_SOT_SMD','SOT-223-3_TabPin2');max((a for a in f.Pads() if a.GetNumber()=='2'),key=lambda a:a.GetSize().x*a.GetSize().y).SetNumber('4');return f,'SOT223, tab explicitly numbered 4 and tied to output 2'
 if value.startswith('MIC5247'):return stock('Package_TO_SOT_SMD','SOT-23-5'),'SOT23-5'
 if value=='MGA-82563':return stock('Package_TO_SOT_SMD','SOT-363_SC-70-6'),'SOT363'
 if value=='GVA-84+':
  f=stock('Package_TO_SOT_SMD','SOT-89-3');pad(f,4,0,0,.8,.8,layers=lset(p.F_Cu,p.F_Mask));return f,'SOT89, heat tab numbered 4 (GND), inside continuous pin-2 copper'
 if ref[0] in 'RCL':
  size='0402_1005Metric' if ref[0]!='L' else '0603_1608Metric'
  if ref in ['L290','L291','L292','L293','L295','L296','L297','L298']:size='0402_1005Metric'
  cap=re.search(r'([\d.]+)\s*u',value.lower()) if ref[0]=='C' else None
  if cap:
   uf=float(cap.group(1))
   if uf>=22:
    pkg='CP_EIA-7343-31_Kemet-D' if uf>=47 else 'CP_EIA-3528-21_Kemet-B'
    return stock('Capacitor_Tantalum_SMD',pkg),'Polarized bulk capacitor '+pkg+'; positive pad 1'
   size='0402_1005Metric' if uf<=.1 else '0603_1608Metric' if uf<=1 else '0805_2012Metric' if uf<=4.7 else '1206_3216Metric'
  lib={'R':'Resistor_SMD','C':'Capacitor_SMD','L':'Inductor_SMD'}[ref[0]]
  return stock(lib,ref[0]+'_'+size),ref[0]+'_'+size
 raise ValueError((ref,value))

def build(name):
 d=ROOT/'projects'/name;vdir=ROOT/'verification'/name
 model=json.loads((vdir/'reconstructed-netlist.json').read_text());netmap=json.loads((vdir/'kicad-net-name-map.json').read_text())
 b=p.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
 legacy={n:p.LoadBoard(str(ROOT/'projects'/n/(n+'.kicad_pcb'))) for n in ['BasicRX','BasicTX']}
 nets={}
 for source in model['nets']:
  ni=p.NETINFO_ITEM(b,netmap[source]);b.Add(ni);nets[source]=ni
 pin_net={tuple(pin):net for net,ps in model['nets'].items() for pin in ps}
 fps={};fpdir=d/'USRP.pretty';fpdir.mkdir(exist_ok=True);plugin=p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP);audit={}
 for ref,c in model['components'].items():
  f,src=choose(ref,c,legacy)
  # Normalize local library copy to the top side; instance flipping is below.
  if f.GetLayer()==p.B_Cu:f.Flip(f.GetPosition(),False)
  f.SetOrientationDegrees(0);f.SetPosition(v(0,0));f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID('USRP',ref));f.SetLocked(False)
  for a in f.Pads():a.SetNetCode(0)
  f.Reference().SetTextSize(v(.65,.65));f.Reference().SetTextThickness(p.FromMM(.1));f.Reference().SetPosition(v(0,-2.8));f.Reference().SetLayer(p.F_SilkS);f.Value().SetVisible(False)
  actual={a.GetNumber() for a in f.Pads() if a.GetNumber()}
  assert set(c['pins'])==actual,(name,ref,c['pins'],actual)
  plugin.FootprintSave(str(fpdir),f)
  b.Add(f);f.SetPath(p.KIID_PATH(c['sheet_path']+'/'+c['symbol_uuid']))
  for a in f.Pads():
   if (ref,a.GetNumber()) in pin_net:a.SetNet(nets[pin_net[ref,a.GetNumber()]])
  fps[ref]=f;audit[ref]={'value':c['value'],'source':src,'numbered_pads':sorted(actual)}
 h=142.24 if name=='WBX' else 63.5
 for a,c in [((0,0),(69.85,0)),((69.85,0),(69.85,h)),((69.85,h),(0,h)),((0,h),(0,0))]:
  s=p.PCB_SHAPE(b);s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(v(*a));s.SetEnd(v(*c));s.SetLayer(p.Edge_Cuts);s.SetWidth(p.FromMM(.05));b.Add(s)
 placement={}
 def place(ref,x,y,angle=0,back=False):
  f=fps[ref]
  if back!=(f.GetLayer()==p.B_Cu):f.Flip(f.GetPosition(),False)
  f.SetOrientationDegrees(angle);f.SetPosition(v(x,y));placement[ref]=(x,y,angle,back)
 if name=='TVRX2':
  seeds={'J2':(24.128222,24.335994,0,True),'J100':(64,12),'J140':(64,49),'U100':(51,13,180),'U140':(51,48,180),'U80':(29,44),'U1':(15,29),'U2':(15,10,90),'U3':(22,10),'J25':(6,21,90),'J26':(8,35),'J27':(8,44),'J280':(18,53,90)}
  for ref,loc in seeds.items():place(ref,*loc)
  for i,(x,y) in enumerate([(3.81,3.81),(66.04,3.81),(3.81,59.69),(66.04,59.69)]):
   f=stock('MountingHole','MountingHole_2.7mm_M2.5');f.SetReference('H'+str(i+1));f.SetPosition(v(x,y));f.SetExcludedFromBOM(True);b.Add(f)
 else:
  seeds={'J402':(24.128222,35.511994,0,True),'J201':(24.128222,103.075994,0,True),'J102':(64,10),'J101':(64,92),'J202':(9,134),'J401':(9,65),'J109':(35,72),'J203':(13,103),'J404':(13,34),'J405':(15,59),'U403':(10,28),'U202':(10,96),'U401':(22,49,90),'U201':(22,119,90),'U501':(43,30,180),'U502':(56,14,90),'U302':(53,92,180),'U313':(44,92),'T301':(33,90,180),'U307':(30,98,180),'U304':(43,113),'U503':(13,12),'U505':(13,20),'U306':(13,82),'U308':(13,89),'T201':(12,126,90),'T202':(29,114,90),'T401':(12,56,90),'T402':(31,43,90)}
  for ref,loc in seeds.items():place(ref,*loc)
  holes=[(3.81,3.81),(66.04,3.81),(3.81,59.69),(66.04,59.69),(3.81,82.55),(66.04,82.55),(3.81,138.43),(66.04,138.43),(13.97,70),(55.88,70),(35,138.43)]
  for ref,loc in zip(['M1','M2','M3','M4','M5','M6','M7','M8','M9','M11','M12'],holes):place(ref,*loc)
 # Geometry and seed positions, followed by the electrical placement engine.
 electrical_place(name,b,fps,model,pin_net,placement,place,h)
 for ref,f in fps.items():
  audit[ref]['position_mm']=xy(f);audit[ref]['rotation_deg']=f.GetOrientationDegrees();audit[ref]['side']=f.GetLayerName()
 b.BuildConnectivity();p.SaveBoard(str(d/(name+'.kicad_pcb')),b)
 # FootprintLoad retains library UUIDs. Give every instance and child a stable,
 # project-unique ID; schematic adoption uses the separate path field.
 from build_legacy_schematics import sexp,Q,uid
 tree=sexp.load_file(d/(name+'.kicad_pcb'))
 def fresh(node,key):
  for j,it in enumerate(node):
   if isinstance(it,list):
    if str(it[0])=='uuid':it[1]=Q(uid(name+'/pcb/'+key+'/'+str(j)))
    else:fresh(it,key+'/'+str(j))
 fresh(tree,'root');sexp.save_file(d/(name+'.kicad_pcb'),tree)
 (vdir/'footprint-audit.json').write_text(json.dumps(audit,indent=2));(vdir/'placement.json').write_text(json.dumps(placement,indent=2))
 print(name,'staged',len(fps),'footprints',len(nets),'nets')

def electrical_place(name,b,fps,model,pin_net,placement,place,h):
 """Greedy connected placement with exhaustive local legal pad/body clearance.

 Rails are excluded from barycentres; rail-only capacitors are assigned to an
 IC on that rail. Subsequent reviewed placements can be supplied as JSON.
 """
 pads=lambda ref:{a.GetNumber():a for a in fps[ref].Pads() if a.GetNumber()}
 allpads={r:pads(r) for r in fps}
 rawnet=model['nets'];rails={n for n,ps in rawnet.items() if len(ps)>14 or n in ['AGND','DGND','DGND_TX','DGND_RX','DVDD','DVDD_TX','DVDD_RX','6V','1_8V','3_3V_RF','5V_RX','5V_TX','3_3V_RX','3_3V_TX']}
 # Body occupancy from copper and fabrication outline, with assembly spacing.
 def bounds(ref):
  f=fps[ref];bb=f.GetBoundingBox(False,False);a=(p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom()))
  return a
 # Footprint bounds above exclude user text but include courtyards/hidden fab.
 sizes={}
 for r,f in fps.items():
  bb=f.GetBoundingBox(False,False);sizes[r]=(max(.8,p.ToMM(bb.GetWidth())),max(.8,p.ToMM(bb.GetHeight())))
 fixed=set(placement);occupied={r:bounds(r) for r in fixed if fps[r].GetLayer()==p.F_Cu}
 # PTH connector and hole copper reserves space on both sides.
 for r in fixed:
  if fps[r].GetLayer()==p.B_Cu:
   for i,a in enumerate(fps[r].Pads()):
    if a.GetAttribute()==p.PAD_ATTRIB_NPTH:
     x,y=xy(a);occupied[r+str(i)]=(x-1,y-1,x+1,y+1)
 hintfile=ROOT/'scripts'/('placement-'+name+'.json')
 if hintfile.exists():
  for r,loc in json.loads(hintfile.read_text()).items():place(r,*loc);fixed.add(r);occupied[r]=bounds(r)
 def legal(bb,ignore=None):
  if bb[0]<1 or bb[1]<1 or bb[2]>68.85 or bb[3]>h-1:return False
  for r,other in occupied.items():
   if r==ignore:continue
   if bb[0]<other[2]+.18 and bb[2]>other[0]-.18 and bb[1]<other[3]+.18 and bb[3]>other[1]-.18:return False
  return True
 assigned=set(fixed);todo=set(fps)-assigned;usage=collections.Counter();targets={}
 # Locate decoupling's intended supply terminal in the original multi-unit
 # drawing. This prevents one large common rail attracting all bypass caps.
 bypass={}
 rawpages=json.loads((ROOT/'verification'/name/'pdf-vector-extraction.json').read_text())
 for page in rawpages:
  for part in page['parts']:
   rr=part['ref']
   if not rr.startswith('C'):continue
   options=[]
   for pp in part['pins']:
    net=pin_net.get((rr,pp['number']))
    if net not in rails or 'GND' in net:continue
    for ic in page['parts']:
     if not ic['ref'].startswith('U'):continue
     for ip in ic['pins']:
      if pin_net.get((ic['ref'],ip['number']))==net:options.append((math.dist(pp['xy'],ip['xy']),pp['number'],ic['ref'],ip['number']))
   if options:bypass[rr]=min(options)[1:]
 def connections(ref):
  con=[]
  for num,pa in allpads[ref].items():
   net=pin_net.get((ref,num))
   if not net or net in rails:continue
   for rr,pn in rawnet[net]:
    if rr!=ref and rr in assigned:con.append((num,rr,pn))
  return con
 while todo:
  choices=[(len(connections(r))+(10 if r in bypass else 5 if r.startswith('L') else 0),r) for r in sorted(todo)];_,ref=max(choices);con=connections(ref)
  anchors=[(num,xy(allpads[rr][pn]),rr) for num,rr,pn in con]
  if not anchors and ref in bypass:
   num,rr,pn=bypass[ref];anchors=[(num,xy(allpads[rr][pn]),rr)]
  if not anchors:
   # Prefer a local active device; keep bypass components on their relevant rail.
   relevant={pin_net.get((ref,num)) for num in allpads[ref]}-{'AGND','DGND','DGND_RX','DGND_TX',None}
   eligible=[r for r in assigned if r.startswith('U') and any(pin_net.get((r,pn)) in relevant for pn in allpads[r])]
   page=model['components'][ref]['source_pages'][0]
   if name=='WBX':eligible=[r for r in eligible if set(model['components'][r]['source_pages'])&set(model['components'][ref]['source_pages'])] or eligible
   if not eligible:eligible=[r for r in assigned if r.startswith('U')]
   rr=min(eligible,key=lambda r:usage[r]+(0 if model['components'][r]['source_pages'][0]==page else 20));usage[rr]+=1
   pp=[a for pn,a in allpads[rr].items() if pin_net.get((rr,pn)) in relevant];anchor=xy(pp[usage[rr]%len(pp)]) if pp else xy(fps[rr]);anchors=[(next(iter(allpads[ref])),anchor,rr)]
  tx=sum(a[1][0] for a in anchors)/len(anchors);ty=sum(a[1][1] for a in anchors)/len(anchors)
  best=None
  for radius in [0,1.5,2.5,3.5,4.5,6,8,10,13,17,22,30,40]:
   for j in range(1 if radius==0 else 24):
    angle=j*math.pi/12;x=round((tx+radius*math.cos(angle))*4)/4;y=round((ty+radius*math.sin(angle))*4)/4
    for rot in [0,90,180,270]:
     f=fps[ref];f.SetOrientationDegrees(rot);f.SetPosition(v(x,y));bb=bounds(ref)
     if not legal(bb):continue
     cost=sum(math.dist(xy(allpads[ref][num]),anchor) for num,anchor,rr in anchors)+radius*.03
     if best is None or cost<best[0]:best=(cost,x,y,rot,bb)
   if best is not None and radius>best[0]/len(anchors)+3:break
  if best is None:raise RuntimeError(('No legal placement',name,ref,tx,ty))
  _,x,y,rot,bb=best;place(ref,x,y,rot);occupied[ref]=bb;assigned.add(ref);todo.remove(ref);targets[ref]=anchors
 (ROOT/'verification'/name/'placement-targets.json').write_text(json.dumps(targets,indent=2))

if __name__=='__main__':
 for name in sys.argv[1:] or ['TVRX2','WBX']:build(name)
