"""Review the AT24C02 migration against its pre-edit Git checkpoint.

Run after verify_final_projects.py and export_delivery_previews.py.
KiCad Python is required. Raster review is performed separately on PDF exports.
"""
from pathlib import Path
import collections, copy, csv, hashlib, io, json, subprocess, sys
import pcbnew
from apply_current_component_policy import children, properties, sexp, align_eeprom_text
from component_policy import EEPROM_REFS, DECOUPLING, RESISTORS, passive_kind

ROOT = Path(__file__).resolve().parents[1]
BASE = 'bf6d371'
METADATA = {'Value', 'Manufacturer', 'MPN', 'LCSC', 'Sourcing_status', 'Specification', 'Evidence', 'Approved_brands', 'Sourcing_policy', 'Datasheet'}

def original(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT)

def plain(node, eeprom=False):
    """Allow only the reviewed metadata and EEPROM WP symbol correction."""
    if not isinstance(node, list):
        return str(node)
    eeprom = eeprom or properties(node).get('Value') in ('AT24C02', 'GT24C02A-2GLI-TR', '24LC024/SN', '24LC025B')
    out = [plain(x, eeprom) for x in node if not (isinstance(x, list) and str(x[0]) == 'property' and str(x[1]) in METADATA)]
    if eeprom and out[0] == 'pin' and children(out, 'number') and str(children(out, 'number')[0][1]) == '7':
        out[1] = 'input'
        children(out, 'name')[0][1] = 'WP'
    return out

def property_layouts(node):
    result = {}
    def walk(item, path=()):
        if not isinstance(item, list): return
        # Metadata additions must not alter positions/effects of existing text.
        nonprops = 0
        for child in item:
            if not isinstance(child, list): continue
            if str(child[0]) == 'property':
                result[path + ('property:' + str(child[1]),)] = child[3:]
            else:
                walk(child, path + (str(nonprops),))
                nonprops += 1
    walk(node)
    return result

def violations(data, erc):
    items = [v for sheet in data['sheets'] for v in sheet['violations']] if erc else data['violations']
    return {json.dumps(v, sort_keys=True) for v in items}

