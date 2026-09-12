"""Route residual same-layer connections with explicit obstacle checks.

No component moves, RF changes, ground-reference traces or clearance changes.
"""
from pathlib import Path
import json,math
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'projects/WBX/WBX.kicad_pcb';vd=ROOT/'verification/WBX';b=p.LoadBoard(str(path));rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]))
def xy(q):return q.x/1e6,q.y/1e6
def vec(q):return p.VECTOR2I(round(q[0]*1e6),round(q[1]*1e6))
def ps(q,a,c):
 dx,dy=c[0]-a[0],c[1]-a[1];den=dx*dx+dy*dy;u=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/den)) if den else 0
 return math.hypot(q[0]-a[0]-u*dx,q[1]-a[1]-u*dy)
def dist(a,c,d,e):
 def cross(a,c,d):return (c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0])
 if cross(a,c,d)*cross(a,c,e)<0 and cross(d,e,a)*cross(d,e,c)<0:return 0
 return min(ps(a,d,e),ps(c,d,e),ps(d,a,c),ps(e,a,c))
def bboxdist(a,c,r):
 x,y,xx,yy=r
 if x<=a[0]<=xx and y<=a[1]<=yy or x<=c[0]<=xx and y<=c[1]<=yy:return 0
 corners=[(x,y),(xx,y),(xx,yy),(x,yy)];return min(dist(a,c,corners[i],corners[(i+1)%4]) for i in range(4))
pads=[a for f in b.GetFootprints() for a in f.Pads()];tracks=list(b.GetTracks());objs={t.m_Uuid.AsString():t for t in pads+tracks};obs=[]
for a in pads:
 bb=a.GetBoundingBox();obs.append((a.GetNetname(),{l for l in [p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu] if a.IsOnLayer(l)},(bb.GetX()/1e6,bb.GetY()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6),None,0))
def addobs(t):
 via=isinstance(t,p.PCB_VIA);a,c=xy(t.GetStart()),xy(t.GetEnd());rad=(t.GetWidth(p.F_Cu) if via else t.GetWidth())/2e6
 obs.append((t.GetNetname(),{p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu} if via else {t.GetLayer()},(min(a[0],c[0])-rad,min(a[1],c[1])-rad,max(a[0],c[0])+rad,max(a[1],c[1])+rad),(a,c),rad))
for t in tracks:addobs(t)
def clear(a,c,net,layer,width):
 left,right=min(a[0],c[0]),max(a[0],c[0]);top,bottom=min(a[1],c[1]),max(a[1],c[1]);margin=width/2+.15
 for n,ls,box,line,r in obs:
  if n==net or layer not in ls or left>box[2]+margin or right<box[0]-margin or top>box[3]+margin or bottom<box[1]-margin:continue
  cl=.15 if n in rf else .127
  if (dist(a,c,*line)-r if line else bboxdist(a,c,box))<width/2+cl-.000002:return False
 return True
def points(o):return [xy(o.GetPosition())] if isinstance(o,(p.PAD,p.PCB_VIA)) else [xy(o.GetStart()),xy(o.GetEnd())]
def layers(o):return {l for l in [p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu] if o.IsOnLayer(l)} if isinstance(o,p.PAD) else {p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu} if isinstance(o,p.PCB_VIA) else {o.GetLayer()}
def routes(a,c):
 yield [a,c]
 yield [a,(a[0],c[1]),c];yield [a,(c[0],a[1]),c]
 dx,dy=c[0]-a[0],c[1]-a[1];d=min(abs(dx),abs(dy));sx,sy=math.copysign(1,dx),math.copysign(1,dy)
 yield [a,(a[0]+sx*d,a[1]+sy*d),c];yield [a,(c[0]-sx*d,c[1]-sy*d),c]
 for offset in [0,-.5,.5,-1,1,-1.5,1.5,-2,2,-3,3,-4,4,-6,6]:
  for x in [a[0]+offset,c[0]+offset,(a[0]+c[0])/2+offset]:yield [a,(x,a[1]),(x,c[1]),c]
  for y in [a[1]+offset,c[1]+offset,(a[1]+c[1])/2+offset]:yield [a,(a[0],y),(c[0],y),c]
