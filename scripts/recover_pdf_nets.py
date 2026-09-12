"""Recover connectivity from the PDF's vector endpoints, with an audit trail.

This stage does not certify a netlist. Ambiguous labels, missing terminals,
and inconsistent names are recorded for comparison with the source drawing.
"""
from pathlib import Path
import json, math, re, collections, bisect
from geda_model import DSU, on_segment
ROOT=Path(__file__).resolve().parents[1]

def display(p,page):
    return (1224-p[1],p[0]) if page['rotation']==90 else tuple(p)
def box(b,page):
    pts=[display(b[:2],page),display(b[2:],page)]
    return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]
def eligible(s):
    return bool(re.fullmatch(r'(?:[A-Z0-9_]+:1|(?:AUX_(?:ADC|DAC)_[A-Z0-9_]+)|(?:I2C_A[01](?:_[RT]X)?)|(?:io_[rt]x_\d\d)|(?:LO_[RT]X(?:_[NP]|_test_[np])?)|(?:[RT]X_(?:CONN|PUP_[35]V))|(?:RF_[RT]X)|(?:I(?:BB|OUT)[NP](?:_[AB])?)|(?:QBB[NP])|(?:VIN[NP]_[AB])|(?:VREF|Vocm|local_vref)|(?:clock_(?:[rt]x_)?p)|(?:SC(?:LK|L)|SD[AOI]|SEN)(?:_[RT]X)?|(?:XTAL[NP])|(?:U[34]_TEST[12])|(?:DGND_NC|RESET|RS232_[RT]XD|TCK|TDI|TDO|TMS|3_3V_RF))',s))
def recover(name):
    pages=json.loads((ROOT/'verification'/name/'pdf-vector-extraction.json').read_text());out=[]
    for page in pages:
        used={s for p in page['parts'] for s in p['drawing_sequences']}
        textused={s for p in page['parts'] for s in range(min(p['drawing_sequences']),p['seq']+1)}
        lines=[]
        for dd in page['drawings']:
            if dd['seq'] in used or dd['type']!='s' or len(dd['items'])!=1 or dd['items'][0][0]!='l':continue
            aa,bb=[display(p,page) for p in dd['items'][0][1:]]
            if abs(aa[0]-bb[0])>.02 and abs(aa[1]-bb[1])>.02:continue
            if math.dist(aa,bb)<.02:continue
            lines.append({'a':aa,'b':bb,'seq':dd['seq']})
        # Cluster printed coordinates; the PDF rounds to 1/1000 point.
        axes=[]
        for axis in (0,1):
            vals=sorted([s[k][axis] for s in lines for k in ['a','b']]+[display(p['xy'],page)[axis] for part in page['parts'] for p in part['pins']]);groups=[]
            for v in vals:
                if not groups or v-groups[-1][-1]>.02:groups.append([v])
                else:groups[-1].append(v)
            axes.append([round(sum(g)/len(g),4) for g in groups])
        def snap(p):
            return tuple(min(ax,key=lambda v:abs(v-p[i])) for i,ax in enumerate(axes))
        pins=[]
        for part in page['parts']:
            for pin in part['pins']:
                pins.append({'ref':part['ref'],'number':pin['number'],'at':snap(display(pin['xy'],page)),'seq':part['seq']})
        for s in lines:
            s['a']=snap(s['a']);s['b']=snap(s['b'])
        points={p for s in lines for p in [s['a'],s['b']]}|{p['at'] for p in pins}
        dsu=DSU()
        for s in lines:
            dsu.join(s['a'],s['b'])
            for p in points:
                if on_segment(p,s['a'],s['b']):dsu.join(p,s['a'])
        roots_with_pins={dsu.find(p['at']) for p in pins}
        labels=[];label_issues=[]
        active=[s for s in lines if dsu.find(s['a']) in roots_with_pins]
        label_words=list(page['words']);known_words={(w['seq'],w['text']) for w in label_words}
        label_words += [t for t in page['texts'] if eligible(t['text']) and (t['seq'],t['text']) not in known_words]
        for w in label_words:
            if w['seq'] in textused or not eligible(w['text']):continue
            bb=box(w['bbox'],page);c=((bb[0]+bb[2])/2,(bb[1]+bb[3])/2)
            power=w['text'].endswith(':1')
            scores=[]
            for s in active:
                lo=[min(s['a'][i],s['b'][i]) for i in (0,1)];hi=[max(s['a'][i],s['b'][i]) for i in (0,1)]
                dx=max(lo[0]-bb[2],bb[0]-hi[0],0);dy=max(lo[1]-bb[3],bb[1]-hi[1],0)
                dist=math.hypot(dx,dy)
                # A port's two strokes immediately precede its text event.
                temporal=.0 if 0<w['seq']-s['seq']<=2 else .8
                score=dist+temporal
                scores.append((score,s))
            scores.sort(key=lambda x:x[0])
            if not scores or scores[0][0]>8:
                label_issues.append({'label':w['text'],'bbox':bb,'reason':'No wire within 8 pt','nearest_distance':scores[0][0] if scores else None});continue
            score,s=scores[0];root=dsu.find(s['a']);alternative=next(((ss,ln) for ss,ln in scores if dsu.find(ln['a'])!=root),None)
            if alternative and alternative[0]-score<.2:
                label_issues.append({'label':w['text'],'bbox':bb,'reason':'Ambiguous nearest wire','scores':[score,alternative[0]],'candidates':[s,alternative[1]]})
            pp=min([s['a'],s['b']],key=lambda p:math.dist(p,c))
            labels.append({'name':w['text'].removesuffix(':1'),'at':pp,'seq':w['seq'],'bbox':bb,'source_power':power,'wire_seq':s['seq'],'distance':score})
        names=collections.defaultdict(set)
        for lab in labels:names[dsu.find(lab['at'])].add(lab['name'])
        conflicts=[{'at':r,'names':sorted(ns)} for r,ns in names.items() if len(ns)>1]
        rootnames={r:(sorted(names[r])[0] if names[r] else f"P{page['page']}_N{i+1:03}") for i,r in enumerate(sorted(roots_with_pins))}
        def net(at):return rootnames.get(dsu.find(at))
        for pin in pins:pin['net']=net(pin['at']);pin['connected']=any(on_segment(pin['at'],s['a'],s['b']) for s in active)
        for s in active:s['net']=net(s['a'])
        for lab in labels:lab['net']=net(lab['at'])
        np=collections.Counter(p['net'] for p in pins)
        singletons=[p for p in pins if np[p['net']]==1 and not names[dsu.find(p['at'])]]
        orphan=[p for p in pins if not p['connected']]
        row={'page':page['page'],'pins':pins,'wires':active,'labels':labels,'conflicts':conflicts,'label_issues':label_issues,'orphan_pins':orphan,'unnamed_singletons':singletons}
        out.append(row)
        print(name,page['page'],'pins',len(pins),'nets',len(rootnames),'conflicts',len(conflicts),'labels',len(labels),'label_issues',len(label_issues),'orphans',len(orphan),'singletons',len(singletons))
        print('CONFLICTS',conflicts)
        print('ORPHANS',[(p['ref'],p['number']) for p in orphan])
    (ROOT/'verification'/name/'pdf-net-recovery.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':
    for name in ['WBX','TVRX2']:recover(name)
