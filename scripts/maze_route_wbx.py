"""Conservative F/In2/In3/B grid routing for ordinary WBX connections.

In1 is never a signal-routing layer. RF copper is an immutable obstacle.
Every candidate is also checked against exact segment/rectangle geometry.
"""
from pathlib import Path as _PausePath
if (_PausePath(__file__).resolve().parents[1]/'tmp/pause-wbx-routing').exists():raise SystemExit('Routing paused at a saved checkpoint.')
from wbx_geometry import *
from PIL import Image,ImageDraw
import heapq,time,sys
RIP='--rip' in sys.argv;SOFT=set();soft_images=[];removed_hold=[]
def track_key(net,layer,line):return (net,layer,tuple(line))
def clear(a,c,net,layer,width):
 margin=width/2+.15;left,right=min(a[0],c[0]),max(a[0],c[0]);top,bottom=min(a[1],c[1]),max(a[1],c[1])
 for nn,ls,box,line,r in obs:
  if nn==net or layer not in ls or left>box[2]+margin or right<box[0]-margin or top>box[3]+margin or bottom<box[1]-margin:continue
  if RIP and line and track_key(nn,layer,line) in SOFT:continue
  cl=.15 if nn in rf else .127
  if (dist(a,c,*line)-r if line else bboxdist(a,c,box))<width/2+cl-.000002:return False
 return True
GRID=.05;NX=1400;NY=2850;LS=[p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu];N=NX*NY
b.BuildConnectivity()
def island(item):
 result=[]
 for obj in b.GetConnectivity().GetConnectedItems(item):
  known=objs.get(obj.m_Uuid.AsString())
  if known is None:continue
  pp=points(known)
  if isinstance(known,p.PCB_TRACK) and not isinstance(known,p.PCB_VIA):
   a,c=pp;steps=max(1,math.ceil(math.dist(a,c)/.6));pp+=[(a[0]+(c[0]-a[0])*i/steps,a[1]+(c[1]-a[1])*i/steps) for i in range(1,steps)]
  for layer in layers(known)&set(LS):
   result.extend((LS.index(layer),q) for q in pp)
 return result
def masks(net,width):
 global SOFT,soft_images
 SOFT={track_key(t.GetNetname(),t.GetLayer(),(xy(t.GetStart()),xy(t.GetEnd()))) for t in tracks if not isinstance(t,p.PCB_VIA) and not t.IsLocked() and t.GetNetname() not in rf and t.GetLayer() in [p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu]} if RIP else set()
 ims=[Image.new('L',(NX,NY),0) for _ in LS];vi=Image.new('L',(NX,NY),0);ds=[ImageDraw.Draw(im) for im in ims];dv=ImageDraw.Draw(vi)
 soft=[Image.new('L',(NX,NY),0) for _ in LS];sd=[ImageDraw.Draw(im) for im in soft]
 def draw(drawer,box,line,r,margin):
  if line:
   rad=r+margin;coords=[(a/GRID,c/GRID) for a,c in line];drawer.line(coords,fill=255,width=math.ceil(2*rad/GRID))
   for x,y in coords:drawer.ellipse((x-rad/GRID,y-rad/GRID,x+rad/GRID,y+rad/GRID),fill=255)
  else:drawer.rectangle(((box[0]-margin)/GRID,(box[1]-margin)/GRID,(box[2]+margin)/GRID,(box[3]+margin)/GRID),fill=255)
 for nn,layerset,box,line,r in obs:
  if nn==net:continue
  cl=.15 if nn in rf else .127
  if not nn:cl=.25
  for i,l in enumerate(LS):
   if l in layerset:draw(sd[i] if line and track_key(nn,l,line) in SOFT else ds[i],box,line,r,cl+width/2+(.02 if l==p.In3_Cu else .03))
  if layerset:draw(dv,box,line,r,cl+.225+.08)
 for d in ds+[dv]:
  d.rectangle((0,0,NX-1,4),fill=255);d.rectangle((0,NY-6,NX-1,NY-1),fill=255);d.rectangle((0,0,4,NY-1),fill=255);d.rectangle((NX-6,0,NX-1,NY-1),fill=255)
 soft_images=[im.tobytes() for im in soft]
 return [im.tobytes() for im in ims],vi.tobytes()
