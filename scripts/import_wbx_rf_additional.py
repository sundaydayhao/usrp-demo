"""Import only the newly reviewed F.Cu RF connections from a subset SES."""
from pathlib import Path
import json
import pcbnew as p
from build_legacy_schematics import sexp
from build_advanced_boards import v
ROOT=Path(__file__).resolve().parents[1];vd=ROOT/'verification/WBX';file=ROOT/'projects/WBX/WBX.kicad_pcb';b=p.LoadBoard(str(file));nets=set(json.loads((vd/'rf-additional-nets.json').read_text()));text=(vd/'WBX-rf-additional.ses').read_text()
for c,e in json.loads((vd/'dsn-character-map.json').read_text()).items():text=text.replace(e,c)
tree=sexp.parse(text.replace('(string_quote ")','(string_quote quote)'));routes=sexp.find(tree,'routes');resolution=sexp.find(routes,'resolution');assert str(resolution[1])=='um';units_per_mm=1000*float(resolution[2]);network=sexp.find(routes,'network_out');counts={}
old_tracks=list(b.GetTracks())
for t in old_tracks:
 if t.GetNetname() in nets:b.Remove(t)
for net in sexp.find_all(network,'net'):
 name=str(net[1])
 if name not in nets:continue
 assert not list(sexp.find_all(net,'via')),'Additional RF vias forbidden'
 count=0
 for wire in sexp.find_all(net,'wire'):
  path=sexp.find(wire,'path');assert str(path[1])=='F.Cu';width=float(path[2])/units_per_mm;coords=[float(x)/units_per_mm for x in path[3:]];assert .127<=width<=.5;points=[v(coords[i],-coords[i+1]) for i in range(0,len(coords),2)]
  assert all(0<q.x<p.FromMM(69.85) and 0<q.y<p.FromMM(142.24) for q in points),'RF path outside board'
  for a,c in zip(points,points[1:]):
   t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(p.FromMM(width));t.SetLayer(p.F_Cu);t.SetNetCode(b.FindNet(name).GetNetCode());t.SetLocked(True);b.Add(t);count+=1
 counts[name]=count
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b);print(counts)
