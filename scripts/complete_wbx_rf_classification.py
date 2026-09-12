"""Include the ADL5386 modulator/attenuator link and RF detector coupling.

These are RF ports even though some are not on the external SMA path.
Remove their provisional ordinary routes and export a top-only subset.
"""
from pathlib import Path
import json
import pcbnew as p
from build_legacy_schematics import sexp,Q
ROOT=Path(__file__).resolve().parents[1];vd=ROOT/'verification/WBX';file=ROOT/'projects/WBX/WBX.kicad_pcb';b=p.LoadBoard(str(file));m=json.loads((vd/'reconstructed-netlist.json').read_text());mp=json.loads((vd/'kicad-net-name-map.json').read_text());rf=json.loads((vd/'rf-net-classes.json').read_text());selected=set()
for net,ps in m['nets'].items():
 if net=='AGND' or net.startswith(('5V','6V','3_3V')):continue
 if any(ref in ['C509','C510','C521','C523'] for ref,num in ps):
  mapped=mp[net];selected.add(mapped);cn='RF50_START' if any(ref=='C509' for ref,num in ps) else 'RF_LOCAL'
  if mapped not in rf[cn]:rf[cn].append(mapped)
for cn in rf:rf[cn]=sorted(set(rf[cn]))
(vd/'rf-net-classes.json').write_text(json.dumps(rf,indent=2));(vd/'rf-additional-nets.json').write_text(json.dumps(sorted(selected),indent=2))
tracks=list(b.GetTracks())
for t in tracks:
 if t.GetNetname() in selected:b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
target=vd/'WBX-rf-additional.dsn';assert p.ExportSpecctraDSN(b,str(target));doc=sexp.parse(target.read_text().replace('(string_quote ")','(string_quote quote)'));network=sexp.find(doc,'network');network[:]=[network[0]]+[x for x in network[1:] if str(x[0])=='net' and str(x[1]) in selected]
network.append(['class','RF_EXTRA',*[Q(n) for n in sorted(selected)],['rule',['width',200],['clearance',150]]])
# The subset session is imported selectively; unrelated copper is an obstacle.
for wire in sexp.find(doc,'wiring')[1:]:
 if not isinstance(wire,list):continue
 fixed=sexp.find(wire,'type')
 if fixed:fixed[1]='fix'
 else:wire.append(['type','fix'])
text=sexp.dumps(doc).replace('(string_quote quote)','(string_quote ")').replace('\t','  ').replace('\r','');esc=json.loads((vd/'dsn-character-map.json').read_text())
for c,e in esc.items():text=text.replace(c,e)
target.write_bytes(text.encode('ascii'));print('WBX additional RF nets',sorted(selected))
