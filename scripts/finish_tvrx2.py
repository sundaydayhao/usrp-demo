"""Evaluate a small set of explicit last-connection routes with KiCad DRC.

All candidates retain the reviewed RF copper. The two control nets imported
on In1 are moved to a signal layer to restore the uninterrupted RF reference.
"""
from pathlib import Path
import itertools,json,subprocess,shutil
import pcbnew as p
from build_advanced_boards import v
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/TVRX2/TVRX2.kicad_pcb';vd=ROOT/'verification/TVRX2';cp=ROOT/'tmp/checkpoints/TVRX2/TVRX2-before-final-connection.kicad_pcb'
if not cp.exists():shutil.copy2(file,cp)
best=None
for layer1,layer2,caplayer,style in itertools.product([p.In2_Cu,p.B_Cu],repeat=4):
 # Reuse the two integer layer options as a 2-way path choice.
 file.write_bytes(cp.read_bytes());b=p.LoadBoard(str(file))
 for t in b.GetTracks():
  if not isinstance(t,p.PCB_VIA) and t.GetLayer()==p.In1_Cu:t.SetLayer(layer1 if t.GetNetname()=='io_rx_03' else layer2)
 cap=next(f for f in b.GetFootprints() if f.GetReference()=='C258');a=next(x for x in cap.Pads() if x.GetNumber()=='1');net=a.GetNetCode();end=a.GetPosition()
 via=p.PCB_VIA(b);via.SetPosition(end);via.SetWidth(p.FromMM(.45));via.SetDrill(p.FromMM(.2));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNetCode(net);b.Add(via)
 path=[v(50.25,45.55),v(47.95,43.25) if style==p.B_Cu else v(50.25,43.25),end]
 for x,y in zip(path,path[1:]):
  t=p.PCB_TRACK(b);t.SetStart(x);t.SetEnd(y);t.SetWidth(p.FromMM(.18));t.SetLayer(caplayer);t.SetNetCode(net);b.Add(t)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
 report=vd/'last-route-trial.json';r=subprocess.run([r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe','pcb','drc','--format','json','--output',str(report),str(file)],capture_output=True);assert r.returncode==0
 data=json.loads(report.read_text());viol=[x for x in data['violations'] if x['severity']=='error'];score=(len(viol),len(data['unconnected_items']),len(data['violations']))
 print('trial',layer1,layer2,caplayer,style,score,flush=True)
 if best is None or score<best[0]:best=(score,file.read_bytes(),report.read_bytes(),[layer1,layer2,caplayer,style])
 if score==(0,0,0):break
file.write_bytes(best[1]);(vd/'routed-drc.json').write_bytes(best[2]);(vd/'last-route-selection.json').write_text(json.dumps({'score':best[0],'layer_ids':best[3]},indent=2));print('BEST',best[0])
