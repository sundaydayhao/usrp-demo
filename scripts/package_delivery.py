"""Package reviewed CAD and current checks; refuse unfinished/inconsistent files."""
from pathlib import Path
import json,hashlib,zipfile,datetime
ROOT=Path(__file__).resolve().parents[1]
names=['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']
files=[]
for name in names:
 d=ROOT/'projects'/name;v=ROOT/'verification'/name;s=json.loads((v/'final-summary.json').read_text())
 assert not s['unconnected'] and not any(k.startswith('error:') for k in [*s['erc'],*s['drc']]),name
 for key in ['PCB_pin_net_mismatches','missing_PCB_components','empty_schematic_paths','duplicate_schematic_paths','ordinary_tracks_on_RF_reference','copper_outside_board_bounds']:assert not s[key],(name,key)
 assert hashlib.sha256((d/(name+'.kicad_pcb')).read_bytes()).hexdigest()==s['pcb_sha256'],name+' stale board checks'
 files += [p for p in d.rglob('*') if p.is_file() and p.suffix not in ['.kicad_prl','.svg','.png'] and not p.name.startswith('~')]
 wanted=['final-summary.json','final-rf-audit.json','erc.json','drc.json','validation-summary.json','independent-reference-audit.json','assembly-labels.json','rf-net-classes.json','delivery-review.json','source-netlist.json','reconstructed-netlist.json','pcb-import-audit.json','footprint-audit.json','kicad-net-name-map.json','rf-audit.json','dangling-cleanup.json']
 files += [v/f for f in wanted if (v/f).exists()]
 files += list(v.glob('*geometry.json'))
files += [ROOT/f for f in ['README.md','DESIGN_NOTES.md','REVIEW.md']]
files += list((ROOT/'usrp1-daughterboard').glob('*.pdf'))
files += [p for p in (ROOT/'scripts').glob('*') if p.suffix in ['.py','.md','.json'] and p.name!='inspect_wbx_pending.py']
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'KiCad':'10.0.5','projects':names,'purpose':'Editable CAD prototype review; hardware and RF validation pending','files':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}}
out=ROOT/'deliverables';out.mkdir(exist_ok=True);target=out/'USRP1-seven-KiCad-projects.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(set(files)):z.write(p,str(p.relative_to(ROOT)))
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2,ensure_ascii=False))
with zipfile.ZipFile(target) as z:assert z.testzip() is None
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
print(target,'files',len(files),'bytes',target.stat().st_size)
