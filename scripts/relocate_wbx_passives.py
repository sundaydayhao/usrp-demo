"""Small passive placement adjustments to provide legal through-via escapes.

No RF component is moved. Existing ordinary connections at old positions are
removed; final ERC/DRC and source-to-PCB comparison must be rerun.
"""
from wbx_geometry import *
import sys
targets=sys.argv[1:] or ['C529','C403','R531','R533','C505']
fs={f.GetReference():f for f in b.GetFootprints()};removed=set();moved=[];failed=[]
def box(obj):
 bb=obj.GetBoundingBox(False,False) if isinstance(obj,p.FOOTPRINT) else obj.GetBoundingBox()
 return bb.GetX()/1e6,bb.GetY()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6
def overlap(a,c,cl=0):return a[0]<c[2]+cl and a[2]>c[0]-cl and a[1]<c[3]+cl and a[3]>c[1]-cl
for ref in targets:
 f=fs[ref];ownnets={a.GetNetname() for a in f.Pads() if a.GetNetname()};assert not ownnets&rf,(ref,ownnets&rf)
 original=xy(f.GetPosition());oldpads=[box(a) for a in f.Pads()];best=None;trial=p.FOOTPRINT(f)
 offsets=sorted([(dx*.25,dy*.25) for dx in range(-32,33) for dy in range(-32,33) if 0<dx*dx+dy*dy<=1024],key=lambda q:q[0]**2+q[1]**2)
 for dx,dy in offsets:
  trial.SetPosition(vec((original[0]+dx,original[1]+dy)));fb=box(trial)
  if any(overlap(fb,box(o),.1) for o in fs.values() if o!=f and o.GetLayer()==p.F_Cu):continue
  tp=list(trial.Pads());hard=False
  for a in tp:
   net=a.GetNetname();q=xy(a.GetPosition());ab=box(a)
   for other in pads:
    if other.GetParentFootprint()==f or other.GetNetname()==net:continue
    cl=.15 if other.GetNetname() in rf else .127
    if overlap(ab,box(other),cl) and other.IsOnLayer(p.F_Cu):hard=True;break
    if net!='AGND' and bboxdist(q,q,box(other))<.225+cl:hard=True;break
   if hard:break
   for t in tracks:
    if t.m_Uuid.AsString() in removed or t.GetNetname()==net or (not t.IsLocked() and t.GetNetname() not in rf):continue
    ta,tc=xy(t.GetStart()),xy(t.GetEnd());via=isinstance(t,p.PCB_VIA);r=(t.GetWidth(p.F_Cu) if via else t.GetWidth())/2e6;cl=.15 if t.GetNetname() in rf else .127
    if (via or t.GetLayer()==p.F_Cu) and bboxdist(ta,tc,ab)<r+cl:hard=True;break
    if net!='AGND' and ps(q,ta,tc)<.225+r+cl:hard=True;break
   if hard:break
  if not hard:best=(original[0]+dx,original[1]+dy);break
 if best is None:failed.append(ref);continue
 f.SetPosition(vec(best));pads=[a for of in b.GetFootprints() for a in of.Pads()]
 # Preserve distant fixed IC escapes; old loose same-net routes are rerouted.
 for t in tracks:
  if t.GetNetname() in ownnets-{'AGND'} and not t.IsLocked():removed.add(t.m_Uuid.AsString())
 for a in f.Pads():
  if a.GetNetname()=='AGND' or not a.GetNetname():continue
  via=p.PCB_VIA(b);via.SetPosition(a.GetPosition());via.SetWidth(p.FromMM(.45));via.SetDrill(p.FromMM(.2));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNetCode(a.GetNetCode());via.SetLocked(True);b.Add(via);tracks.append(via)
 moved.append({'ref':ref,'from_mm':original,'to_mm':best});print(ref,original,'->',best,flush=True)
for t in tracks:
 if t.m_Uuid.AsString() in removed:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b);(vd/'passive-via-clearance-placement.json').write_text(json.dumps({'moved':moved,'failed':failed,'ordinary_tracks_removed':len(removed)},indent=2));print('Moved',len(moved),'failed',failed,'ripped',len(removed))
