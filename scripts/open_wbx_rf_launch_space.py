"""Move two ordinary parts to reserve assembly space for C509's RF launch."""
from pathlib import Path
import math,json
import pcbnew as p
from build_advanced_boards import v,xy
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/WBX/WBX.kicad_pcb';b=p.LoadBoard(str(file));fs={f.GetReference():f for f in b.GetFootprints()}
fs['C521'].SetPosition(v(40.5,34.5))
def bb(f):
 z=f.GetBoundingBox(False,False);return (p.ToMM(z.GetX()),p.ToMM(z.GetY()),p.ToMM(z.GetRight()),p.ToMM(z.GetBottom()))
def overlap(a,c):return a[0]<c[2]+.05 and a[2]>c[0]-.05 and a[1]<c[3]+.05 and a[3]>c[1]-.05
moved={};nets=set()
for ref,target in [('R516',(39,38)),('L507',(47,39))]:
 f=fs[ref];occupied=[bb(g) for g in fs.values() if g!=f and g.GetLayer()==p.F_Cu];candidates=[]
 for i in range(-12,13):
  for j in range(-12,13):
   pt=(target[0]+i*.25,target[1]+j*.25);f.SetPosition(v(*pt));bounds=bb(f)
   if not any(overlap(bounds,z) for z in occupied):candidates.append((math.dist(pt,target),pt))
 assert candidates,ref
 pt=min(candidates)[1];f.SetPosition(v(*pt));moved[ref]=pt;nets|={a.GetNetname() for a in f.Pads() if a.GetNetname()}
tracks=list(b.GetTracks())
for t in tracks:
 if t.GetNetname() in nets:
  assert not t.IsLocked();b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b);print(moved)
(ROOT/'verification/WBX/rf-launch-space.json').write_text(json.dumps({'ordinary_part_positions_mm':moved,'C521':[40.5,34.5]},indent=2))
