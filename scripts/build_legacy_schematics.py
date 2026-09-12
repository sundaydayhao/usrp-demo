"""Reconstruct editable KiCad schematics from gEDA geometry and audited nets.

Run with KiCad's Python. Original copper is imported separately by KiCad's
native gEDA importer. All generated symbols are stored in project-local libs.
"""
from pathlib import Path
import sys, uuid, json, math, collections, copy
sys.path.insert(0,'C:/projects/kicad-projects/tools/KiSkill-main')
from kicad_lib import sexp
from kicad_lib.verify import Seg, Pin, verify
from geda_model import *

ROOT=Path(__file__).resolve().parents[1]
GEDA=ROOT/'tmp/source-audit/geda'
SOURCES={'BasicRX':'basic-dboard/rxmod','BasicTX':'basic-dboard/txmod',
         'LFRX':'basic-lf/lfrx','LFTX':'basic-lf/lftx','TVRX':'tvrx/tvrx'}
Q=sexp.QStr.of; S=sexp.Sym
def n(tag,*xs):return [S(tag),*[S(str(x)) if isinstance(x,(float,int)) else x for x in xs]]
def a(v):return S(str(v))
def uid(name):return str(uuid.uuid5(uuid.NAMESPACE_URL,'usrp-reconstruction/'+name))
def effects(size=1.0,hide=False,justify=None):
    x=n('effects',n('font',n('size',size,size)))
    if justify:x.append(n('justify',*[S(j) for j in justify.split()]))
    if hide:x.append(n('hide',S('yes')))
    return x
def prop(k,v,x=0,y=0,hide=False):return n('property',Q(k),Q(str(v)),n('at',x,y,0),effects(1.0,hide))
def stroke(w=.18):return n('stroke',n('width',w),n('type',S('default')))
def pt(x,y):return n('xy',round(x,4),round(y,4))
def poly(ps):return n('polyline',n('pts',*[pt(*p) for p in ps]),stroke(),n('fill',n('type',S('none'))))
def make_label(text,p,key):
    return n('label',Q(text),n('at',*p,0),effects(.9,justify='left bottom'),n('uuid',Q(uid(key))))
def ktype(t):return {'in':'input','out':'output','io':'bidirectional','pwr':'power_in','pas':'passive','clk':'input','nc':'no_connect','oc':'open_collector','tp':'tri_state'}.get(t,'passive')

