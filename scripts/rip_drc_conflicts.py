"""Remove ordinary routed items which collide with preserved RF or other copper.

No change to footprints, RF copper, locked escapes, or design rules.
"""
from pathlib import Path
import sys,json,subprocess,collections
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1]
CLI=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
def run(name):
 path=ROOT/'projects'/name/(name+'.kicad_pcb');report=ROOT/'verification'/name/'routed-drc.json'
 rf=set(sum(json.loads((report.parent/'rf-net-classes.json').read_text()).values(),[]));history=[]
 b=p.LoadBoard(str(path))
 for cycle in range(1):
  subprocess.run([CLI,'pcb','drc','--format','json','--output',str(report),str(path)],capture_output=True,check=True)
  drc=json.loads(report.read_text());tracks=list(b.GetTracks());byid={t.m_Uuid.AsString():t for t in tracks};remove={};untouched=[]
  for v in drc['violations']:
   if v['severity']!='error':continue
   if v['type'] not in ['clearance','shorting_items','tracks_crossing','hole_clearance','solder_mask_bridge','hole_to_hole']:untouched.append(v);continue
   candidates=[byid[i['uuid']] for i in v['items'] if i['uuid'] in byid and not byid[i['uuid']].IsLocked() and byid[i['uuid']].GetNetname() not in rf]
   if candidates:
    choice=min(candidates,key=lambda t:(isinstance(t,p.PCB_VIA),t.GetLength()));remove[choice.m_Uuid.AsString()]=choice
   else:untouched.append(v)
  print(name,'cycle',cycle,'unconnected',len(drc['unconnected_items']),'violations',dict(collections.Counter(v['severity']+':'+v['type'] for v in drc['violations'])),'rip',len(remove),'unresolved errors',len(untouched),flush=True)
  if not remove:break
  history.append([{'uuid':u,'net':t.GetNetname()} for u,t in remove.items()])
  for t in remove.values():b.Remove(t)
  b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b)
 (report.parent/'ordinary-conflict-rip.json').write_text(json.dumps(history,indent=2))
if __name__=='__main__':run(sys.argv[1])
