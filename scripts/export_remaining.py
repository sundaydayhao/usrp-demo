from pathlib import Path
import json,sys
import pcbnew as p
from build_legacy_schematics import sexp,Q
ROOT=Path(__file__).resolve().parents[1]
def export(name):
 vd=ROOT/'verification'/name;b=p.LoadBoard(str(ROOT/'projects'/name/(name+'.kicad_pcb')));target=vd/(name+'-remaining.dsn');assert p.ExportSpecctraDSN(b,str(target))
 text=target.read_text().replace('(string_quote ")','(string_quote quote)');tree=sexp.parse(text);st=sexp.find(tree,'structure');st[:]=[x for x in st if not(isinstance(x,list) and str(x[0])=='plane' and 'In2.Cu' in str(x))]
 st.append(['control',['via_at_smd','on']])
 for layer in sexp.find_all(st,'layer'):
  if str(layer[1])=='In1.Cu':sexp.find(layer,'type')[1]='power'
 # Put the layer policy in the exchange file as well as CLI settings; older
 # engines otherwise route through the intended continuous In1 reference.
 st.insert(1+max(i for i,x in enumerate(st) if isinstance(x,list) and str(x[0])=='layer'),['autoroute_settings',['fanout','off'],['autoroute','on'],['postroute','off'],['vias','on'],
   *[['layer_rule',Q(layer),['active','off' if layer=='In1.Cu' else 'on'],['preferred_direction','horizontal' if layer in ['F.Cu','In2.Cu'] else 'vertical']] for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']]])
 # These boards deliberately use filled/capped via-in-pad for QFN exposed
 # pads and reviewed escapes. KiCad exports attach=off by default; leaving
 # that flag in place makes the router treat valid existing same-net
 # pad/via contacts as obstacles and disconnects the escape vias.
 for ps in sexp.find_all(sexp.find(tree,'library'),'padstack'):
  if str(ps[1]).startswith('Via[') or '[T]' in str(ps[1]) or '[B]' in str(ps[1]):
   attach=sexp.find(ps,'attach')
   if attach:attach[1]='on'
 classes=list(sexp.find_all(sexp.find(tree,'network'),'class'));power=next(c for c in classes if str(c[1])=='POWER')
 for rail in (['6V_RX','6V_TX'] if name=='WBX' else ['6V']):
  for c in classes:c[:]=[x for x in c if isinstance(x,list) or str(x)!=rail]
  power.insert(2,Q(rail))
 text=sexp.dumps(tree).replace('(string_quote quote)','(string_quote ")').replace('\t','  ').replace('\r','')
 esc=json.loads((vd/'dsn-character-map.json').read_text());esc.update({c:f'_U{ord(c):04X}_' for c in set(text) if ord(c)>127})
 for c,e in esc.items():text=text.replace(c,e)
 target.write_bytes(text.encode('ascii'));(vd/'dsn-character-map.json').write_text(json.dumps(esc));print(name,'exported; In1 reference remains continuous; In2 available for power/control')
if __name__=='__main__':
 for name in sys.argv[1:]:export(name)
