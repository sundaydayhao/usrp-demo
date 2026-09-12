"""Run independent KiCad gates and compare exported connectivity to source."""
from pathlib import Path
import subprocess,concurrent.futures,json,collections,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
CLI='C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
def check(name):
    d=ROOT/'projects'/name;v=ROOT/'verification'/name;v.mkdir(parents=True,exist_ok=True)
    for args in [('sch','erc','--format','json','--output',str(v/'erc.json'),str(d/(name+'.kicad_sch'))),('pcb','drc','--format','json','--output',str(v/'drc.json'),str(d/(name+'.kicad_pcb'))),('sch','export','netlist','--format','kicadxml','--output',str(v/'export.net'),str(d/(name+'.kicad_sch')))]:
        r=subprocess.run([CLI,*args],capture_output=True)
        if r.returncode:print(name,args[:2],r.stderr.decode(errors='replace'))
    d=json.loads((v/'drc.json').read_text());e=json.loads((v/'erc.json').read_text());source=json.loads((v/'source-netlist.json').read_text())
    x=ET.parse(v/'export.net');actual={n.attrib['name'].removeprefix('/'):sorted((p.attrib['ref'],p.attrib['pin']) for p in n.findall('node') if not p.attrib['ref'].startswith('#')) for n in x.findall('.//nets/net')}
    expected={n:sorted(map(tuple,ps)) for n,ps in source['nets'].items()}
    bypins={tuple(ps):n for n,ps in actual.items() if not n.startswith('unconnected-')}
    mismatches={n:{'expected':ps,'actual':actual.get(n,[])} for n,ps in expected.items() if (tuple(ps) not in bypins if n.startswith('unnamed_net') else actual.get(n,[])!=ps)}
    expected_sets={tuple(ps) for ps in expected.values()}
    for n,ps in actual.items():
        if not n.startswith('unconnected-') and tuple(ps) not in expected_sets:mismatches[n]={'unexpected_nodes':ps}
    (v/'kicad-net-name-map.json').write_text(json.dumps({n:bypins.get(tuple(ps),n) for n,ps in expected.items()},indent=2))
    result={'erc':dict(collections.Counter(i['severity'] for s in e['sheets'] for i in s['violations'])),'drc':dict(collections.Counter(i['type'] for i in d['violations'])),'unconnected':len(d['unconnected_items']),'netlist_mismatches':mismatches}
    (v/'validation-summary.json').write_text(json.dumps(result,indent=2));print(name,json.dumps(result))
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(5) as p:list(p.map(check,['BasicRX','BasicTX','LFRX','LFTX','TVRX']))
