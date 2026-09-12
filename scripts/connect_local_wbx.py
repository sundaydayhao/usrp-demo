from wbx_geometry import *
b.BuildConnectivity()
def island(item):
 result={}
 for obj in b.GetConnectivity().GetConnectedItems(item):
  known=objs.get(obj.m_Uuid.AsString())
  if known is None:continue
  pp=points(known)
  if isinstance(known,p.PCB_TRACK) and not isinstance(known,p.PCB_VIA):
   a,c=pp;steps=max(1,math.ceil(math.dist(a,c)/1.0))
   pp+=[(a[0]+(c[0]-a[0])*i/steps,a[1]+(c[1]-a[1])*i/steps) for i in range(1,steps)]
  for layer in layers(known)&{p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu}:
   for pt in pp:result[layer,pt]=True
 return result
report=json.loads((vd/'routed-drc.json').read_text());added=[];failed=[]
for uc in sorted(report['unconnected_items'],key=lambda u:math.dist(tuple(u['items'][0]['pos'].values()),tuple(u['items'][1]['pos'].values()))):
 if len(uc['items'])!=2 or any(i['uuid'] not in objs for i in uc['items']):continue
 o1,o2=[objs[i['uuid']] for i in uc['items']];net=o1.GetNetname()
 if net in rf:continue
 part1,part2=island(o1),island(o2)
 if part1.keys()&part2.keys():continue
 candidates=sorted([(math.dist(a,c),l,a,c) for l,a in part1 for m,c in part2 if l==m])[:120];found=None
 for length,layer,a,c in candidates:
  width=.4 if net.startswith(('3_3V','5V','6V','DVDD')) and length>3 else .18
  for pathpts in routes(a,c):
   if any(not(.4<q[0]<69.45 and .4<q[1]<141.84) for q in pathpts):continue
   if all(clear(s,e,net,layer,width) for s,e in zip(pathpts,pathpts[1:])):found=(pathpts,layer,width);break
  if found:break
 if not found:failed.append(net);continue
 pts,layer,width=found
 for s,e in zip(pts,pts[1:]):
  if math.dist(s,e)<.001:continue
  t=p.PCB_TRACK(b);t.SetStart(vec(s));t.SetEnd(vec(e));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNetCode(o1.GetNetCode());b.Add(t);tracks.append(t);addobs(t);objs[t.m_Uuid.AsString()]=t
 added.append({'net':net,'layer':b.GetLayerName(layer),'width_mm':width,'path_mm':pts})
 b.BuildConnectivity();print('Connected',net,b.GetLayerName(layer),flush=True)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b);(vd/'local-connections.json').write_text(json.dumps({'added':added,'failed':failed},indent=2));print('Local connections added',len(added),'remaining candidates',len(failed))
