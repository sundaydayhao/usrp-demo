"""Six-layer WBX option retaining the top RF reference geometry."""
from pathlib import Path
import pcbnew as p,shutil
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'projects/WBX/WBX.kicad_pcb';backup=ROOT/'tmp/checkpoints/WBX/four-layer-last';backup.mkdir(exist_ok=True)
shutil.copy2(path,backup/path.name);shutil.copy2(path.with_suffix('.kicad_pro'),backup/'WBX.kicad_pro');b=p.LoadBoard(str(path));assert b.GetCopperLayerCount()==4;b.SetCopperLayerCount(6)
z=p.ZONE(b);z.SetLayer(p.In4_Cu);z.SetNet(b.FindNet('AGND'));z.SetLocalClearance(p.FromMM(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(p.FromMM(.15));poly=z.Outline();poly.NewOutline()
for x,y in [(.5,.5),(69.35,.5),(69.35,141.74),(.5,141.74)]:poly.Append(p.FromMM(x),p.FromMM(y))
b.Add(z);b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b);print('WBX: 6 copper layers; In3 signal, In4 ground; RF geometry unchanged')
