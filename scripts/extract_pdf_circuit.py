"""Recover vector circuit objects from gschem PDF plots for manual auditing.

This is an intermediate representation, never considered a verified netlist.
Run with the workspace Python (PyMuPDF).
"""
from pathlib import Path
import re,json,collections,math
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
REF=re.compile(r'^(?:FB|[RCLDUJTQM])\d+$')
def string(s):return ''.join(chr(c[0]) for c in s['chars'])
def simple(d):return len(d['items'])==1 and d['items'][0][0]=='l'
def extract(name):
    pdf=fitz.open(ROOT/'usrp1-daughterboard'/(name.lower()+'.pdf'));pages=[]
    for pageidx,page in enumerate(pdf):
        drawings=page.get_drawings();texts=page.get_texttrace();words=page.get_text('words');byseq=collections.defaultdict(list)
        for t in texts:byseq[t['seqno']].append(t)
        refs=[]
        for w in words:
            if not REF.fullmatch(w[4]):continue
            bbox=fitz.Rect(w[:4]);middle=(bbox.tl+bbox.br)/2
            options=[s for s in texts if w[4] in string(s) and fitz.Rect(s['bbox']).contains(middle)]
            if not options:raise ValueError(f'{name} page {pageidx+1}: cannot identify text event {w[4]}')
            s=min(options,key=lambda s:fitz.Rect(s['bbox']).get_area());refs.append({'ref':w[4],'seq':s['seqno'],'text_bbox':list(bbox)})
        # Occasionally a reference touches its device text in the printed
        # PDF; the text extractor then returns one joined word.
        known={(r['ref'],r['seq']) for r in refs}
        for s in texts:
            for ref in re.findall(r'U\d{3}(?!\d)',string(s)):
                if (ref,s['seqno']) not in known and not any(rr.startswith('U') and ss==s['seqno'] for rr,ss in known):refs.append({'ref':ref,'seq':s['seqno'],'text_bbox':list(s['bbox'])});known.add((ref,s['seqno']))
            # WBX C201 and its 0.01uF value are one text event/one PDF word:
            # C2010.01uF. The reference has three digits; the fourth is value.
            merged=re.match(r'^([RCL]\d{3})(?=[\d.]+.*(?:uF|pF|nF|nH|uH|%))',string(s))
            if merged and (merged[1],s['seqno']) not in known:
                refs.append({'ref':merged[1],'seq':s['seqno'],'text_bbox':list(s['bbox'])});known.add((merged[1],s['seqno']))
        refs=[r for r in refs if not ('=' in ' '.join(string(s) for s in byseq[r['seq']]) and r['ref'].startswith(('R','C','L')))]
        refs.sort(key=lambda r:r['seq']);parts=[];used=set();previous=-1
        for ref in refs:
            seq=ref['seq'];rawtext=' '.join(string(s) for s in byseq[seq]);part={**ref,'rawtext':rawtext,'pins':[]}
            before=[d for d in drawings if previous<d['seqno']<seq and d['type']=='s']
            if ref['ref'].startswith(('R','C','L','FB')):
                cap=('pF' in rawtext or 'uF' in rawtext or 'nF' in rawtext or ref['ref'].startswith('C'))
                polar=cap and any(string(s).strip() in ('1','2') for s in texts if max(previous,seq-15)<s['seqno']<seq)
                count=9 if ref['ref'].startswith('R') and not cap else (11 if ref['ref'].startswith(('L','FB')) else (8 if polar else 6))
                selected=before[-count:];part['kind']='resistor' if count==9 else 'inductor' if count==11 else 'capacitor';part['polar']=polar
                pts=[item[k] for d in selected for item in d['items'] if item[0]=='l' for k in (1,2)]
                if pts:
                    axis=0 if max(q.x for q in pts)-min(q.x for q in pts)>max(q.y for q in pts)-min(q.y for q in pts) else 1
                    lo=min(pts,key=lambda q:q[axis]);hi=max(pts,key=lambda q:q[axis]);part['pins']=[{'number':'1','xy':list(lo)},{'number':'2','xy':list(hi)}]
            else:
                part['kind']='multi_pin';selected=[]
                # Most generated gEDA ICs end with four rectangle strokes.
                tail=before[-4:]
                rect=None
                if len(tail)==4 and all(simple(d) for d in tail):
                    ends=[tuple(q) for d in tail for q in d['items'][0][1:]]
                    if len(set(ends))==4 and all(v==2 for v in collections.Counter(ends).values()):rect=fitz.Rect(min(q[0] for q in ends),min(q[1] for q in ends),max(q[0] for q in ends),max(q[1] for q in ends))
                bound=(rect+(-20,-20,20,20)) if rect else None
                pintexts=[s for s in texts if previous<s['seqno']<=seq and re.match(r'^\d{1,2}(?:[^\d]|$)',string(s)) and ':' not in string(s) and '24Cxx' not in string(s)]
                if bound:pintexts=[s for s in pintexts if bound.intersects(fitz.Rect(s['bbox']))]
                for t in pintexts:
                    m=re.match(r'^(\d{1,2})(.*)',string(t));prior=[d for d in before if d['seqno']<t['seqno'] and simple(d)]
                    if not prior:continue
                    line=prior[-1];aa,bb=line['items'][0][1:]
                    if rect:
                        center=(rect.tl+rect.br)/2;outer=max([aa,bb],key=lambda q:abs(q-center));inner=min([aa,bb],key=lambda q:abs(q-center))
                    else:outer=bb;inner=aa
                    part['pins'].append({'number':m[1],'name':m[2],'xy':list(outer),'inner':list(inner),'text_seq':t['seqno'],'line_seq':line['seqno']})
                if part['pins']:
                    if ref['ref'].startswith('J') and any(string(s)=='5' for s in byseq[seq]):part['pins']=[pin for pin in part['pins'] if int(pin['number'])<=5]
                    if not rect:
                        ends=[q for pin in part['pins'] for q in [pin['xy'],pin['inner']]];center=fitz.Point(sum(q[0] for q in ends)/len(ends),sum(q[1] for q in ends)/len(ends))
                        for pin in part['pins']:
                            aa,bb=fitz.Point(pin['xy']),fitz.Point(pin['inner']);pin['xy']=list(max([aa,bb],key=lambda q:abs(q-center)));pin['inner']=list(min([aa,bb],key=lambda q:abs(q-center)))
                    start=min(x['line_seq'] for x in part['pins']);selected=[d for d in before if d['seqno']>=start]
                elif ref['ref'].startswith('M') or (name=='TVRX2' and ref['ref'].startswith('T')):
                    count=2 if ref['ref'].startswith('M') else 5;selected=before[-count:];lead=selected[0]['items'][0]
                    if lead[0]!='l':raise ValueError('Missing mechanical/test point lead')
                    pts=[q for dd in selected[1:] for item in dd['items'] for q in item[1:] if isinstance(q,fitz.Point)];center=fitz.Point(sum(q.x for q in pts)/len(pts),sum(q.y for q in pts)/len(pts));outer=max(lead[1:],key=lambda q:abs(q-center));inner=min(lead[1:],key=lambda q:abs(q-center));part['pins']=[{'number':'1','xy':list(outer),'inner':list(inner)}]
                    part['kind']='mounting_hole' if ref['ref'].startswith('M') else 'test_point'
                if rect:part['body_bbox']=list(rect)
            part['drawing_sequences']=[d['seqno'] for d in selected];used.update(part['drawing_sequences']);parts.append(part);previous=seq
        # Serialize plot coordinates in their unrotated PDF system.
        serialized=[]
        for d in drawings:
            items=[]
            for item in d['items']:
                items.append([item[0],*[list(x) if isinstance(x,(fitz.Point,fitz.Rect)) else x for x in item[1:]]])
            serialized.append({'seq':d['seqno'],'items':items,'type':d['type'],'width':d['width']})
        word_data=[]
        for w in words:
            bbox=fitz.Rect(w[:4]);middle=(bbox.tl+bbox.br)/2
            options=[s for s in texts if w[4] in string(s) and fitz.Rect(s['bbox']).contains(middle)]
            if options:
                ss=min(options,key=lambda s:fitz.Rect(s['bbox']).get_area());word_data.append({'text':w[4],'seq':ss['seqno'],'bbox':list(bbox),'dir':list(ss['dir'])})
        pages.append({'page':pageidx+1,'rotation':page.rotation,'rect':list(page.rect),'parts':parts,'drawings':serialized,'words':word_data,'texts':[{'seq':s['seqno'],'text':string(s),'bbox':list(s['bbox']),'dir':list(s['dir'])} for s in texts]})
        print(name,pageidx+1,len(parts),'units',len({p['ref'] for p in parts}),'components',collections.Counter(p['kind'] for p in parts))
        print('IC pin counts:',[(p['ref'],p['rawtext'],len(p['pins'])) for p in parts if p['kind']=='multi_pin'])
    out=ROOT/'verification'/name;out.mkdir(parents=True,exist_ok=True);(out/'pdf-vector-extraction.json').write_text(json.dumps(pages,indent=2))
if __name__=='__main__':
    for name in ['WBX','TVRX2']:extract(name)
