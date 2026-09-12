"""Remove an explicit ordinary-copper set, in a fresh pcbnew process."""
from pathlib import Path
import sys,json,pcbnew as p
root=Path(__file__).resolve().parents[1];file=root/'projects/WBX/WBX.kicad_pcb';b=p.LoadBoard(str(file));wanted=set(json.loads(Path(sys.argv[1]).read_text()));rf=set(sum(json.loads((root/'verification/WBX/rf-net-classes.json').read_text()).values(),[]));tracks=list(b.GetTracks());remove=[t for t in tracks if t.m_Uuid.AsString() in wanted and t.GetNetname() not in rf]
for t in remove:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
