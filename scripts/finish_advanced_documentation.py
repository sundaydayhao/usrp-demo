"""Apply the declared stack and readable assembly/connector identification."""
from pathlib import Path
import sys,math,json
import pcbnew as p
from build_advanced_boards import v
from build_legacy_schematics import sexp,n,Q,S
ROOT=Path(__file__).resolve().parents[1]
def apply(name):
 file=ROOT/'projects'/name/(name+'.kicad_pcb');b=p.LoadBoard(str(file));h=142.24 if name=='WBX' else 63.5;occupied={p.F_Cu:[],p.B_Cu:[]}
 def bbox(obj):
  a=obj.GetBoundingBox(False,False) if isinstance(obj,p.FOOTPRINT) else obj.GetBoundingBox();return (p.ToMM(a.GetX())-.2,p.ToMM(a.GetY())-.2,p.ToMM(a.GetRight())+.2,p.ToMM(a.GetBottom())+.2)
 def overlap(a,c):return a[0]<c[2] and a[2]>c[0] and a[1]<c[3] and a[3]>c[1]
 for f in b.GetFootprints():
  side=f.GetLayer();field=f.Reference();field.SetLayer(p.B_Fab if side==p.B_Cu else p.F_Fab);field.SetVisible(True);field.SetPosition(f.GetPosition());field.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));field.SetTextSize(v(.6,.6));field.SetTextThickness(p.FromMM(.08));field.SetMirrored(side==p.B_Cu);f.Value().SetVisible(False)
  occupied[side].append(bbox(f))
  for pad in f.Pads():
   if pad.GetAttribute() in [p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH]:
    occupied[p.F_Cu].append(bbox(pad));occupied[p.B_Cu].append(bbox(pad))
 for via in b.GetTracks():
  if isinstance(via,p.PCB_VIA):
   occupied[p.F_Cu].append(bbox(via));occupied[p.B_Cu].append(bbox(via))
 # Remove only our previously generated board-level labels.
 removed_labels=[]
 for t in list(b.GetDrawings()):
  if isinstance(t,p.PCB_TEXT) and t.GetText().startswith('ID '):removed_labels.append(t);b.Remove(t)
 labels={'TVRX2':{'J100':'RX1','J140':'RX2','J280':'JTAG','J2':'USRP1 RX'},'WBX':{'J101':'RX','J102':'TX','J202':'RX LO','J401':'TX LO','J201':'USRP1 RX','J402':'USRP1 TX','J109':'QTE ALT'}}[name]
 placed=[]
 for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
  ref=f.GetReference()
  if not ref.startswith(('U','J')):continue
  label='ID '+ref+(' '+labels[ref] if ref in labels else '');side=f.GetLayer();cx,cy=p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y);text=p.PCB_TEXT(b);text.SetText(label);text.SetTextSize(v(.75,.75));text.SetTextThickness(p.FromMM(.11));text.SetLayer(p.B_SilkS if side==p.B_Cu else p.F_SilkS);text.SetMirrored(side==p.B_Cu);text.SetPosition(v(cx,cy));tbb=bbox(text);w=(tbb[2]-tbb[0])/2;hh=(tbb[3]-tbb[1])/2;found=None
  for radius in [.8,1.5,2.5,3.5,4.5,6,8,10,12,15,18]:
   for angle in [-90,90,0,180,-45,45,135,225]:
    x=cx+radius*math.cos(math.radians(angle));y=cy+radius*math.sin(math.radians(angle));r=(x-w,y-hh,x+w,y+hh)
    if r[0]>.5 and r[1]>.5 and r[2]<69.35 and r[3]<h-.5 and not any(overlap(r,q) for q in occupied[side]):found=(x,y,r);break
   if found:break
  if found:text.SetPosition(v(*found[:2]));b.Add(text);occupied[side].append(found[2]);placed.append(ref)
 p.SaveBoard(str(file),b)
 doc=sexp.load_file(file);setup=sexp.find(doc,'setup');setup[:]=[x for x in setup if not(isinstance(x,list) and str(x[0])=='stackup')];stack=n('stackup')
 stack_layers=[('F.Cu','copper',.035,None),('dielectric 1','prepreg',.2104,4.4),('In1.Cu','copper',.0152,None),('dielectric 2','core',1.065,4.6),('In2.Cu','copper',.0152,None),('dielectric 3','prepreg',.2104,4.4),('B.Cu','copper',.035,None)]
 if name=='WBX':stack_layers=[('F.Cu','copper',.035,None),('dielectric 1','prepreg',.2104,4.4),('In1.Cu','copper',.0152,None),('dielectric 2','core',.3,4.6),('In2.Cu','copper',.0152,None),('dielectric 3','prepreg',.42,4.4),('In3.Cu','copper',.0152,None),('dielectric 4','core',.3,4.6),('In4.Cu','copper',.0152,None),('dielectric 5','prepreg',.2104,4.4),('B.Cu','copper',.035,None)]
 for layer,typ,thick,er in stack_layers:
  z=n('layer',Q(layer),n('type',Q(typ)),n('thickness',thick))
  if er:z.extend([n('material',Q('FR4 custom prepreg - confirm with fabricator' if name=='WBX' and typ=='prepreg' else 'FR4 7628' if typ=='prepreg' else 'FR4')),n('epsilon_r',er),n('loss_tangent',.02)])
  stack.append(z)
 stack.extend([n('copper_finish',Q('ENIG')),n('dielectric_constraints',S('yes'))]);setup.insert(1,stack);sexp.save_file(file,doc)
 (ROOT/'verification'/name/'assembly-labels.json').write_text(json.dumps({'silkscreen_IC_connector_refs':placed,'all_references_on_fabrication_layers':True,'stackup':'Custom 6-layer nominal 1.6 mm; fabricator confirmation required' if name=='WBX' else 'JLC04161H-7628 nominal 1.6 mm starting specification'},indent=2));print(name,'stack and assembly identification applied')
if __name__=='__main__':
 for name in sys.argv[1:]:apply(name)