def seed_points(pp,mask,net,width):
 out={}
 for l,q in pp:
  x,y=round(q[0]/GRID),round(q[1]/GRID)
  for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)]:
   xx,yy=x+dx,y+dy;idx=yy*NX+xx
   if 0<=xx<NX and 0<=yy<NY and not mask[l][idx] and clear(q,(xx*GRID,yy*GRID),net,LS[l],width):out[l*N+idx]=q
 return out
def route(o1,o2,net):
 power=net.startswith(('3_3V','5V','6V','DVDD'));width=.4 if power and net!='3_3V_TX' else .18
 # Exact geometry can use legal gaps that the conservative raster closes.
 if p.In3_Cu in LS:
  ix=LS.index(p.In3_Cu);aa=[q for l,q in island(o1) if l==ix];cc=[q for l,q in island(o2) if l==ix]
  for _,a,c in sorted((math.dist(a,c),a,c) for a in aa for c in cc)[:100]:
   for pathpts in routes(a,c):
    if any(q[0]<.4 or q[0]>69.45 or q[1]<.4 or q[1]>141.84 for q in pathpts):continue
    if all(clear(s,e,net,p.In3_Cu,width) for s,e in zip(pathpts,pathpts[1:])):
     return ([(s,e,p.In3_Cu,width) for s,e in zip(pathpts,pathpts[1:]) if math.dist(s,e)>.001],set()),'exact In3 geometry'
 # Try nominal power width; escape necks are handled separately if required.
 mask,vm=masks(net,width);sp=seed_points(island(o1),mask,net,width);tp=seed_points(island(o2),mask,net,width)
 if not sp or not tp:return None,'no legal grid entry'
 goals=set(tp);gxy=[(idx%N%NX,idx%N//NX) for idx in goals];xmin=min(q[0] for q in gxy);xmax=max(q[0] for q in gxy);ymin=min(q[1] for q in gxy);ymax=max(q[1] for q in gxy)
 allxy=gxy+[(idx%N%NX,idx%N//NX) for idx in sp];bound=(max(4,min(q[0] for q in allxy)-200),max(4,min(q[1] for q in allxy)-200),min(NX-5,max(q[0] for q in allxy)+200),min(NY-5,max(q[1] for q in allxy)+200))
 def heuristic(idx):
  x,y=idx%N%NX,idx%N//NX;return max(0,xmin-x,x-xmax,ymin-y,y-ymax)*10
 heap=[(heuristic(idx),0,idx) for idx in sp];heapq.heapify(heap);cost={idx:0 for idx in sp};prev={};start=time.time();finished=None;expanded=0
 while heap and time.time()-start<40 and expanded<2200000:
  _,val,u=heapq.heappop(heap)
  if val!=cost.get(u):continue
  if u in goals:finished=u;break
  expanded+=1;l=u//N;i=u%N;x=i%NX;y=i//NX;neighbors=[]
  for dx,dy,w in [(-1,0,10),(1,0,10),(0,-1,10),(0,1,10),(-1,-1,14),(1,1,14),(-1,1,14),(1,-1,14)]:
   xx,yy=x+dx,y+dy;j=yy*NX+xx
   if bound[0]<=xx<=bound[2] and bound[1]<=yy<=bound[3] and not mask[l][j]:neighbors.append((l*N+j,w+(100 if soft_images[l][j] else 0)))
  if not vm[i]:neighbors.extend((other*N+i,200) for other in range(len(LS)) if other!=l and not mask[other][i])
  for dest,w in neighbors:
   nv=val+w
   if nv<cost.get(dest,10**15):cost[dest]=nv;prev[dest]=u;heapq.heappush(heap,(nv+heuristic(dest)*1.35,nv,dest))
 if finished is None:return None,f'no path ({expanded} cells)'
 seq=[finished]
 while seq[-1] in prev:seq.append(prev[seq[-1]])
 seq.reverse();segments=[];vias=[];last=sp[seq[0]];layer=seq[0]//N
 points3=[(u//N,(u%N%NX*GRID,u%N//NX*GRID)) for u in seq];points3.insert(0,(layer,last));points3.append((finished//N,tp[finished]))
 # Collapse only collinear grid steps, retaining layer transitions.
 simple=[]
 for entry in points3:
  if simple and entry==simple[-1]:continue
  if len(simple)>=2 and simple[-2][0]==simple[-1][0]==entry[0]:
   a,c,e=simple[-2][1],simple[-1][1],entry[1]
   if abs((c[0]-a[0])*(e[1]-c[1])-(c[1]-a[1])*(e[0]-c[0]))<1e-8:simple.pop()
  simple.append(entry)
 for (l,a),(m,c) in zip(simple,simple[1:]):
  if l!=m:
   if math.dist(a,c)>.001:return None,'invalid transition'
   vias.append(a)
  elif math.dist(a,c)>.001:
   if not clear(a,c,net,LS[l],width):return None,'exact clearance rejected'
   segments.append((a,c,LS[l],width))
 for q in set(vias):
  for nn,ls,box,line,r in obs:
   if nn==net or not ls:continue
   cl=.25 if not nn else .15 if nn in rf else .127
   if (ps(q,*line)-r if line else bboxdist(q,q,box))<.225+cl-.000002:return None,'exact via clearance rejected'
 return (segments,set(vias)),f'{expanded} cells'
report=json.loads((vd/'routed-drc.json').read_text());log=[]
report['unconnected_items'].sort(key=lambda u:0 if any(i['uuid'] in objs and objs[i['uuid']].GetNetname() in ['io_tx_04','io_tx_09'] for i in u['items']) else 1)
for uc in report['unconnected_items']:
 if len(uc['items'])!=2 or any(i['uuid'] not in objs for i in uc['items']):continue
 o1,o2=[objs[i['uuid']] for i in uc['items']];net=o1.GetNetname()
 if net in rf:continue
 if any(o.m_Uuid.AsString()==o2.m_Uuid.AsString() for o in b.GetConnectivity().GetConnectedItems(o1)):continue
 candidate,why=route(o1,o2,net)
 if candidate:
  segments,vias=candidate
  ripped=[]
  if RIP:
   for old in list(tracks):
    if isinstance(old,p.PCB_VIA) or old.IsLocked() or old.GetNetname() in rf or old.GetNetname()==net:continue
    oa,oc=xy(old.GetStart()),xy(old.GetEnd())
    if any(layer==old.GetLayer() and dist(a,c,oa,oc)<(width+old.GetWidth()/1e6)/2+.127 for a,c,layer,width in segments):
     uid=old.m_Uuid.AsString();ripped.append(old.GetNetname());obs[:]=[ob for ob in obs if not(ob[0]==old.GetNetname() and ob[3]==(oa,oc) and old.GetLayer() in ob[1])];removed_hold.append(old);b.Remove(old);tracks.remove(old);objs.pop(uid,None)
   if ripped:print('Ripped ordinary routing segments:',len(ripped),sorted(set(ripped)),flush=True)
  for q in vias:
   v=p.PCB_VIA(b);v.SetPosition(vec(q));v.SetWidth(p.FromMM(.45));v.SetDrill(p.FromMM(.2));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNetCode(o1.GetNetCode());v.SetLocked(RIP);b.Add(v);tracks.append(v)
  for a,c,layer,width in segments:
   t=p.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(c));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(o1.GetNetCode());t.SetLocked(RIP);b.Add(t);tracks.append(t)
  b.BuildConnectivity()
 print(net,'CONNECTED' if candidate else 'pending',why,flush=True);log.append({'net':net,'connected':bool(candidate),'detail':why})
 if candidate:break
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b);(vd/'maze-routing.json').write_text(json.dumps(log,indent=2))
