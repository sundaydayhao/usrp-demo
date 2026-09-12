"""Independent text-block inventory, compared with the editable project refs.

This is independent of the vector-to-net recovery, but cannot establish that
every recovered PDF junction is correct; visual/source review remains necessary.
"""
from pathlib import Path
import re,json,xml.etree.ElementTree as ET
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
for name in ['WBX','TVRX2']:
 observed={};events=[]
 for i,page in enumerate(fitz.open(ROOT/'usrp1-daughterboard'/(name.lower()+'.pdf'))):
  for block in page.get_text('blocks'):
   text=block[4]
   refs=set(re.findall(r'(?<![A-Za-z0-9_])((?:FB|[RCLDUJTMQ])\d{1,3})(?![\d_])',text))
   # Manually reviewed printed run: C201 + 0.01uF have no separator.
   if 'C201' in text:refs.add('C201')
   refs.update(re.findall(r'U\d{3}(?!\d)',text))
   # ADA4937 pin names +FB1/-FB1/+FB2/-FB2 are feedback pins.
   if re.search(r'[+−-]FB[12]',text):refs-={'FB1','FB2'}
   for ref in refs:observed.setdefault(ref,[]).append(i+1)
   if refs:events.append({'page':i+1,'refs':sorted(refs),'text':text})
 project={c.attrib['ref'] for c in ET.parse(ROOT/'verification'/name/'export.net').findall('./components/comp')}
 extra=set(observed)-project
 # Text-only design notes may name values/models; retain all for inspection.
 report={'pdf_reference_count':len(observed),'project_reference_count':len(project),'missing_from_project':sorted(extra),'not_found_in_pdf_text':sorted(project-set(observed)),'pages_by_reference':observed,'text_block_evidence':events}
 (ROOT/'verification'/name/'independent-reference-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print(name,'PDF',len(observed),'project',len(project),'missing',sorted(extra),'not in PDF',sorted(project-set(observed)))
