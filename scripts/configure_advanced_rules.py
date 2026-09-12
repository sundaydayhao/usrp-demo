"""Configure project rules independently of board import/placement."""
from pathlib import Path
import json,copy,sys
ROOT=Path(__file__).resolve().parents[1]
for name in sys.argv[1:]:
 path=ROOT/'projects'/name/(name+'.kicad_pro');cfg=json.loads(path.read_text());ds=cfg['board']['design_settings'];ds['rules'].update({'min_clearance':.127,'min_track_width':.127,'min_via_diameter':.45,'min_through_hole_diameter':.2,'min_copper_edge_clearance':.25,'min_text_height':.6,'min_text_thickness':.08})
 default=cfg['net_settings']['classes'][0];default.update({'name':'Default','track_width':.18,'clearance':.127 if name=='WBX' else .15,'via_diameter':.45 if name=='WBX' else .5,'via_drill':.2 if name=='WBX' else .25});classes=[default]
 for cname,width in [('RF50_START',.37),('RF_LOCAL',.2),('POWER',.4)]:
  c=copy.deepcopy(default);c.update({'name':cname,'track_width':width,'clearance':.15 if cname.startswith('RF') else default['clearance']});classes.append(c)
 rf=json.loads((ROOT/'verification'/name/'rf-net-classes.json').read_text());patterns=[{'netclass':cn,'pattern':net} for cn,names in rf.items() for net in names]
 mp=json.loads((ROOT/'verification'/name/'kicad-net-name-map.json').read_text())
 patterns += [{'netclass':'POWER','pattern':mapped} for net,mapped in mp.items() if net.startswith(('5V','3_3V','6V')) or net in ['DVDD','DVDD_RX','DVDD_TX','1_8V']]
 cfg['net_settings']['classes']=classes;cfg['net_settings']['netclass_patterns']=patterns;path.write_text(json.dumps(cfg,indent=2))
 print(name,'routing rules configured')
