"""Bisect dangling-copper removals; retain anything necessary for connectivity."""
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parents[1];board=root/'projects/WBX/WBX.kicad_pcb';report=root/'verification/WBX/routed-drc.json';py=r'C:\Program Files\KiCad\10.0\bin\python.exe';cli=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe';selection=root/'tmp/dangling-selection.json';history=[];kept=set()
def drc():
 subprocess.run([cli,'pcb','drc','--format','json','--output',str(report),str(board)],check=True,capture_output=True)
 return json.loads(report.read_text())
def attempt(ids):
 if not ids:return
 old=board.read_bytes();oldr=report.read_bytes();selection.write_text(json.dumps(ids));r=subprocess.run([py,'-X','utf8',str(root/'scripts/remove_wbx_copper_set.py'),str(selection)],capture_output=True)
 if r.returncode:board.write_bytes(old);raise RuntimeError(r.stderr.decode('utf-8',errors='replace')[-1200:])
 new=drc();ok=not new['unconnected_items'] and not any(v['severity']=='error' for v in new['violations'])
 if ok:history.append({'removed_count':len(ids),'ids':ids});print('Removed',len(ids),'dangling items; all pads still connected',flush=True)
 else:
  board.write_bytes(old);report.write_bytes(oldr)
  if len(ids)==1:kept.add(ids[0])
  else:mid=len(ids)//2;attempt(ids[:mid]);attempt(ids[mid:])
d=drc();assert not d['unconnected_items']
for cycle in range(5):
 ids=list({v['items'][0]['uuid'] for v in d['violations'] if v['type'] in ['track_dangling','via_dangling']}-kept)
 if not ids:break
 before=len(history);attempt(ids);d=drc()
 if len(history)==before:break
(root/'verification/WBX/dangling-cleanup.json').write_text(json.dumps({'removed_batches':history,'connectivity_critical_retained':sorted(kept)},indent=2));print('Cleanup complete; remaining warnings',len(d['violations']),flush=True)