reports = []
for name, refs in EEPROM_REFS.items():
    directory = ROOT / 'projects' / name
    vdir = ROOT / 'verification' / name
    bom_path = directory / 'BOM-sourcing.csv'
    rows = {r['Reference']:r for r in csv.DictReader(bom_path.open(encoding='utf-8-sig'))}
    old_rows = {r['Reference']:r for r in csv.DictReader(io.StringIO(original(bom_path).decode('utf-8-sig')))}
    assert rows.keys() == old_rows.keys()
    for ref, row in rows.items():
        assert row['Value'] == ('AT24C02' if ref in refs else old_rows[ref]['Value'])
        assert row['Source_value'] == old_rows[ref]['Source_value']
    checked = 0
    files = list(directory.glob('*.kicad_sch')) + [directory/'USRP.kicad_sym', directory/(name+'.kicad_pcb')] + list((directory/'USRP.pretty').glob('*.kicad_mod'))
    for path in files:
        old = sexp.parse(original(path).decode('utf-8')); new = sexp.load_file(path)
        # Normalize only the eight deliberately aligned EEPROM signal-unit labels.
        if path.suffix == '.kicad_sch':
            for inst in children(old, 'symbol'):
                if properties(inst).get('Reference') in refs:
                    libid = children(inst,'lib_id')[0][1]
                    cached = next(s for cache in children(old,'lib_symbols') for s in children(cache,'symbol') if s[1]==libid)
                    align_eeprom_text(inst,cached)
        assert plain(old) == plain(new), (path, 'unapproved CAD change')
        a, b = property_layouts(old), property_layouts(new)
        assert all(b[k] == val for k, val in a.items()), (path, 'existing property layout moved')
        checked += 1
    pro = directory/(name+'.kicad_pro')
    assert pro.read_bytes().replace(b'\r\n',b'\n') == original(pro).replace(b'\r\n',b'\n')
    lib = sexp.load_file(directory/'USRP.kicad_sym')
    pinmaps = {}
    for symbol in children(lib, 'symbol'):
        ref = str(symbol[1]).split('_')[0]
        if ref not in refs: continue
        pp = properties(symbol)
        assert pp['MPN'] == 'AT24C02C-SSHM-T' and pp['LCSC'] == 'C6203'
        pins = {str(children(pin,'number')[0][1]):str(children(pin,'name')[0][1]) for unit in children(symbol,'symbol') for pin in children(unit,'pin')}
        assert set(pins) == {str(i) for i in range(1,9)}, (name,ref,pins)
        assert all(pins[i]==label for i,label in {'1':'A0','2':'A1','3':'A2','5':'SDA','6':'SCL','7':'WP'}.items()), (name,ref,pins)
        assert pins['4'] in ('GND','AGND','DGND','DGND_RX','DGND_TX')
        assert pins['8'].startswith(('DVDD','VCC','VDD'))
        pinmaps[ref] = pins
    for path in directory.glob('*.kicad_sch'):
        doc=sexp.load_file(path)
        for inst in children(doc,'symbol'):
            pp=properties(inst); ref=pp.get('Reference')
            if ref in rows and (ref in refs or passive_kind(ref,rows[ref]['Value'])):
                assert all(pp.get(k)==val for k,val in rows[ref].items() if k not in ('Reference','Footprint')), (name,ref,'BOM/schematic mismatch')
        for cache in children(doc,'lib_symbols'):
            for symbol in children(cache,'symbol'):
                ref=str(symbol[1]).split(':')[-1].split('_')[0]
                if ref in refs:
                    assert properties(symbol)['MPN']=='AT24C02C-SSHM-T'
                    for unit in children(symbol,'symbol'):
                        for pin in children(unit,'pin'):
                            if str(children(pin,'number')[0][1])=='7':
                                assert str(pin[1])=='input' and str(children(pin,'name')[0][1])=='WP'
    bpath=directory/(name+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(bpath)); fps={f.GetReference():f for f in board.GetFootprints()}
    powernets={'3_3V_RF','6V','3_3V_RX','5V_RX','6V_RX','3_3V_TX','5V_TX','6V_TX'}
    for ref in DECOUPLING.get(name,[]):
        nets={p.GetNetname() for p in fps[ref].Pads()}
        assert len(nets)==2 and 'AGND' in nets and len(nets & powernets)==1, (name,ref,nets)
    eeproms=[]
    for ref in refs:
        nets={p.GetNumber():p.GetNetname() for p in fps[ref].Pads()}
        wp=nets['7']; ground=nets['4']; via=None
        if wp!=ground:
            via='R28' if name=='LFRX' else 'R29' if name=='LFTX' else None
            assert via and {p.GetNetname() for p in fps[via].Pads()}=={wp,ground} and rows[via]['Value']=='0'
        assert nets['3']==nets['8']
        eeproms.append({'reference':ref,'value':'AT24C02','MPN':rows[ref]['MPN'],'LCSC':rows[ref]['LCSC'],'symbol_pin_names':pinmaps[ref],'pad_nets':nets,'WP_ground_via_zero_ohm':via,'page_bytes':8})
    concrete=set(refs+RESISTORS.get(name,[])+DECOUPLING.get(name,[]))
    root=sexp.load_file(bpath); models=0
    for fp in children(root,'footprint'):
        ref=properties(fp)['Reference']
        lf=directory/'USRP.pretty'/(ref+'.kicad_mod')
        if lf.exists():
            assert children(fp,'model')==children(sexp.load_file(lf),'model')
        for model in children(fp,'model'):
            path=directory/str(model[1]).split('}/',1)[1]
            assert path.is_file()
            assert path.read_bytes()==original(path), (path,'3D asset changed')
            models+=1
        if ref in concrete:
            for target in [fp,sexp.load_file(lf)]:
                pp=properties(target)
                assert all(pp.get(k)==rows[ref][k] for k in ('Value','MPN','LCSC','Manufacturer','Specification')), (name,ref,'PCB/library metadata mismatch')
    delta={}
    for kind in ('erc','drc'):
        path=vdir/(kind+'.json'); old=json.loads(original(path)); new=json.loads(path.read_text())
        a,c=violations(old,kind=='erc'),violations(new,kind=='erc')
        delta[kind]={'added':len(c-a),'removed':len(a-c)}
        assert a==c, (name,kind,delta[kind])
        if kind=='drc': assert not new['unconnected_items']
    summary=json.loads((vdir/'final-summary.json').read_text())
    assert not summary['unconnected'] and not summary['PCB_pin_net_mismatches']
    assert not any(k.startswith('error:') for k in [*summary['erc'],*summary['drc']])
    report={'project':name,'baseline_commit':BASE,'machine_review':'PASS','pcb_sha256':hashlib.sha256(bpath.read_bytes()).hexdigest(),'cad_files_compared':checked,'geometry_connectivity_UUIDs_paths_and_settings_preserved':True,'EEPROM_signal_unit_labels_aligned_above_symbol':refs,'other_existing_text_placement_preserved':True,'model_bindings_and_files_preserved':models,'EEPROMs':eeproms,'selected_YAGEO_resistors':RESISTORS.get(name,[]),'selected_Samsung_decoupling_caps':DECOUPLING.get(name,[]),'electrical_check_set_diff':delta}
    report['schematic_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.kicad_sch')}
    report['BOM_sha256']=hashlib.sha256(bom_path.read_bytes()).hexdigest()
    (vdir/'component-update-review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    reports.append(report)
    print(name,'PASS; CAD geometry/net/model preservation and BOM synchronization',flush=True)
(ROOT/'verification/component-update-summary.json').write_text(json.dumps({'baseline_commit':BASE,'EEPROM_total':sum(len(x) for x in EEPROM_REFS.values()),'projects':reports},indent=2,ensure_ascii=False),encoding='utf-8')
