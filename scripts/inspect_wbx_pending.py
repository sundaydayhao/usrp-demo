from wbx_geometry import *
b.BuildConnectivity()
for uc in json.loads((vd/'routed-drc.json').read_text())['unconnected_items']:
 print('\nNET',objs[uc['items'][0]['uuid']].GetNetname())
 for i in uc['items']:
  o=objs[i['uuid']];group=[objs[t.m_Uuid.AsString()] for t in b.GetConnectivity().GetConnectedItems(o) if t.m_Uuid.AsString() in objs]
  print(i['description'], 'pads',[(t.GetParentFootprint().GetReference(),t.GetNumber(),xy(t.GetPosition())) for t in group if isinstance(t,p.PAD)],'vias',[(xy(t.GetPosition())) for t in group if isinstance(t,p.PCB_VIA)])
