from pathlib import Path
import json,subprocess,collections,xml.etree.ElementTree as ET,concurrent.futures
ROOT=Path(__file__).resolve().parents[1]
CLI=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
def run(name):
    d=ROOT/'projects'/name;v=ROOT/'verification'/name;sch=d/(name+'.kicad_sch');preview=d/'preview';preview.mkdir(exist_ok=True)
    cmds=[['sch','erc','--format','json','--output',str(v/'erc.json'),str(sch)],['sch','export','netlist','--format','kicadxml','--output',str(v/'export.net'),str(sch)],['sch','export','svg','--output',str(preview),'--no-background-color',str(sch)]]
    for cmd in cmds:
        r=subprocess.run([CLI,*cmd],capture_output=True,text=True,encoding='utf-8');assert r.returncode==0,(r.stdout,r.stderr)
    doc=ET.parse(v/'export.net').getroot();expected=json.loads((v/'reconstructed-netlist.json').read_text());actual={frozenset((x.attrib['ref'],x.attrib['pin']) for x in net.findall('node')):net.attrib['name'] for net in doc.findall('./nets/net') if not net.attrib['name'].startswith('unconnected-')}
    expected_sets={frozenset(map(tuple,pins)):net for net,pins in expected['nets'].items()}
    missing=[{'net':net,'pins':sorted(pins)} for pins,net in expected_sets.items() if pins not in actual]
    extra=[{'net':net,'pins':sorted(pins)} for pins,net in actual.items() if pins not in expected_sets]
    erc=json.loads((v/'erc.json').read_text());violations=[x for p in erc['sheets'] for x in p['violations']]
    summary={'expected_components':len(expected['components']),'actual_components':len(doc.findall('./components/comp')),'expected_nets':len(expected_sets),'actual_nets':len(actual),'missing_nets':missing,'unexpected_nets':extra,'erc':dict(collections.Counter((x['severity']+':'+x['type']) for x in violations))}
    (v/'validation-summary.json').write_text(json.dumps(summary,indent=2));(v/'kicad-net-name-map.json').write_text(json.dumps({net:actual[pins] for pins,net in expected_sets.items() if pins in actual},indent=2))
    print(name,summary['expected_components'],summary['actual_components'],'nets',len(expected_sets),len(actual),'missing',len(missing),'extra',len(extra),'ERC',summary['erc'])
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(run,['WBX','TVRX2']))
