"""Read historical gEDA objects without executing gEDA configuration files."""
from pathlib import Path
import math, re
from collections import defaultdict

def read_objects(path):
    lines=Path(path).read_text(encoding='utf-8',errors='replace').splitlines()
    def block(i, end=None):
        out=[]
        while i<len(lines):
            line=lines[i].strip(); i+=1
            if line==end: return out,i
            if not line: continue
            if line in ('{','['):
                sub,i=block(i,'}' if line=='{' else ']')
                if out: out[-1]['attrs' if line=='{' else 'embedded']=sub
                continue
            f=line.split(); obj={'kind':f[0],'f':f[1:],'attrs':[]}
            if f[0]=='T':
                count=int(f[-1]) if len(f)>=10 else 1
                obj['text']='\n'.join(lines[i:i+count]); i+=count
            elif f[0]=='H':
                count=int(f[-1]); obj['path']=lines[i:i+count]; i+=count
            out.append(obj)
        return out,i
    return block(0)[0]

def attributes(objects):
    result=defaultdict(list)
    for o in objects:
        if o['kind']=='T' and '=' in o.get('text',''):
            k,v=o['text'].split('=',1); result[k].append(v)
    return dict(result)

def transform(x,y,origin,angle=0,mirror=0):
    if mirror: x=-x
    a=math.radians(angle)
    return (round(origin[0]+x*math.cos(a)-y*math.sin(a),6),
            round(origin[1]+x*math.sin(a)+y*math.cos(a),6))

def read_netlist(path):
    nets={}; pins={}
    for line in Path(path).read_text().replace('\\\n',' ').splitlines():
        f=line.split()
        if len(f)<2: continue
        net=f[0]; ns=[]
        for member in f[1:]:
            ref,pin=member.rsplit('-',1)
            if (ref,pin) in pins and pins[ref,pin]!=net:
                raise ValueError(f'duplicate source pin {ref}.{pin}')
            pins[ref,pin]=net; ns.append((ref,pin))
        nets[net]=ns
    return nets,pins

def source_model(sch,lib_root):
    symbol_paths={p.name:p for p in Path(lib_root).rglob('*.sym')}
    objects=read_objects(sch); components=[]; powers=[]; wires=[]; texts=[]
    for o in objects:
        if o['kind']=='N':
            p=list(map(int,o['f'][:4])); a=attributes(o['attrs'])
            wires.append({'a':tuple(p[:2]),'b':tuple(p[2:]),'name':a.get('netname',[None])[0]})
        elif o['kind']=='T':
            if len(o['f'])>4 and o['f'][4]=='1': texts.append(o)
        elif o['kind']=='C':
            f=o['f']; basename=f[-1]
            if basename.startswith('title'): continue
            definition=o.get('embedded') or read_objects(symbol_paths[basename])
            if basename=='ad813x.sym':
                # The archive's generated library was regenerated with a
                # different grid after LFRX was drawn. Restore the pin geometry
                # used by lfrx.sch/PDF; numbers are unchanged (SOIC-8 AD8132).
                places={'8':(100,1900,400,1900),'2':(100,1400,400,1400),
                        '1':(100,900,400,900),'3':(800,2700,800,2400),
                        '5':(2100,1900,1800,1900),'7':(2100,1400,1800,1400),
                        '4':(2100,900,1800,900),'6':(800,100,800,400)}
                definition=[d for d in definition if d['kind'] not in ('L','B')]
                definition.append({'kind':'B','f':['400','400','1400','2000'],'attrs':[]})
                for d in definition:
                    if d['kind']=='P':
                        pin=attributes(d['attrs'])['pinnumber'][0]
                        d['f'][:4]=[str(x) for x in places[pin]];d['f'][6]='0'
            base=attributes(definition); overrides=attributes(o['attrs']); a=base|overrides
            origin=tuple(map(int,f[:2])); angle=int(f[3]); mirror=int(f[4])
            xform=lambda x,y:transform(x,y,origin,angle,mirror)
            slot=int(a.get('slot',['1'])[0]); slotdefs={}
            for sd in base.get('slotdef',[]):
                k,v=sd.split(':',1); slotdefs[int(k)]=v.split(',')
            pinlist=[]
            for p in definition:
                if p['kind']!='P':continue
                pa=attributes(p['attrs']); nums=list(map(int,p['f'][:4])); end=int(p['f'][6])
                outer=xform(*nums[2*end:2*end+2]); inner=xform(*nums[2*(1-end):2*(1-end)+2])
                pin=pa.get('pinnumber',['?'])[0]
                if slot in slotdefs: pin=slotdefs[slot][int(pa['pinseq'][0])-1]
                pinlist.append({'number':pin,'name':pa.get('pinlabel',['~'])[0],
                                'type':pa.get('pintype',['pas'])[0], 'at':outer,'inner':inner})
            if 'refdes' not in a:
                if pinlist:
                    implicit=a.get('net',['GND:1'])[0].split(':',1)[0]
                    powers.append({'at':pinlist[0]['at'],'name':implicit})
                continue
            components.append({'ref':a['refdes'][0], 'attrs':a,'overrides':overrides,
              'definition':definition,'basename':basename,'origin':origin,'angle':angle,
              'mirror':mirror,'slot':slot,'pins':pinlist})
    return {'components':components,'powers':powers,'wires':wires,'texts':texts}

class DSU:
    def __init__(self):self.parent={}
    def find(self,p):
        self.parent.setdefault(p,p)
        if self.parent[p]!=p:self.parent[p]=self.find(self.parent[p])
        return self.parent[p]
    def join(self,a,b):self.parent[self.find(a)]=self.find(b)

def on_segment(p,a,b):
    return abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-5 and min(a[0],b[0])-1e-6<=p[0]<=max(a[0],b[0])+1e-6 and min(a[1],b[1])-1e-6<=p[1]<=max(a[1],b[1])+1e-6

def assign_nets(model,expected_pins):
    d=DSU(); points=set()
    for w in model['wires']:d.join(w['a'],w['b']);points.update((w['a'],w['b']))
    for c in model['components']:
        for p in c['pins']:points.add(p['at'])
    for p in model['powers']:points.add(p['at'])
    for w in model['wires']:
        for p in points:
            if on_segment(p,w['a'],w['b']):d.join(p,w['a'])
    names=defaultdict(set)
    for w in model['wires']:
        if w['name']:names[d.find(w['a'])].add(w['name'])
    for p in model['powers']:names[d.find(p['at'])].add(p['name'])
    for c in model['components']:
        for p in c['pins']:
            n=expected_pins.get((c['ref'],p['number']))
            if n:names[d.find(p['at'])].add(n)
    # Named sources may have synonymous labels; fail on conflicting named nets.
    for root,ns in names.items():
        meaningful={n for n in ns if not n.startswith('unnamed_net')}
        if len(meaningful)>1:raise ValueError(f'Conflicting source nets at {root}: {ns}')
    def net(p):
        ns=names[d.find(p)]
        if not ns:return None
        return sorted(ns,key=lambda n:(n.startswith('unnamed_net'),n))[0]
    for w in model['wires']:w['net']=net(w['a'])
    for c in model['components']:
        for p in c['pins']:p['net']=net(p['at'])
    return model
