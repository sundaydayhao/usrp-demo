"""Import top-layer RF routes, lock them, add return vias and ground planes."""
from pathlib import Path
import json,math,sys,collections
import pcbnew as p
from build_advanced_boards import v,xy
ROOT=Path(__file__).resolve().parents[1]

def distseg(q,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];d=dx*dx+dy*dy
 t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/d)) if d else 0
 return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
def prepare(name,ground_only=False,rf_only=False):
 d=ROOT/'projects'/name;vd=ROOT/'verification'/name;file=d/(name+'.kicad_pcb');b=p.LoadBoard(str(file))
 if not ground_only:
  assert not list(b.GetTracks()),'Only import into reviewed placement; do not overwrite an existing route'
  ses=(vd/(name+'-rf.ses')).read_text()
  for c,e in json.loads((vd/'dsn-character-map.json').read_text()).items():ses=ses.replace(e,c)
  (vd/(name+'-rf-native.ses')).write_text(ses,encoding='utf-8')
  assert p.ImportSpecctraSES(b,str(vd/(name+'-rf-native.ses')))
 rf=json.loads((vd/'rf-net-classes.json').read_text());rfset=set(rf['RF50_START']+rf['RF_LOCAL']);routing=[]
 for t in b.GetTracks():
  assert not isinstance(t,p.PCB_VIA),'RF layer transition is not allowed'
  assert t.GetLayer()==p.F_Cu,'RF must stay on top'
  assert t.GetNetname() in rfset,(t.GetNetname(),'unrequested routing')
  t.SetLocked(True)
  routing.append((t.GetNetCode(),p.ToMM(t.GetWidth()),xy(t.GetStart()) if False else (p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y)),(p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y)),t.GetLayer()))
 if rf_only:p.SaveBoard(str(file),b);print(name,'imported',len(routing),'RF segments');return
 pads=[a for f in b.GetFootprints() for a in f.Pads() if a.IsOnLayer(p.F_Cu) or a.IsOnLayer(p.B_Cu)]
 obstacles=[]
 for a in pads:
  bb=a.GetBoundingBox();obstacles.append((a,a.GetNetCode(),(p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom()))))
 height=142.24 if name=='WBX' else 63.5
 vias=[]
 def clear_point(q,net,rad=.25,layer=None):
  if q[0]<.5 or q[0]>69.35 or q[1]<.5 or q[1]>height-.5:return False
  for a,nn,bb in obstacles:
   if nn==net and nn!=0:continue
   if layer is not None and not a.IsOnLayer(layer):continue
   dx=max(bb[0]-q[0],0,q[0]-bb[2]);dy=max(bb[1]-q[1],0,q[1]-bb[3])
   if math.hypot(dx,dy)<rad+.155:return False
  for nn,w,aa,bb,ll in routing:
   if nn==net or layer is not None and layer!=ll:continue
   if distseg(q,aa,bb)<rad+w/2+.155:return False
  for nn,pt in vias:
   if math.dist(q,pt)<(.45 if nn==net else .66):return False
  return True
 def clear_line(a,c,net,width=.18,layer=p.F_Cu):
  steps=max(1,math.ceil(math.dist(a,c)/.08))
  return all(clear_point((a[0]+(c[0]-a[0])*j/steps,a[1]+(c[1]-a[1])*j/steps),net,width/2,layer) for j in range(steps+1))
 def via(q,net):
  a=p.PCB_VIA(b);a.SetPosition(v(*q));a.SetWidth(p.FromMM(.5));a.SetDrill(p.FromMM(.25));a.SetViaType(p.VIATYPE_THROUGH);a.SetLayerPair(p.F_Cu,p.B_Cu);a.SetNetCode(net);a.SetLocked(True);b.Add(a);vias.append((net,q));return a
 def line(a,c,net,layer=p.F_Cu,width=.18):
  if math.dist(a,c)<.001:return
  t=p.PCB_TRACK(b);t.SetStart(v(*a));t.SetEnd(v(*c));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(net);t.SetLocked(True);b.Add(t);routing.append((net,width,a,c,layer))
 # Exposed pads get a distributed via array. Remaining ground pins get a
 # short, local return, outside the signal pad clearances on both surfaces.
 ground=[a for a in pads if a.GetNetname()=='AGND' and a.GetAttribute()==p.PAD_ATTRIB_SMD]
 failed=[]
 ground.sort(key=lambda a:-(a.GetSize().x*a.GetSize().y))
 for a in ground:
  net=a.GetNetCode();point=xy(a);f=a.GetParentFootprint();fc=xy(f);layer=p.F_Cu if a.IsOnLayer(p.F_Cu) else p.B_Cu
  w,h=p.ToMM(a.GetSize().x),p.ToMM(a.GetSize().y)
  if min(w,h)>1.7 and a.GetNumber() in ['25','33','41']:
   for xx in [-.65,0,.65]:
    for yy in [-.65,0,.65]:
     q=(point[0]+xx,point[1]+yy)
     if clear_point(q,net):via(q,net)
   continue
  if any(nn==net and math.dist(point,q)<.8 and clear_line(point,q,net,layer=layer) for nn,q in vias):
   q=min((q for nn,q in vias if nn==net and math.dist(point,q)<.8 and clear_line(point,q,net,layer=layer)),key=lambda q:math.dist(point,q));line(point,q,net,layer);continue
  theta=math.atan2(point[1]-fc[1],point[0]-fc[0]);found=None
  for radius in [.65,.85,1.1,1.4,1.8,2.4]:
   for offset in [0,math.pi/4,-math.pi/4,math.pi/2,-math.pi/2,3*math.pi/4,-3*math.pi/4,math.pi]:
    q=(round(point[0]+radius*math.cos(theta+offset),3),round(point[1]+radius*math.sin(theta+offset),3))
    if clear_point(q,net) and clear_line(point,q,net,layer=layer):found=q;break
   if found:break
  if found:via(found,net);line(point,found,net,layer)
  else:failed.append(f.GetReference()+'.'+a.GetNumber())
 agnd=b.FindNet('AGND')
 for layer in [p.In1_Cu,p.In2_Cu]:
  z=p.ZONE(b);z.SetLayer(layer);z.SetNet(agnd);z.SetLocalClearance(p.FromMM(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(p.FromMM(.15));z.SetIsFilled(False)
  o=z.Outline();o.NewOutline()
  for x,y in [(.3,.3),(69.55,.3),(69.55,height-.3),(.3,height-.3)]:o.Append(v(x,y))
  b.Add(z)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
 (vd/'ground-return-audit.json').write_text(json.dumps({'ground_vias':len(vias),'ground_pads_without_local_via':failed,'RF_tracks_locked':sum(1 for t in b.GetTracks() if t.GetNetname() in rfset)},indent=2))
 assert p.ExportSpecctraDSN(b,str(vd/(name+'-remaining.dsn')))
 # DSN's lexer does not accept tabs inside long pin lists, nor Unicode labels.
 text=(vd/(name+'-remaining.dsn')).read_text();esc=json.loads((vd/'dsn-character-map.json').read_text());esc.update({c:f'_U{ord(c):04X}_' for c in set(text) if ord(c)>127});(vd/'dsn-character-map.json').write_text(json.dumps(esc))
 for c,e in esc.items():text=text.replace(c,e)
 (vd/(name+'-remaining.dsn')).write_bytes(text.replace('\t','  ').replace('\r','').encode('ascii'))
 print(name,'RF tracks',sum(t.GetNetname() in rfset for t in b.GetTracks()),'ground vias',len(vias),'local return failures',failed)

if __name__=='__main__':
 for name in [s for s in sys.argv[1:] if not s.startswith('--')] or ['TVRX2','WBX']:prepare(name,'--ground-only' in sys.argv,'--rf-only' in sys.argv)
