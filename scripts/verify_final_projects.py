"""Final CAD checks plus independent schematic-to-PCB pad/net comparison."""
from pathlib import Path
import json,sys,collections,xml.etree.ElementTree as ET,subprocess,math,hashlib
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];CLI=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
def run(name):
 d=ROOT/'projects'/name;vd=ROOT/'verification'/name
 for args in [['sch','erc','--format','json','--output',str(vd/'erc.json'),str(d/(name+'.kicad_sch'))],['pcb','drc','--format','json','--output',str(vd/'drc.json'),str(d/(name+'.kicad_pcb'))],['sch','export','netlist','--format','kicadxml','--output',str(vd/'export.net'),str(d/(name+'.kicad_sch'))]]:
  result=subprocess.run([CLI,*args],capture_output=True);assert result.returncode==0,(args,result.stderr)
 tree=ET.parse(vd/'export.net');expected={(node.attrib['ref'],node.attrib['pin']):net.attrib['name'] for net in tree.findall('.//nets/net') for node in net.findall('node')};components={c.attrib['ref'] for c in tree.findall('.//components/comp')};b=p.LoadBoard(str(d/(name+'.kicad_pcb')));actual={};paths=[]
 for f in b.GetFootprints():
  if f.GetReference() in components:paths.append((f.GetReference(),f.GetPath().AsString()))
  for a in f.Pads():
   if a.GetNumber():actual[f.GetReference(),a.GetNumber()]=a.GetNetname()
 mismatches=[]
 for pin,net in expected.items():
  if pin[0].startswith('#'):continue
  got=actual.get(pin)
  if net.startswith('unconnected-'):
   if got not in ('',net):mismatches.append([pin,net,got])
  elif got!=net:mismatches.append([pin,net,got])
 missing_components=sorted(components-{r for r,path in paths});empty_paths=[r for r,path in paths if not path.strip('/')];path_counts=collections.Counter(path for r,path in paths);duplicate_paths=[key for key,val in path_counts.items() if val>1]
 erc=json.loads((vd/'erc.json').read_text());drc=json.loads((vd/'drc.json').read_text());ev=[v for sheet in erc['sheets'] for v in sheet['violations']];rf_report={};foreign_inner=[]
 if name in ['WBX','TVRX2']:
  rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]));traces=list(b.GetTracks());pads=[a for f in b.GetFootprints() for a in f.Pads()]
  for net in sorted(rf):
   tt=[t for t in traces if t.GetNetname()==net];sample_count=0;gaps=[]
   for t in tt:
    if isinstance(t,p.PCB_VIA):continue
    a,c=t.GetStart(),t.GetEnd();steps=max(1,math.ceil(t.GetLength()/p.FromMM(.2)))
    for i in range(steps+1):
     q=p.VECTOR2I(round(a.x+(c.x-a.x)*i/steps),round(a.y+(c.y-a.y)*i/steps));sample_count+=1
     covered=any(z.GetLayer()==p.In1_Cu and z.GetNetname()=='AGND' and z.HitTestFilledArea(p.In1_Cu,q) for z in b.Zones())
     if not covered:
      own_launch=any(a.GetNetname()==net and a.GetAttribute()==p.PAD_ATTRIB_PTH and math.hypot(q.x-a.GetPosition().x,q.y-a.GetPosition().y)<=max(a.GetSize().x,a.GetSize().y)/2+p.FromMM(.3) for a in pads)
      gaps.append({'xy_mm':[p.ToMM(q.x),p.ToMM(q.y)],'own_PTH_launch':own_launch})
   rf_report[net]={'length_mm':sum(t.GetLength()/1e6 for t in tt if not isinstance(t,p.PCB_VIA)),'vias':sum(isinstance(t,p.PCB_VIA) for t in tt),'layers':sorted({b.GetLayerName(t.GetLayer()) for t in tt if not isinstance(t,p.PCB_VIA)}),'samples':sample_count,'reference_gaps':gaps}
  ground_layers={p.In1_Cu,p.In4_Cu} if name=='WBX' else {p.In1_Cu}
  foreign_inner=[{'net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'uuid':t.m_Uuid.AsString()} for t in traces if not isinstance(t,p.PCB_VIA) and t.GetLayer() in ground_layers and t.GetNetname()!='AGND']
  (vd/'final-rf-audit.json').write_text(json.dumps({'reference_layer':'In1.Cu AGND','ordinary_tracks_on_reference_layer':foreign_inner,'nets':rf_report},indent=2))
 edge=b.GetBoardEdgesBoundingBox();outside=[]
 # DRC can miss copper entirely outside the board: independently inspect
 # every route/via and copper pad, allowing only source edge-launch overhang.
 for item in list(b.GetTracks())+[a for f in b.GetFootprints() for a in f.Pads()]:
  bb=item.GetBoundingBox();margin=p.FromMM(.5) if isinstance(item,p.PAD) else 0
  if bb.GetX()<edge.GetX()-margin or bb.GetY()<edge.GetY()-margin or bb.GetRight()>edge.GetRight()+margin or bb.GetBottom()>edge.GetBottom()+margin:
   outside.append({'uuid':item.m_Uuid.AsString(),'net':item.GetNetname(),'bbox_mm':[p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())]})
 report={'project':name,'components':len(components),'erc':dict(collections.Counter(v['severity']+':'+v['type'] for v in ev)),'drc':dict(collections.Counter(v['severity']+':'+v['type'] for v in drc['violations'])),'unconnected':len(drc['unconnected_items']),'PCB_pin_net_mismatches':mismatches,'missing_PCB_components':missing_components,'empty_schematic_paths':empty_paths,'duplicate_schematic_paths':duplicate_paths,'ordinary_tracks_on_RF_reference':foreign_inner,'copper_outside_board_bounds':outside,'pcb_sha256':hashlib.sha256((d/(name+'.kicad_pcb')).read_bytes()).hexdigest()}
 report['copper_layer_count']=b.GetCopperLayerCount()
 (vd/'final-summary.json').write_text(json.dumps(report,indent=2));print(name,json.dumps({k:v for k,v in report.items() if k not in ['pcb_sha256','PCB_pin_net_mismatches']},ensure_ascii=False),'pin-net mismatch',len(mismatches))
if __name__=='__main__':
 for name in sys.argv[1:]:run(name)
