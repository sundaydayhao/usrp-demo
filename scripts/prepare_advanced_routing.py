from pathlib import Path
import json,sys,copy
import pcbnew as p
from build_legacy_schematics import sexp,n,S,Q
ROOT=Path(__file__).resolve().parents[1]

def prepare(name):
 d=ROOT/'projects'/name;vd=ROOT/'verification'/name;model=json.loads((vd/'reconstructed-netlist.json').read_text());mp=json.loads((vd/'kicad-net-name-map.json').read_text())
 rf=set();r50=set()
 if name=='TVRX2':
  refs={'R102','C102','R142','C142'};rfnodes=[('U100',str(i)) for i in [31,32,33,34,36,37,38]]+[('U140',str(i)) for i in [31,32,33,34,36,37,38]]
 else:
  refs={'C103','C104','C304','C315','R339','R340','R341','C327','C329','C331','C334','C511'}
  refs|={f'C{i}' for i in [205,206,207,208,405,406,407,408,507,508]}
  rfnodes=[]
 for net,ps in model['nets'].items():
  if 'GND' in net or net.startswith(('5V','3_3V')):continue
  if any(ref in refs or (ref,pin) in rfnodes for ref,pin in ps):rf.add(mp[net])
  if name=='TVRX2' and any(ref in refs for ref,pin in ps):r50.add(mp[net])
  if name=='WBX' and any(ref in ['C103','C104','C304','C315','R339','R340','R341','C511'] for ref,pin in ps):r50.add(mp[net])
 if name=='WBX':
  for net in ['P3_N095','P5_N097','LO_TX']:rf.add(mp[net]);r50.add(mp[net])
 pro=d/(name+'.kicad_pro');cfg=json.loads(pro.read_text());ds=cfg['board']['design_settings'];rules=ds['rules'];rules.update({'min_clearance':.127,'min_track_width':.127,'min_via_diameter':.45,'min_through_hole_diameter':.2,'min_copper_edge_clearance':.25,'min_text_height':.6,'min_text_thickness':.08})
 default=cfg['net_settings']['classes'][0];default.update({'name':'Default','track_width':.18,'clearance':.15,'via_diameter':.5,'via_drill':.25})
 classes=[default]
 for cname,width in [('RF50_START',.37),('RF_LOCAL',.2),('POWER',.4)]:
  c=copy.deepcopy(default);c.update({'name':cname,'track_width':width});classes.append(c)
 patterns=[{'netclass':'RF50_START' if net in r50 else 'RF_LOCAL','pattern':net} for net in sorted(rf)]
 patterns += [{'netclass':'POWER','pattern':mp[net]} for net in model['nets'] if net.startswith(('5V','3_3V')) or net in ['6V','DVDD','DVDD_RX','DVDD_TX','1_8V']]
 cfg['net_settings']['classes']=classes;cfg['net_settings']['netclass_patterns']=patterns;pro.write_text(json.dumps(cfg,indent=2))
 b=p.LoadBoard(str(d/(name+'.kicad_pcb')))
 for f in b.GetFootprints():f.Reference().SetVisible(False)
 p.SaveBoard(str(d/(name+'.kicad_pcb')),b)
 assert p.ExportSpecctraDSN(b,str(vd/(name+'-all.dsn')))
 tx=(vd/(name+'-all.dsn')).read_text();tx=tx.replace('(string_quote ")','(string_quote quote)')
 doc=sexp.parse(tx);network=sexp.find(doc,'network');network[:]=[network[0]]+[item for item in network[1:] if str(item[0])=='net' and str(item[1]) in rf]
 for label,names,width in [('RF50',r50,370),('RF_LOCAL',rf-r50,200)]:
  network.append(n('class',S(label),*[Q(x) for x in sorted(names)],n('rule',n('width',width),n('clearance',150))))
 out=sexp.dumps(doc).replace('(string_quote quote)','(string_quote ")').replace('\t','  ').replace('\r','')
 escapes={c:f'_U{ord(c):04X}_' for c in set(out) if ord(c)>127}
 for c,e in escapes.items():out=out.replace(c,e)
 (vd/'dsn-character-map.json').write_text(json.dumps(escapes));(vd/(name+'-rf.dsn')).write_bytes(out.encode('ascii'))
 (vd/'rf-net-classes.json').write_text(json.dumps({'RF50_START':sorted(r50),'RF_LOCAL':sorted(rf-r50)},indent=2))
 print(name,'RF routing subset:',len(rf),'nets; F.Cu only')

if __name__=='__main__':
 for name in sys.argv[1:] or ['TVRX2','WBX']:prepare(name)
