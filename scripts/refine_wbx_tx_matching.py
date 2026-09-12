"""Bring the ADL5386 RF coupling capacitors next to their actual RF pins."""
from pathlib import Path
import pcbnew as p,json
from build_advanced_boards import v
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/WBX/WBX.kicad_pcb';b=p.LoadBoard(str(file));fs={f.GetReference():f for f in b.GetFootprints()};rf=set(sum(json.loads((ROOT/'verification/WBX/rf-net-classes.json').read_text()).values(),[]));moves={'C509':(47.5,33.75),'C521':(40.5,34.25)}
for ref,pt in moves.items():fs[ref].SetPosition(v(*pt))
tracks=list(b.GetTracks());removed=[]
def inside(q):return p.FromMM(39)<=q.x<=p.FromMM(49) and p.FromMM(31.4)<=q.y<=p.FromMM(36.2)
for t in tracks:
 if t.IsLocked() or t.GetNetname() in rf:continue
 if isinstance(t,p.PCB_VIA):hit=inside(t.GetPosition())
 else:hit=t.GetLayer()==p.F_Cu and (inside(t.GetStart()) or inside(t.GetEnd()))
 if hit:removed.append(t.GetNetname());b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
(ROOT/'verification/WBX/tx-matching-placement.json').write_text(json.dumps({'positions_mm':moves,'ordinary_segments_removed_for_local_reroute':len(removed)},indent=2));print('RF coupling capacitors moved; ordinary local segments removed',len(removed))
