"""Inventory the supplied PDFs and the historical gEDA source archive."""
from pathlib import Path
import json, hashlib, re

ROOT = Path(__file__).resolve().parents[1]
GEDA = ROOT / 'tmp/source-audit/geda'
BOARDS = {'BasicRX': 'basic-dboard/rxmod', 'BasicTX': 'basic-dboard/txmod',
          'LFRX': 'basic-lf/lfrx', 'LFTX': 'basic-lf/lftx', 'TVRX': 'tvrx/tvrx'}
inventory = {}
symbols = {p.name:p for p in (GEDA/'sym').rglob('*.sym')}
missing = set()
for name, stem in BOARDS.items():
    sch = GEDA/(stem+'.sch')
    basenames = re.findall(r'^C .*? (\S+\.sym)$', sch.read_text(), re.M)
    missing.update(n for n in basenames if n not in symbols)
    inventory[name] = {'source':stem, 'symbols':sorted(set(basenames)),
                       'components':len(re.findall(r'^refdes=',sch.read_text(),re.M))}
print(json.dumps(inventory, indent=2))
print('MISSING', sorted(missing))
(ROOT/'tmp/source-audit/inventory.json').write_text(json.dumps(inventory,indent=2))
