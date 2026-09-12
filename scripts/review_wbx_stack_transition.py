"""Audit WBX layer transition and exact preservation of the reviewed RF geometry."""
from pathlib import Path
import json,sys,collections,hashlib
sys.path.insert(0,r'C:\projects\kicad-projects\tools\KiSkill-main')
from kicad_lib import sexp
root=Path(__file__).resolve().parents[1];vd=root/'verification/WBX';file=root/'projects/WBX/WBX.kicad_pcb';oldfile=root/'tmp/checkpoints/WBX/four-layer-last/WBX.kicad_pcb';rf=set(sum(json.loads((vd/'rf-net-classes.json').read_text()).values(),[]))
def items(node,key):return [a for a in node if isinstance(a,list) and str(a[0])==key]
def one(node,key):return next(iter(items(node,key)),None)
def geom(node):
 return collections.Counter(tuple((key,tuple(one(t,key)[1:])) for key in ['net','start','end','width','layer']) for t in items(node,'segment') if str(one(t,'net')[1]) in rf)
a=sexp.load_file(oldfile);c=sexp.load_file(file);ga,gc=geom(a),geom(c);assert ga==gc,'RF geometry changed'
stack=one(one(c,'setup'),'stackup');layers=[]
for layer in items(stack,'layer'):
 layers.append({'name':str(layer[1]),'type':str(one(layer,'type')[1]),'thickness_mm':float(one(layer,'thickness')[1])})
assert len([z for z in layers if z['type']=='copper'])==6
assert layers[1]['name']=='dielectric 1' and layers[1]['thickness_mm']==.2104
assert not any(str(one(v,'net')[1]) in rf for v in items(c,'via'))
summary={'comparison_baseline':'four-layer-last checkpoint before six-layer conversion','RF_segment_geometry_unchanged':True,'RF_segment_count':sum(gc.values()),'copper_layer_count':6,'stack_layers':layers,'stack_total_mm':sum(z['thickness_mm'] for z in layers),'RF_reference_distance_mm':.2104,'stack_status':'Custom target, fabricator confirmation required','pcb_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(vd/'delivery-review.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
