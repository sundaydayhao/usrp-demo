"""Reviewed QFN escape vias for the remaining trapped control/supply pins.

These vias are within the package courtyard. Filled/capped holes are required
for the U80 pin-6 via in pad and are also specified for exposed-pad arrays.
"""
from pathlib import Path
import pcbnew as p
from build_advanced_boards import v
ROOT=Path(__file__).resolve().parents[1];file=ROOT/'projects/TVRX2/TVRX2.kicad_pcb';b=p.LoadBoard(str(file));fs={f.GetReference():f for f in b.GetFootprints()}
escapes=[('U100','35',50.75,15.45),('U140','35',50.75,50.45),('U100','6',53.45,12.75),('U80','6',26.5,44.75),('U100','4',53.45,13.75),('U100','8',53.45,11.75),('U140','8',53.45,46.75),('U140','17',50.25,45.55)]
for ref,num,x,y in escapes:
 a=next(a for a in fs[ref].Pads() if a.GetNumber()==num);q=v(x,y)
 assert not any(isinstance(t,p.PCB_VIA) and t.GetPosition()==q for t in b.GetTracks()),'Escape already exists'
 via=p.PCB_VIA(b);via.SetPosition(q);via.SetWidth(p.FromMM(.45));via.SetDrill(p.FromMM(.2));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNetCode(a.GetNetCode());via.SetLocked(True);b.Add(via)
 if a.GetPosition()!=q:
  t=p.PCB_TRACK(b);t.SetStart(a.GetPosition());t.SetEnd(q);t.SetWidth(p.FromMM(.18));t.SetLayer(p.F_Cu);t.SetNetCode(a.GetNetCode());t.SetLocked(True);b.Add(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b);print('TVRX2: added 8 reviewed QFN escapes')
