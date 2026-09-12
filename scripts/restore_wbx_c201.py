"""Apply the independently found merged-text C201 omission without moving RF."""
from pathlib import Path
import json,math
import pcbnew as p
from build_advanced_boards import v,xy,stock
from build_legacy_schematics import uid
ROOT=Path(__file__).resolve().parents[1]
name='WBX';d=ROOT/'projects'/name;vd=ROOT/'verification'/name
model=json.loads((vd/'reconstructed-netlist.json').read_text());newnames=json.loads((vd/'kicad-net-name-map.json').read_text())
b=p.LoadBoard(str(d/'WBX.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};assert 'C201' not in fps
pinmap={(r,a.GetNumber()):a for r,f in fps.items() for a in f.Pads() if a.GetNumber()}
netobjs={};renames={}
for source,ps in model['nets'].items():
 codes={pinmap[tuple(pair)].GetNetCode() for pair in ps if tuple(pair) in pinmap};assert len(codes)==1,(source,codes)
 code=next(iter(codes));obj=b.FindNet(code);netobjs[source]=obj;renames[obj.GetNetname()]=newnames[source]
for source,obj in netobjs.items():obj.SetNetname(newnames[source])
f=stock('Capacitor_SMD','C_0402_1005Metric');f.SetReference('C201');f.SetValue('0.01uF');f.SetFPID(p.LIB_ID('USRP','C201'));f.Reference().SetVisible(False);f.Value().SetVisible(False)
plugin=p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP);plugin.FootprintSave(str(d/'USRP.pretty'),f)
b.Add(f);c=model['components']['C201'];f.SetPath(p.KIID_PATH(c['sheet_path']+'/'+c['symbol_uuid']))
for a in f.Pads():
 source=next(n for n,ps in model['nets'].items() if ['C201',a.GetNumber()] in ps);a.SetNet(netobjs[source])
def bounds(o):
 bb=o.GetBoundingBox(False,False) if isinstance(o,p.FOOTPRINT) else o.GetBoundingBox();return [p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())]
obs=[bounds(o) for o in fps.values() if o.GetLayer()==p.F_Cu]+[bounds(t) for t in b.GetTracks() if isinstance(t,p.PCB_VIA) or t.GetLayer()==p.F_Cu]
best=None
for x in [i/2 for i in range(22,53)]:
 for y in [i/2 for i in range(224,252)]:
  for rot in [0,90,180,270]:
   f.SetOrientationDegrees(rot);f.SetPosition(v(x,y));bb=bounds(f)
   if any(bb[0]<o[2]+.2 and bb[2]>o[0]-.2 and bb[1]<o[3]+.2 and bb[3]>o[1]-.2 for o in obs):continue
   cost=math.dist((x,y),xy(pinmap['R201','1']))+math.dist((x,y),xy(pinmap['C202','2']))
   if best is None or cost<best[0]:best=(cost,x,y,rot)
assert best
_,x,y,rot=best;f.SetOrientationDegrees(rot);f.SetPosition(v(x,y));b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(d/'WBX.kicad_pcb'),b)
fp_audit=json.loads((vd/'footprint-audit.json').read_text());fp_audit['C201']={'value':'0.01uF','source':'C_0402_1005Metric','numbered_pads':['1','2'],'position_mm':[x,y],'rotation_deg':rot,'side':'F.Cu'};(vd/'footprint-audit.json').write_text(json.dumps(fp_audit,indent=2))
rf=json.loads((vd/'rf-net-classes.json').read_text());rf={k:[renames.get(n,n) for n in ns] for k,ns in rf.items()};(vd/'rf-net-classes.json').write_text(json.dumps(rf,indent=2))
pro=d/'WBX.kicad_pro';cfg=json.loads(pro.read_text())
for pp in cfg['net_settings']['netclass_patterns']:pp['pattern']=renames.get(pp['pattern'],pp['pattern'])
pro.write_text(json.dumps(cfg,indent=2))
(vd/'c201-correction.json').write_text(json.dumps({'source_text':'C2010.01uF, seq534, PDF page3','source_label':'clock_rx_p, seq527, omitted by PDF word grouping','new_part':'C201 0.01uF','position_mm':[x,y],'net_renames':renames,'trace_geometry_changed':False},indent=2))
print('C201 restored',x,y,rot,'nets renamed without changing existing copper')
