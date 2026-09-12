"""Isolated per-connection routing with saved checkpoints and DRC gates."""
from pathlib import Path
import json,subprocess,sys,shutil,collections
ROOT=Path(__file__).resolve().parents[1];PY=r'C:\Program Files\KiCad\10.0\bin\python.exe';CLI=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe';vd=ROOT/'verification/WBX';board=ROOT/'projects/WBX/WBX.kicad_pcb';tmp=ROOT/'tmp/route-iterations';tmp.mkdir(exist_ok=True)
for iteration in range(60):
 before=json.loads((vd/'routed-drc.json').read_text());connected=False
 for rip in [False,True]:
  label=f'{iteration:02d}-'+('rip' if rip else 'normal');shutil.copy2(board,tmp/(label+'.kicad_pcb'))
  with (tmp/(label+'.stdout')).open('w',encoding='utf-8') as out,(tmp/(label+'.stderr')).open('w',encoding='utf-8') as err:
   run=subprocess.run([PY,'-X','utf8',str(ROOT/'scripts/maze_route_wbx.py'),*(['--rip'] if rip else [])],cwd=ROOT,stdout=out,stderr=err)
  if run.returncode:print('STOP: routing exception',label,(tmp/(label+'.stderr')).read_text()[-1200:],flush=True);sys.exit(2)
  log=json.loads((vd/'maze-routing.json').read_text());done=[x['net'] for x in log if x['connected']]
  if not done:continue
  result=subprocess.run([CLI,'pcb','drc','--format','json','--output',str(vd/'routed-drc.json'),str(board)],capture_output=True)
  if result.returncode:print('STOP: DRC invocation failed',flush=True);sys.exit(2)
  d=json.loads((vd/'routed-drc.json').read_text());errors=[v for v in d['violations'] if v['severity']=='error'];print(label,'connected',done,'unconnected',len(before['unconnected_items']),'->',len(d['unconnected_items']),'errors',len(errors),flush=True)
  if errors:print('STOP: DRC findings require review',flush=True);sys.exit(3)
  for _ in range(2):
   cleanup=subprocess.run([PY,'-X','utf8',str(ROOT/'scripts/trim_wbx_routing_debris.py')],cwd=ROOT,capture_output=True)
   if cleanup.returncode:print('STOP: cleanup exception',cleanup.stderr.decode('utf-8',errors='replace')[-800:],flush=True);sys.exit(2)
  d=json.loads((vd/'routed-drc.json').read_text())
  if not d['unconnected_items']:print('ALL CONNECTIONS COMPLETE',flush=True);sys.exit(0)
  connected=True;break
 if not connected:print('STOP: remaining terminals need a placement or escape adjustment',flush=True);sys.exit(1)
print('Iteration batch complete',flush=True)
