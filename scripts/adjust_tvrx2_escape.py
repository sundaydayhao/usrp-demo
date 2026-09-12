"""Find a clear C258 escape location against actual KiCad geometry."""
from pathlib import Path
import json,subprocess,math
import pcbnew as p
from build_advanced_boards import v
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/TVRX2/TVRX2.kicad_pcb';data=file.read_bytes();vd=ROOT/'verification/TVRX2';best=None
offsets=[(0,-.8),(-.8,0),(0,.8),(.8,0),(-.6,-.6),(.6,-.6),(-.6,.6),(.6,.6),(0,-1.2),(-1.2,0),(1.2,0),(0,1.2)]
for dx,dy in offsets:
 file.write_bytes(data);b=p.LoadBoard(str(file));old=v(47.73,43.25);new=v(47.73+dx,43.25+dy)
 via=next(t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetPosition()==old);net=via.GetNetCode();via.SetPosition(new)
 for t in b.GetTracks():
  if isinstance(t,p.PCB_VIA) or t.GetNetCode()!=net:continue
  if t.GetStart()==old:t.SetStart(new)
  if t.GetEnd()==old:t.SetEnd(new)
 t=p.PCB_TRACK(b);t.SetStart(old);t.SetEnd(new);t.SetLayer(p.F_Cu);t.SetWidth(p.FromMM(.18));t.SetNetCode(net);b.Add(t)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
 report=vd/'escape-location-drc.json';subprocess.run([r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe','pcb','drc','--format','json','--output',str(report),str(file)],check=True,capture_output=True)
 d=json.loads(report.read_text());score=(sum(x['severity']=='error' for x in d['violations']),len(d['unconnected_items']));print(dx,dy,score,flush=True)
 if best is None or score<best[0]:best=(score,file.read_bytes(),report.read_bytes(),[dx,dy])
 if score[0]==0:break
file.write_bytes(best[1]);(vd/'routed-drc.json').write_bytes(best[2]);(vd/'escape-location.json').write_text(json.dumps({'score':best[0],'offset':best[3]}));print('BEST',best[0])
