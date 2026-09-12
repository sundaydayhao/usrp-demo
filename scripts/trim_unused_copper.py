"""Remove DRC-reported unused copper only while connectivity remains intact."""
from pathlib import Path
import json,subprocess,sys
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];name=sys.argv[1];file=ROOT/'projects'/name/(name+'.kicad_pcb');vd=ROOT/'verification'/name;rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]))
for iteration in range(1):
 report=vd/'routed-drc.json';subprocess.run([r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe','pcb','drc','--format','json','--output',str(report),str(file)],check=True,capture_output=True)
 d=json.loads(report.read_text());old=file.read_bytes();old_report=report.read_bytes();before=len(d['unconnected_items']);ids={v['items'][0]['uuid'] for v in d['violations'] if v['type'] in ['track_dangling','via_dangling']}
 if not ids:print(name,'no dangling copper');break
 b=p.LoadBoard(str(file));tracks=list(b.GetTracks());remove=[t for t in tracks if t.m_Uuid.AsString() in ids and t.GetNetname() not in rf]
 if not remove:break
 for t in remove:b.Remove(t)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
 subprocess.run([r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe','pcb','drc','--format','json','--output',str(report),str(file)],check=True,capture_output=True)
 after=json.loads(report.read_text())
 if len(after['unconnected_items'])>before:
  file.write_bytes(old);report.write_bytes(old_report);print('Kept copper: removal would break a connection');break
 print(name,'removed',len(remove),'unused items; remaining unconnected',before,flush=True)
