from pathlib import Path
import json,sys,collections,shutil,math
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1]
def import_route(name):
 d=ROOT/'projects'/name;vd=ROOT/'verification'/name;path=d/(name+'.kicad_pcb');b=p.LoadBoard(str(path));rf=json.loads((vd/'rf-net-classes.json').read_text());names=set(sum(rf.values(),[]))
 def signature():
  vals=collections.defaultdict(float)
  for t in b.GetTracks():
   if t.GetNetname() in names:
    assert not isinstance(t,p.PCB_VIA),'RF vias are forbidden'
    vals[t.GetNetname(),t.GetLayer(),t.GetWidth()]+=t.GetLength()/1e6
  return vals
 before=signature();rf_original=[(t.GetStart(),t.GetEnd(),t.GetWidth(),t.GetLayer(),t.GetNetname()) for t in b.GetTracks() if t.GetNetname() in names];backup=ROOT/'tmp/checkpoints'/name;backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/(name+'-before-full-import.kicad_pcb'))
 ses=(vd/(name+'-routed.ses')).read_text()
 for c,e in json.loads((vd/'dsn-character-map.json').read_text()).items():ses=ses.replace(e,c)
 native=vd/(name+'-routed-native.ses');native.write_text(ses,encoding='utf-8');assert p.ImportSpecctraSES(b,str(native))
 # The ordinary-net router must not own RF geometry. Even fixed RF segments
 # may be split or receive a redundant tiny branch in a SES file. Restore
 # the exact reviewed RF copper, then let KiCad check all final connections.
 imported=list(b.GetTracks())
 for t in imported:
  if t.GetNetname() in names:b.Remove(t)
 for a,c,width,layer,net in rf_original:
  t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(width);t.SetLayer(layer);t.SetNetCode(b.FindNet(net).GetNetCode());t.SetLocked(True);b.Add(t)
 after=signature()
 delta={str(k):after.get(k,0)-before.get(k,0) for k in set(before)|set(after) if abs(after.get(k,0)-before.get(k,0))>.003}
 assert not delta,('RF changed',delta)
 for t in b.GetTracks():
  if t.GetNetname() in names:t.SetLocked(True)
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b)
 (vd/'rf-preservation.json').write_text(json.dumps({'rf_length_width_layer_delta':delta,'track_segments':sum(not isinstance(t,p.PCB_VIA) for t in b.GetTracks()),'vias':sum(isinstance(t,p.PCB_VIA) for t in b.GetTracks())},indent=2));print(name,'route imported; RF geometry preserved')
if __name__=='__main__':
 for name in sys.argv[1:]:import_route(name)
