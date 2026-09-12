"""Discard ordinary copper islands with no component pad connected."""
from pathlib import Path
import pcbnew as p,json,subprocess
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/WBX/WBX.kicad_pcb';vd=ROOT/'verification/WBX';report=vd/'routed-drc.json';d=json.loads(report.read_text());b=p.LoadBoard(str(file));b.BuildConnectivity();tracks=list(b.GetTracks());pads=[a for f in b.GetFootprints() for a in f.Pads()];objs={t.m_Uuid.AsString():t for t in tracks+pads};rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]));remove={};seen=set()
for u in d['unconnected_items']:
 for item in u['items']:
  uid=item['uuid'];t=objs.get(uid)
  if t is None or uid in seen or isinstance(t,p.PAD) or t.GetNetname() in rf:continue
  cluster={o.m_Uuid.AsString() for o in b.GetConnectivity().GetConnectedItems(t)};seen|=cluster
  if any(isinstance(objs.get(i),p.PAD) and objs[i].GetNumber() for i in cluster):continue
  remove.update({i:objs[i] for i in cluster if i in objs and isinstance(objs[i],p.PCB_TRACK)})
if remove:
 old=file.read_bytes();oldr=report.read_bytes()
 for t in remove.values():b.Remove(t)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
 subprocess.run([r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe','pcb','drc','--format','json','--output',str(report),str(file)],check=True,capture_output=True)
 after=json.loads(report.read_text())
 if len(after['unconnected_items'])>len(d['unconnected_items']):file.write_bytes(old);report.write_bytes(oldr);print('Kept copper: unexpected connectivity increase')
 else:print('Removed',len(remove),'items in pad-free copper islands; unconnected',len(d['unconnected_items']),'->',len(after['unconnected_items']))
else:print('No pad-free copper islands')
