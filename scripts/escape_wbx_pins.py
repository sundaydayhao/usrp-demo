"""Find short, clearance-checked escapes for trapped ordinary WBX QFN pins.

Candidate geometry is conservative; KiCad DRC remains the acceptance check.
RF traces, all pads and locked copper are hard obstacles. Ordinary conflicting
routes may be ripped, then routed again with these escapes fixed.
"""
from pathlib import Path
import pcbnew as p
import json,math,sys
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'projects/WBX/WBX.kicad_pcb';vd=ROOT/'verification/WBX'
b=p.LoadBoard(str(path));rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]))
def xy(q):return q.x/1e6,q.y/1e6
def v(q):return p.VECTOR2I(round(q[0]*1e6),round(q[1]*1e6))
def point_segment(q,a,c):
 dx,dy=c[0]-a[0],c[1]-a[1];den=dx*dx+dy*dy;t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/den)) if den else 0
 return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
def intersects(a,c,d,e):
 def cross(a,c,d):return (c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0])
 return cross(a,c,d)*cross(a,c,e)<0 and cross(d,e,a)*cross(d,e,c)<0
def segment_distance(a,c,d,e):return 0 if intersects(a,c,d,e) else min(point_segment(a,d,e),point_segment(c,d,e),point_segment(d,a,c),point_segment(e,a,c))
def rect_distance(a,c,box):
 x,y,r,s=box
 if x<=a[0]<=r and y<=a[1]<=s or x<=c[0]<=r and y<=c[1]<=s:return 0
 ps=[(x,y),(r,y),(r,s),(x,s)];return min(segment_distance(a,c,ps[i],ps[(i+1)%4]) for i in range(4))
pads=[a for f in b.GetFootprints() for a in f.Pads()];padmap={a.m_Uuid.AsString():a for a in pads};tracks=list(b.GetTracks());removed=set();new=[]
unconnected=json.loads((vd/'routed-drc.json').read_text())['unconnected_items'];wanted=[]
allobjects={t.m_Uuid.AsString():t for t in pads+tracks};pending_nets={allobjects[i['uuid']].GetNetname() for uc in unconnected for i in uc['items'] if i['uuid'] in allobjects}
for a in pads:
 allowed=a.GetNetname() in pending_nets and a.GetParentFootprint().GetLayer()==p.F_Cu and a.GetNetname() not in rf and a.GetNetname() and not a.GetNetname().startswith('unconnected-')
 ref_filter=next((s[7:].split(',') for s in sys.argv[1:] if s.startswith('--refs=')),None)
 if allowed and (a.GetParentFootprint().GetReference() in ref_filter if ref_filter else len(sys.argv)>1 or a.GetParentFootprint().GetReference() in ['U201','U401','U501','U302','U304','U307']):wanted.append(a)
accepted=[];failed=[]
for pad in wanted:
 net=pad.GetNetname();a=xy(pad.GetPosition());center=xy(pad.GetParentFootprint().GetPosition());dx,dy=a[0]-center[0],a[1]-center[1];ux,uy=(math.copysign(1,dx),0) if abs(dx)>abs(dy) else (0,math.copysign(1,dy));best=None
 if any(isinstance(t,p.PCB_VIA) and t.GetNetname()==net and math.dist(a,xy(t.GetPosition()))<.4 for t in tracks if t.m_Uuid.AsString() not in removed):continue
 for outward in [0,.25,.5,.75,1,1.25,1.5,2,2.5,-.15,-.3]:
  for lateral in [0,.2,-.2,.4,-.4,.6,-.6,.8,-.8,1,-1,1.2,-1.2,1.5,-1.5,2,-2]:
   q=(a[0]+ux*outward-uy*lateral,a[1]+uy*outward+ux*lateral);k=(a[0]+ux*min(.3,outward),a[1]+uy*min(.3,outward));segs=[(a,k),(k,q)];hits=set();hard=False
   for other in pads:
    if other.GetNetname()==net:continue
    bb=other.GetBoundingBox();box=(bb.GetX()/1e6,bb.GetY()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6)
    clearance=.15 if other.GetNetname() in rf else .127
    if rect_distance(q,q,box)<.225+clearance or (other.IsOnLayer(p.F_Cu) and any(rect_distance(s,e,box)<.09+clearance for s,e in segs)):
     hard=True;break
   if hard:continue
   for t in tracks:
    uid=t.m_Uuid.AsString()
    if uid in removed or t.GetNetname()==net:continue
    ta,tc=xy(t.GetStart()),xy(t.GetEnd());cl=.15 if t.GetNetname() in rf else .127;r=(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2e6
    hit=point_segment(q,ta,tc)<.225+r+cl or ((isinstance(t,p.PCB_VIA) or t.GetLayer()==p.F_Cu) and any(segment_distance(s,e,ta,tc)<.09+r+cl for s,e in segs))
    if hit:
     if t.IsLocked() or t.GetNetname() in rf:hard=True;break
     hits.add(uid)
   if hard:continue
   score=len(hits)*10+outward+abs(lateral)*2
   if best is None or score<best[0]:best=(score,q,k,hits)
 if best is None:failed.append([pad.GetParentFootprint().GetReference(),pad.GetNumber(),net]);continue
 _,q,k,hits=best;removed|=hits
 via=p.PCB_VIA(b);via.SetPosition(v(q));via.SetWidth(p.FromMM(.45));via.SetDrill(p.FromMM(.2));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNetCode(pad.GetNetCode());via.SetLocked(True);b.Add(via);tracks.append(via);new.append(via)
 for s,e in [(a,k),(k,q)]:
  if math.dist(s,e)<.001:continue
  t=p.PCB_TRACK(b);t.SetStart(v(s));t.SetEnd(v(e));t.SetWidth(p.FromMM(.18));t.SetLayer(p.F_Cu);t.SetNetCode(pad.GetNetCode());t.SetLocked(True);b.Add(t);tracks.append(t);new.append(t)
 accepted.append({'ref':pad.GetParentFootprint().GetReference(),'pin':pad.GetNumber(),'net':net,'via_mm':q,'ripped':len(hits)})
for t in tracks:
 if t.m_Uuid.AsString() in removed:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b)
(vd/'QFN-escape-additions.json').write_text(json.dumps({'added':accepted,'failed':failed,'ripped':len(removed)},indent=2));print('Added',len(accepted),'escapes, ripped',len(removed),'ordinary items; no space',failed)
