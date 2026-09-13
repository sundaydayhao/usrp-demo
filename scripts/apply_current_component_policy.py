"""Apply reviewed component metadata with the S-expression backend.

Uses the existing BOM as input. Preserves nets, pads, copper, symbol geometry,
UUIDs, paths, and models. Generic purchasing policy lives in schematic/BOM;
concrete selected parts are also recorded in PCB and local footprint libraries.
"""
from pathlib import Path
import copy, csv, json, sys, uuid
sys.path.insert(0, 'C:/projects/kicad-projects/tools/KiSkill-main')
from kicad_lib import sexp
from component_policy import EEPROM_REFS, EEPROM_SOURCE, RESISTORS, DECOUPLING, passive_kind, update_row

ROOT = Path(__file__).resolve().parents[1]
Q, S = sexp.QStr.of, sexp.Sym

def children(node, tag):
    return [x for x in node if isinstance(x, list) and str(x[0]) == tag]

def properties(node):
    return {str(x[1]): str(x[2]) for x in children(node, 'property') if len(x) >= 3}

def set_property(node, key, value, identity='', pcb=False):
    found = next((x for x in children(node, 'property') if str(x[1]) == key), None)
    if found is not None:
        found[2] = Q(value)
        return
    if pcb:
        template = next(x for x in children(node, 'property') if str(x[1]) == 'Datasheet')
        item = copy.deepcopy(template)
        item[1:3] = [Q(key), Q(value)]
        for uid in children(item, 'uuid'):
            uid[1] = Q(str(uuid.uuid5(uuid.NAMESPACE_URL, 'usrp-component-policy/' + identity + '/' + key)))
    else:
        item = [S('property'), Q(key), Q(value), [S('at'), S('0'), S('0'), S('0')],
                [S('effects'), [S('font'), [S('size'), S('1'), S('1')]], [S('hide'), S('yes')]]]
    index = max(i for i, x in enumerate(node) if isinstance(x, list) and str(x[0]) == 'property') + 1
    node.insert(index, item)

def set_metadata(node, row, identity='', pcb=False):
    for key, value in row.items():
        if key not in ('Reference', 'Footprint', 'Source_value'):
            set_property(node, key, value, identity, pcb)
    if row['MPN'] == 'AT24C02C-SSHM-T':
        set_property(node, 'Datasheet', EEPROM_SOURCE, identity, pcb)

def fix_wp(symbol):
    for unit in children(symbol, 'symbol'):
        for pin in children(unit, 'pin'):
            if str(children(pin, 'number')[0][1]) == '7':
                assert str(children(pin, 'name')[0][1]) in ('WP', 'n/c')
                children(pin, 'name')[0][1] = Q('WP')
                pin[1] = S('input')

def align_eeprom_text(inst, library_symbol):
    if str(children(inst, 'unit')[0][1]) != '1':
        return
    at = children(inst, 'at')[0]
    assert float(at[3]) == 0
    unit = next(x for x in children(library_symbol, 'symbol') if str(x[1]).endswith('_1_1'))
    points = [xy for poly in children(unit, 'polyline') for pts in children(poly, 'pts') for xy in children(pts, 'xy')]
    cx = float(at[1]) + (min(float(p[1]) for p in points) + max(float(p[1]) for p in points))/2
    top = float(at[2]) - max(float(p[2]) for p in points)
    for prop in children(inst, 'property'):
        key = str(prop[1])
        if key in ('Reference', 'Value'):
            xy = children(prop, 'at')[0]
            xy[1:3] = [S(str(round(cx,4))), S(str(round(top - (3.6 if key == 'Reference' else 1.6),4)))]

def save_changed(path, before, after):
    if before != after:
        sexp.save_file(path, after)

def apply(name):
    directory = ROOT / 'projects' / name
    bom = directory / 'BOM-sourcing.csv'
    old_rows = list(csv.DictReader(bom.open(encoding='utf-8-sig')))
    audit_path = ROOT / 'verification' / name / 'footprint-audit.json'
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    rows = {r['Reference']: update_row(name, r, audit.get(r['Reference'], {}).get('source', '')) for r in old_rows}
    affected = {r['Reference'] for r in old_rows if r['Reference'] in EEPROM_REFS[name] or passive_kind(r['Reference'], r['Value'])}
    concrete = set(EEPROM_REFS[name] + RESISTORS.get(name, []) + DECOUPLING.get(name, []))
    count = 0
    for path in directory.glob('*.kicad_sch'):
        doc = sexp.load_file(path); before = copy.deepcopy(doc)
        for inst in children(doc, 'symbol'):
            ref = properties(inst).get('Reference')
            if ref in affected:
                set_metadata(inst, rows[ref])
                if ref in EEPROM_REFS[name]:
                    count += 1
                    libid = children(inst, 'lib_id')[0][1]
                    cached = next(s for cache in children(doc, 'lib_symbols') for s in children(cache, 'symbol') if s[1] == libid)
                    align_eeprom_text(inst, cached)
        for cache in children(doc, 'lib_symbols'):
            for symbol in children(cache, 'symbol'):
                ref = str(symbol[1]).split(':')[-1].split('_')[0]
                if ref in affected:
                    set_metadata(symbol, rows[ref])
                if ref in EEPROM_REFS[name]:
                    fix_wp(symbol)
        save_changed(path, before, doc)
    path = directory / 'USRP.kicad_sym'
    lib = sexp.load_file(path); before = copy.deepcopy(lib)
    for symbol in children(lib, 'symbol'):
        ref = str(symbol[1]).split('_')[0]
        if ref in affected:
            set_metadata(symbol, rows[ref])
        if ref in EEPROM_REFS[name]:
            fix_wp(symbol)
    save_changed(path, before, lib)
    path = directory / (name + '.kicad_pcb')
    board = sexp.load_file(path); before = copy.deepcopy(board)
    for fp in children(board, 'footprint'):
        ref = properties(fp)['Reference']
        if ref in concrete:
            set_metadata(fp, rows[ref], name + '/' + ref, pcb=True)
    save_changed(path, before, board)
    for ref in sorted(concrete):
        path = directory / 'USRP.pretty' / (ref + '.kicad_mod')
        fp = sexp.load_file(path); before = copy.deepcopy(fp)
        set_metadata(fp, rows[ref], name + '/library/' + ref, pcb=True)
        save_changed(path, before, fp)
    with bom.open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=list(next(iter(rows.values()))))
        writer.writeheader(); writer.writerows(rows[r['Reference']] for r in old_rows)
    assert count == len(EEPROM_REFS[name]) * 2, (name, count)
    print(name, count // 2, 'EEPROMs;', len(affected), 'sourcing rows;', len(concrete), 'PCB/library parts synchronized', flush=True)

if __name__ == '__main__':
    for name in sys.argv[1:] or EEPROM_REFS:
        apply(name)