def build(name):
    stem=SOURCES[name]; model=source_model(GEDA/(stem+'.sch'),GEDA)
    nets,expected=read_netlist(GEDA/(stem+'.net'));assign_nets(model,expected)
    allpts=[p['at'] for c in model['components'] for p in c['pins']]+[p for w in model['wires'] for p in (w['a'],w['b'])]
    xmin=min(p[0] for p in allpts)-1500; ymax=max(p[1] for p in allpts)+1800
    # gEDA 100 mil grid becomes a 1.27 mm KiCad grid; graphic vertices need
    # not be on the electrical grid. Electrical endpoints are snapped together.
    def world(p,snap=True):
        x=(p[0]-xmin)*.0127;y=(ymax-p[1])*.0127
        if snap:return (round(round(x/1.27)*1.27,3),round(round(y/1.27)*1.27,3))
        return (round(x,4),round(y,4))
    width=max(world(p)[0] for p in allpts)+90;height=max(world(p)[1] for p in allpts)+45
    paper='A3' if width<420 and height<280 else ('A2' if width<594 and height<405 else 'A1')
    rootid=uid(name+'/root'); project=ROOT/'projects'/name;project.mkdir(parents=True,exist_ok=True)
    doc=n('kicad_sch',n('version',20250114),n('generator',Q('eeschema')),n('generator_version',Q('10.0')),n('uuid',Q(rootid)),n('paper',Q(paper)),n('title_block',n('title',Q(name+' - USRP1 daughterboard')),n('date',Q('2026-09-12')),n('rev',Q('R0')),n('company',Q('Reconstructed from Ettus Research sources')),n('comment',1,Q('RF matching and USRP1 connector retained; see README for verification.'))))
    cache=n('lib_symbols');doc.append(cache); library=n('kicad_symbol_lib',n('version',20241209),n('generator',Q('kicad_symbol_editor')))
    comps=collections.defaultdict(list)
    for c in model['components']:comps[c['ref']].append(c)
    smap={}; modeled_pins=[]; geom_pins=[]; labels=[]; power_ports=[]
    for ref,units in comps.items():
        base=units[0];attrs=base['attrs']; value=attrs.get('value',attrs.get('device',[base['basename'].removesuffix('.sym')]))[0]
        symname=ref+'_'+base['basename'].removesuffix('.sym').replace('-','_'); libid='USRP:'+symname
        definition=n('symbol',Q(symname),n('pin_names',n('offset',.5)),n('exclude_from_sim',S('no')),n('in_bom',S('yes')),n('on_board',S('yes')),prop('Reference',ref.rstrip('0123456789')),prop('Value',value),prop('Footprint','USRP:'+ref,hide=True))
        passive=base['basename'] in ('resistor-1.sym','capacitor-1.sym','capacitor-2.sym','inductor-1.sym')
        if passive:definition.insert(2,n('pin_numbers',S('hide')))
        # Reproduce each source unit with its actual orientation baked into
        # its symbol. This makes the pin positions independent of text rotation.
        present=set();unit_info=[]
        for unit,c in enumerate(units,1):
            origin=world(c['origin']);group=n('symbol',Q(f'{symname}_{unit}_1'))
            def local(p):
                x,y=world(transform(*p,c['origin'],c['angle'],c['mirror']),False)
                return (round(x-origin[0],4),round(origin[1]-y,4))
            for o in c['definition']:
                f=o['f'];kind=o['kind']
                if kind=='L':group.append(poly([local(tuple(map(int,f[:2]))),local(tuple(map(int,f[2:4])))]))
                elif kind=='B':
                    x,y,w,h=map(int,f[:4]);group.append(poly([local((x,y)),local((x+w,y)),local((x+w,y+h)),local((x,y+h)),local((x,y))]))
                elif kind=='V':
                    x,y,r=map(int,f[:3]);group.append(n('circle',n('center',*local((x,y))),n('radius',r*.0127),stroke(),n('fill',n('type',S('none')))))
                elif kind=='A':
                    x,y,r,start,sweep=map(float,f[:5]);ps=[]
                    for j in range(max(8,int(abs(sweep)/12))+1):
                        theta=math.radians(start+sweep*j/max(8,int(abs(sweep)/12)))
                        ps.append(local((x+r*math.cos(theta),y+r*math.sin(theta))))
                    group.append(poly(ps))
            for p in c['pins']:
                pos=world(p['at']);inner=world(p['inner']);dx=inner[0]-pos[0];dy=inner[1]-pos[1]
                angle={ (1,0):0,(-1,0):180,(0,1):270,(0,-1):90}.get((int(math.copysign(1,dx)) if dx else 0,int(math.copysign(1,dy)) if dy else 0),0)
                length=round(math.hypot(dx,dy),3); pinname=p['name']
                if pinname=='n/c' and p['number']=='7' and c['basename']=='24Cxx-1.sym':pinname='WP'
                group.append(n('pin',S(ktype(p['type'])),S('line'),n('at',round(pos[0]-origin[0],3),round(origin[1]-pos[1],3),angle),n('length',length),n('name',Q(pinname),effects(.8)),n('number',Q(p['number']),effects(.8))))
                present.add(p['number']);modeled_pins.append((ref,p['number'],pos,p['net']))
                if p['net']:geom_pins.append(Pin(p['net'],pos,ref+'.'+p['number']))
                else:doc.append(n('no_connect',n('at',*pos),n('uuid',Q(uid(name+'/'+ref+'/'+p['number']+'/nc')))))
            definition.append(group);unit_info.append((unit,origin,c))
        missing=sorted({pin for (r,pin) in expected if r==ref}-present,key=lambda p:int(p) if p.isdigit() else 999)
        if missing:
            unit=len(units)+1; group=n('symbol',Q(f'{symname}_{unit}_1'));group.append(poly([(0,2.54),(17.78,2.54),(17.78,-2.54*len(missing)),(0,-2.54*len(missing)),(0,2.54)]))
            pos=(round((width-65)/1.27)*1.27,round((25+len(power_ports)*20)/1.27)*1.27)
            for j,pin in enumerate(missing):
                net=expected[ref,pin]; group.append(n('pin',S('power_in'),S('line'),n('at',-5.08,-j*2.54,0),n('length',5.08),n('name',Q(net),effects(.8)),n('number',Q(pin),effects(.8))))
                outer=(round(pos[0]-5.08,3),round(pos[1]+j*2.54,3)); end=(round(outer[0]-5.08,3),outer[1])
                power_ports.append((outer,end,net));modeled_pins.append((ref,pin,outer,net));geom_pins.append(Pin(net,outer,ref+'.'+pin))
            definition.append(group);unit_info.append((unit,pos,base))
        library.append(copy.deepcopy(definition));cached=copy.deepcopy(definition);cached[1]=Q(libid);cache.append(cached)
        for unit,pos,c in unit_info:
            instanceid=uid(name+'/'+ref+'/'+str(unit));smap.setdefault(ref,instanceid)
            # Field placement follows source coordinates where supplied.
            overrides=[o for o in c.get('overrides',{})]
            symbol_points=[world(p['at']) for p in c['pins']]
            sx=(min(p[0] for p in symbol_points)+max(p[0] for p in symbol_points))/2
            sy=min(p[1] for p in symbol_points)
            refpos=(sx,sy-4.0);valpos=(sx,sy-2.0)
            raw_ref=next((o for o in c['definition'] if o['kind']=='T' and o.get('text','').startswith('refdes=')),None)
            if unit<=len(units):
                # Source instance attribute positions, not symbol defaults.
                source_o=next(o for o in read_objects(GEDA/(stem+'.sch')) if o['kind']=='C' and attributes(o['attrs']).get('refdes',[None])[0]==ref and tuple(map(int,o['f'][:2]))==c['origin'])
                if passive:
                    pp=[world(p['at']) for p in c['pins']]
                    cx=sum(p[0] for p in pp)/len(pp);cy=sum(p[1] for p in pp)/len(pp)
                    if pp[0][0]==pp[-1][0]:refpos=(cx+4,cy-1);valpos=(cx+4,cy+1)
                    else:refpos=(cx,cy-3);valpos=(cx,cy-1.4)
            else:refpos=(pos[0]+8.89,pos[1]-6);valpos=(pos[0]+8.89,pos[1]-4)
            instance=n('symbol',n('lib_id',Q(libid)),n('at',*pos,0),n('unit',unit),n('exclude_from_sim',S('no')),n('in_bom',S('yes')),n('on_board',S('yes')),n('dnp',S('yes' if value.lower()=='none' else 'no')),n('uuid',Q(instanceid)),prop('Reference',ref,*refpos),prop('Value',value,*valpos),prop('Footprint','USRP:'+ref,*pos,True),prop('Source',stem+'.sch',*pos,True),n('instances',n('project',Q(name),n('path',Q('/'+rootid),n('reference',Q(ref)),n('unit',unit)))))
            doc.append(instance)
    # Electrical wires retain source topology. Split all wires at existing
    # connection points, remove double-draws, and insert explicit junctions.
    segments=[]
    for w in model['wires']:
        if not w['net']:raise ValueError('Unnamed source wire '+str(w))
        aa,bb=world(w['a']),world(w['b'])
        if aa!=bb:segments.append(Seg(w['net'],aa,bb))
        if w['name']:labels.append((w['net'],aa))
    for p in model['powers']:labels.append((p['name'],world(p['at'])))
    for aa,bb,net in power_ports:segments.append(Seg(net,aa,bb));labels.append((net,bb))
    for c in model['components']:
        for p in c['pins']:
            pos=world(p['at'])
            if p['type']=='pwr' and p['net'] and not any(on_segment(pos,s.a,s.b) for s in segments):
                inn=world(p['inner']);dx=pos[0]-inn[0];dy=pos[1]-inn[1]
                end=(round(pos[0]+(2.54 if dx>0 else -2.54 if dx<0 else 0),3),round(pos[1]+(2.54 if dy>0 else -2.54 if dy<0 else 0),3))
                segments.append(Seg(p['net'],pos,end));labels.append((p['net'],end))
    points={p for s in segments for p in [s.a,s.b]}|{p.p for p in geom_pins}
    split=set()
    for s in segments:
        ps=sorted([p for p in points if on_segment(p,s.a,s.b)])
        for aa,bb in zip(ps,ps[1:]):
            if aa!=bb:split.add((s.net,aa,bb))
    segments=[Seg(*x) for x in sorted(split)]
    # Put labels at open ends (gschem printed the name inside a longer wire,
    # which KiCad otherwise reports as a dangling wire tail).
    pin_positions={p.p for p in geom_pins}
    degree=collections.Counter(p for s in segments for p in (s.a,s.b))
    opens=[(s.net,p) for s in segments for p in (s.a,s.b) if degree[p]==1 and p not in pin_positions]
    named={net for net,p in labels}
    labels=labels+[(net,p) for net,p in opens if net in named]
    junctions=[]
    for p in points:
        count=sum(p in (s.a,s.b) for s in segments)+int(any(g.p==p for g in geom_pins))
        if count>=3:junctions.append(p)
    errs=verify(segments,geom_pins,junctions,merge_power=False)
    audit=ROOT/'verification'/name;audit.mkdir(parents=True,exist_ok=True)
    (audit/'geometry.json').write_text(json.dumps({'violations':errs,'segments':len(segments),'pins':len(geom_pins)},indent=2))
    if errs:raise ValueError(name+' geometric verification failed: '+repr(errs[:15]))
    for i,s in enumerate(segments):doc.append(n('wire',n('pts',pt(*s.a),pt(*s.b)),stroke(0),n('uuid',Q(uid(name+'/wire/'+str(i))))))
    for i,p in enumerate(junctions):doc.append(n('junction',n('at',*p),n('diameter',0),n('color',0,0,0,0),n('uuid',Q(uid(name+'/junction/'+str(i))))))
    for i,(net,p) in enumerate(sorted(set(labels))):doc.append(make_label(net,p,name+'/label/'+str(i)))
    # Source connector rails are passive sources. Declare them explicitly.
    powered={p.net for p in geom_pins if any(c['ref']+'.'+q['number']==p.who and q['type']=='pwr' for c in model['components'] for q in c['pins'])}|{net for aa,bb,net in power_ports}
    flagname='SOURCE_PWR_FLAG'
    flag=n('symbol',Q(flagname),n('power',S('global')),n('pin_names',n('offset',0)),n('exclude_from_sim',S('no')),n('in_bom',S('no')),n('on_board',S('no')),prop('Reference','#FLG',hide=True),prop('Value',flagname,hide=True),n('symbol',Q(flagname+'_1_1'),n('pin',S('power_out'),S('line'),n('at',0,0,90),n('length',0),n('hide',S('yes')),n('name',Q('pwr'),effects()),n('number',Q('1'),effects()))))
    library.append(copy.deepcopy(flag));flag[1]=Q('USRP:'+flagname);cache.append(flag)
    for i,net in enumerate(sorted(powered)):
        p=next((s.a for s in segments if s.net==net));reference=f'#FLG{i+1:03}'
        doc.append(n('symbol',n('lib_id',Q('USRP:'+flagname)),n('at',*p,0),n('unit',1),n('in_bom',S('no')),n('on_board',S('no')),n('uuid',Q(uid(name+'/flag/'+net))),prop('Reference',reference,*p,True),prop('Value',flagname,*p,True),n('instances',n('project',Q(name),n('path',Q('/'+rootid),n('reference',Q(reference)),n('unit',1))))))
    doc.append(n('sheet_instances',n('path',Q('/'),n('page',Q('1')))));doc.append(n('embedded_fonts',S('no')))
    sexp.save_file(project/(name+'.kicad_sch'),doc);sexp.save_file(project/'USRP.kicad_sym',library)
    (project/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "USRP") (type "KiCad") (uri "${KIPRJMOD}/USRP.kicad_sym") (options "") (descr "Verified source symbols")))\n')
    (project/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "USRP") (type "KiCad") (uri "${KIPRJMOD}/USRP.pretty") (options "") (descr "Original footprint geometry")))\n')
    (project/(name+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':name+'.kicad_pro','version':3}},indent=2))
    (audit/'source-netlist.json').write_text(json.dumps({'nets':nets,'symbols':smap,'root_uuid':rootid},indent=2))
    print(name,'verified schematic',len(comps),'components',len(segments),'wires')

if __name__=='__main__':
    # A deliberately crossed pair must fail the shared verifier.
    assert verify([Seg('A',(0,1.27),(2.54,1.27)),Seg('B',(1.27,0),(1.27,2.54))],[],[])
    for name in sys.argv[1:] or SOURCES:build(name)
