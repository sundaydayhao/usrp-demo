"""Through-via escapes within original USRP1 connector lands."""
from wbx_geometry import *
pending={objs[i['uuid']].GetNetname() for u in json.loads((vd/'routed-drc.json').read_text())['unconnected_items'] for i in u['items'] if i['uuid'] in objs};removed=set();added=[];failed=[]
for pad in pads:
 if pad.GetParentFootprint().GetReference() not in ['J402','J201'] or pad.GetNetname() not in pending or pad.GetNetname() in rf:continue
 net=pad.GetNetname();a=xy(pad.GetPosition());best=None
 for dy in [0,.3,-.3,.6,-.6,.9,-.9,1.15,-1.15]:
  for dx in [0,.08,-.08]:
   q=(a[0]+dx,a[1]+dy);hard=False;hits=set()
   if any(isinstance(t,p.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),q)<.5 for t in tracks if t.m_Uuid.AsString() not in removed):continue
   for other in pads:
    if other.GetNetname()==net:continue
    bb=other.GetBoundingBox();box=(bb.GetX()/1e6,bb.GetY()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6);cl=.25 if other.GetAttribute()==p.PAD_ATTRIB_NPTH else .15 if other.GetNetname() in rf else .127
    if bboxdist(q,q,box)<.225+cl:hard=True;break
   if hard:continue
   for t in tracks:
    uid=t.m_Uuid.AsString()
    if uid in removed or t.GetNetname()==net:continue
    via=isinstance(t,p.PCB_VIA);r=(t.GetWidth(p.F_Cu) if via else t.GetWidth())/2e6;cl=.15 if t.GetNetname() in rf else .127
    if ps(q,xy(t.GetStart()),xy(t.GetEnd()))<.225+r+cl:
     if t.IsLocked() or t.GetNetname() in rf:hard=True;break
     hits.add(uid)
   if hard:continue
   score=10*len(hits)+abs(dy)+abs(dx)
   if best is None or score<best[0]:best=(score,q,hits)
 if best is None:failed.append([pad.GetNumber(),net]);continue
 _,q,hits=best;removed|=hits
 via=p.PCB_VIA(b);via.SetPosition(vec(q));via.SetWidth(p.FromMM(.45));via.SetDrill(p.FromMM(.2));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNetCode(pad.GetNetCode());via.SetLocked(True);b.Add(via);tracks.append(via)
 added.append({'ref':pad.GetParentFootprint().GetReference(),'pin':pad.GetNumber(),'net':net,'xy_mm':q})
for t in tracks:
 if t.m_Uuid.AsString() in removed:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b);(vd/'connector-escapes.json').write_text(json.dumps({'added':added,'failed':failed,'ripped':len(removed)},indent=2));print('Connector vias',len(added),'ripped',len(removed),'no space',failed)
