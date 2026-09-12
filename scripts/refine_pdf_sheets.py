"""Move complete schematic geometry together; never move cached symbol pins.

The final exported pin-set comparison is required after this formatting pass.
"""
from pathlib import Path
import sys
from build_legacy_schematics import sexp,Q
ROOT=Path(__file__).resolve().parents[1]

def shift(node,dx,dy):
 for a in node[1:]:
  if not isinstance(a,list):continue
  if str(a[0]) in ('at','xy'):
   a[1]=round(float(a[1])+dx,4);a[2]=round(float(a[2])+dy,4)
  else:shift(a,dx,dy)

def refine(name):
 for file in (ROOT/'projects'/name).glob('*.kicad_sch'):
  doc=sexp.load_file(file)
  # A marker in the title comments makes this pass idempotent.
  title=sexp.find(doc,'title_block')
  if 'Margins reviewed' in str(title):
   orient_labels(doc);sexp.save_file(file,doc);continue
  if name=='WBX' and file.stem==name:
   sexp.find(doc,'paper')[1]=Q('A3')
   for s in sexp.find_all(doc,'sheet'):
    dx=254-float(sexp.find(s,'at')[1]);shift(s,dx,0)
  for item in doc[1:]:
   if not isinstance(item,list):continue
   if str(item[0]) in ('symbol','sheet','wire','junction','no_connect','label','global_label','hierarchical_label','text','polyline'):
    shift(item,25.4,0)
   if str(item[0])=='symbol':
    props={str(a[1]):a for a in sexp.find_all(item,'property')}
    value=str(props.get('Value',['','',''])[2])
    if value in ('M2.5 GND','TestPoint'):
     eff=sexp.find(props['Value'],'effects');eff.append(['hide','yes'])
  if title:title.append(['comment',9,Q('Margins reviewed; PDF-derived editable design')])
  orient_labels(doc)
  sexp.save_file(file,doc)
 print(name,'sheet margins refined')

def orient_labels(doc):
 wires=[[(float(q[1]),float(q[2])) for q in sexp.find(w,'pts')[1:]] for w in sexp.find_all(doc,'wire')]
 for lab in sexp.find_all(doc,'global_label'):
  at=sexp.find(lab,'at');pt=(float(at[1]),float(at[2]))
  branches=[b if a==pt else a for a,b in wires if a==pt or b==pt]
  horizontal=[p for p in branches if p[1]==pt[1]]
  # Place the label body outside an open horizontal wire endpoint.
  if len(horizontal)==1:
   right=horizontal[0][0]>pt[0]
   at[3]=0 if right else 180
   j=sexp.find(sexp.find(lab,'effects'),'justify')
   if j:j[1]='right' if right else 'left'
if __name__=='__main__':
 for name in sys.argv[1:]:refine(name)
