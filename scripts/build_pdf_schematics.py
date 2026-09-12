"""Build editable KiCad sheets from audited PDF vectors and endpoint graphs."""
from pathlib import Path
import json, re, sys, copy, math, collections
from build_legacy_schematics import n,Q,S,uid,prop,stroke,pt,poly,effects,sexp,Seg,Pin,verify,ktype
from recover_pdf_nets import display,box
from geda_model import read_objects,attributes,on_segment
ROOT=Path(__file__).resolve().parents[1]
IC_VALUES={
 'WBX':{'U201':'ADF4350BCPZ','U401':'ADF4350BCPZ','U202':'24LC024/SN','U403':'24LC024/SN','U302':'HMC472LP4E','U304':'ADA4937-2YCPZ','U306':'ADP3336ARMZ','U308':'ADP3336ARMZ','U307':'ADL5387ACPZ','U313':'MGA-82563','U501':'ADL5386ACPZ','U502':'GVA-84+','U503':'ADP3336ARMZ','U505':'ADP3336ARMZ'},
 'TVRX2':{'U100':'TDA18272HN','U140':'TDA18272HN','U80':'XC2C32A-6QFG32C','U1':'24LC024/SN','U2':'LT1085CM-3.3','U3':'MIC5247-1.8YM5'}}
SYMS={'ADF4350BCPZ':['adf4350-ANLG','adf4350-DIG','adf4350-PWR'],'ADL5387ACPZ':['adl5387-MIX','adl5387-PWR'],'ADL5386ACPZ':['adl5386-MIX','adl5386-DET','adl5386-PWR'],'ADP3336ARMZ':['adp3336'],'ADA4937-2YCPZ':['ada493x-2-A','ada493x-2-B'],'HMC472LP4E':['hmc472lp4-RF','hmc472lp4-PWR'],'MGA-82563':['mga82563']}
def value_of(name,p,page):
    ref=p['ref']
    if name=='WBX' and ref in ['C101','C102']:return 'NONE'
    if name=='WBX' and ref in ['C103','C104']:return '1000pF'
    if ref in IC_VALUES[name]:return IC_VALUES[name][ref]
    if p['kind']=='mounting_hole':return 'M2.5 GND'
    if p['kind']=='test_point':return 'TestPoint'
    if ref.startswith('J'):
        if len(p['pins'])==64:return 'USRP1 PMC-64'
        if len(p['pins'])==5:return 'SMA 50 ohm'
        if len(p['pins'])==41:return 'QTE-020'
        return 'Header '+str(len(p['pins']))
    if ref.startswith('T'):return 'TC1-1-13M+'
    raw=p['rawtext'].replace(ref,'').replace('\u2212','-').strip()
    if p['kind']=='inductor' and (not raw or 'FB-' in raw):return 'FB 600R@100MHz'
    return raw or 'UNSPECIFIED'
def pin_types(value):
    ans={}
    for basename in SYMS.get(value,[]):
        files=list((ROOT/'tmp/source-audit/geda').rglob(basename+'.sym'))
        if not files:continue
        for obj in read_objects(files[0]):
            if obj['kind']=='P':
                at=attributes(obj['attrs']);ans[at['pinnumber'][0]]=ktype(at.get('pintype',['pas'])[0])
    if value=='24LC024/SN':ans={'1':'input','2':'input','3':'input','4':'power_in','5':'bidirectional','6':'input','7':'input','8':'power_in'}
    # Internally paralleled output terminals describe one regulator driver.
    if value=='ADP3336ARMZ':ans.update({'1':'power_out','2':'passive','3':'passive'})
    if value=='LT1085CM-3.3':ans={'1':'power_in','2':'power_out','3':'power_in','4':'passive'}
    if value.startswith('MIC5247'):ans={'1':'power_in','2':'power_in','3':'input','4':'passive','5':'power_out'}
    if value.startswith('XC2C32A'):
        ans={str(i):'bidirectional' for i in range(1,34)}
        ans.update({str(i):'power_in' for i in [4,11,12,20,21,26,27,33]})
        ans.update({str(i):'input' for i in [6,14,15,16,17,18,19,22]});ans['25']='output';ans['32']='output'
    if value=='TDA18272HN':
        ans={str(i):'passive' for i in range(1,42)}
        ans.update({str(i):'power_in' for i in [1,7,10,16,18,26,27,31,34,35,37,38,41]})
        ans.update({str(i):'input' for i in [2,6,9,11,14,15,28]});ans['12']='bidirectional'
        ans.update({str(i):'output' for i in [4,8,13,20,21,22,23,24,25,29,30]})
        ans.update({str(i):'no_connect' for i in [3,5,39]})
    if value=='GVA-84+':ans={'1':'input','2':'power_in','3':'passive','4':'power_in'}
    return ans
def label(net,p,key):
    return n('global_label',Q(net),n('shape',S('bidirectional')),n('at',*p,0),effects(.9,justify='left'),n('uuid',Q(uid(key))),prop('Intersheetrefs','${INTERSHEET_REFS}',*p,True))
def build(name):
    raw=json.loads((ROOT/'verification'/name/'pdf-vector-extraction.json').read_text());graphs=json.loads((ROOT/'verification'/name/'pdf-net-recovery.json').read_text())
    for graph in graphs:
        assert not graph['conflicts']
        assert all(x['label']=='AUX_DAC_A' and x['reason']=='No wire within 8 pt' for x in graph['label_issues'])
    directory=ROOT/'projects'/name;directory.mkdir(exist_ok=True,parents=True)
    rootid=uid(name+'/root');library=n('kicad_symbol_lib',n('version',20241209),n('generator',Q('kicad_symbol_editor')))
    units=collections.defaultdict(list);pages=[];all_expected=collections.defaultdict(set);metadata={}
    for i,(page,g) in enumerate(zip(raw,graphs)):
        linewidth=collections.Counter(round(d['width'],5) for d in page['drawings'] if d['width']).most_common(1)[0][0];scale=1.27/(linewidth*10)
        pp=[pin['at'] for pin in g['pins']];x0=min(p[0] for p in pp);y0=min(p[1] for p in pp)
        def world(p,snap=True):
            q=((p[0]-x0)*scale+25.4,(p[1]-y0)*scale+25.4)
            return tuple(round(round(v/1.27)*1.27,3) if snap else round(v,4) for v in q)
        pdata={'index':i,'raw':page,'graph':g,'scale':scale,'x0':x0,'y0':y0,'sheet_uuid':uid(name+'/sheet/'+str(i)),'file':name+'.kicad_sch' if i==0 else f'{name}_p{i+1}.kicad_sch','segments':[],'pins':[],'labels':[],'instances':[],'ncs':[],'extras':[]}
        for p in page['parts']:
            p=copy.deepcopy(p);p['page_index']=i;p['value']=value_of(name,p,page);p['unit']=len(units[p['ref']])+1
            p['pos']=world(display(p['pins'][0]['xy'],page));p['type_map']=pin_types(p['value']);pinmap={(x['ref'],x['number'],x['seq']):x for x in g['pins']}
            singleton={(x['ref'],x['number'],x['seq']) for x in g['unnamed_singletons']}
            for pin in p['pins']:
                k=(p['ref'],pin['number'],p['seq']);gp=pinmap[k];pin['at']=world(gp['at']);pin['net']=None if k in singleton else gp['net'];pin['type']=p['type_map'].get(pin['number'],'passive')
                # Mini-Circuits AT224-1A: source dotted primary terminal 5 is
                # physical terminal 6. Keep the source endpoint graph immutable.
                if p['value']=='TC1-1-13M+' and pin['number']=='5':pin['number']='6'
                if 'inner' in pin:pin['inside']=world(display(pin['inner'],page))
            if p['kind'] in ['capacitor','resistor','inductor']:
                for j,pin in enumerate(p['pins']):
                    other=p['pins'][1-j]['at'];pin['inside']=tuple(round(pin['at'][k]+(other[k]-pin['at'][k])*2/9,3) for k in (0,1))
                    pin['inside']=tuple(round(round(v/1.27)*1.27,3) for v in pin['inside'])
            units[p['ref']].append(p);pdata['instances'].append(p)
            for pin in p['pins']:
                if pin['net']:
                    pdata['pins'].append(Pin(pin['net'],pin['at'],p['ref']+'.'+pin['number']));all_expected[pin['net']].add((p['ref'],pin['number']))
                else:pdata['ncs'].append(pin['at'])
        powerbars={lab['seq']-1 for lab in g['labels'] if lab['source_power']}
        for s in g['wires']:
            if s['seq'] in powerbars:continue
            aa,bb=world(s['a']),world(s['b'])
            if aa!=bb:pdata['segments'].append(Seg(s['net'],aa,bb))
        for lab in g['labels']:
            if lab['source_power']:
                bar=next((s for s in g['wires'] if s['seq']==lab['seq']-1),None)
                if bar:
                    pdata['labels'].append((lab['name'],world(tuple((bar['a'][k]+bar['b'][k])/2 for k in (0,1)))));continue
            pdata['labels'].append((lab['name'],world(lab['at'])))
        pages.append(pdata)
    # Explicitly restore power pins printed as implicit gEDA attributes.
    implicit={'WBX':{'U202':{'4':'DGND_RX','8':'DVDD_RX'},'U403':{'4':'DGND_TX','8':'DVDD_TX'}},'TVRX2':{'U1':{'4':'DGND','8':'DVDD'}}}[name]
    if name=='TVRX2':implicit['U80']={'13':None} # Unused I/O omitted from the source symbol, per AMD DS310.
    if name=='WBX':
        for ref,parts in units.items():
            if parts[0]['value']=='TC1-1-13M+':implicit[ref]={'2':None}
    for ref,ports in implicit.items():
        pd=pages[units[ref][-1]['page_index']];idx=len(pd['extras']);pos=(25.4+idx*40.64,355.6)
        p={'ref':ref,'value':units[ref][0]['value'],'unit':len(units[ref])+1,'kind':'extra','pos':pos,'page_index':pd['index'],'pins':[],'rawtext':'Explicit source implicit pins'}
        for j,(num,net) in enumerate(ports.items()):
            at=(pos[0],round(pos[1]+j*5.08,3));inside=(round(at[0]+5.08,3),at[1]);p['pins'].append({'number':num,'name':net or 'IO_UNUSED','at':at,'inside':inside,'net':net,'type':'power_in' if net else 'bidirectional'})
            if net:
                end=(round(at[0]-5.08,3),at[1]);pd['segments'].append(Seg(net,end,at));pd['labels'].append((net,end));pd['pins'].append(Pin(net,at,ref+'.'+num));all_expected[net].add((ref,num))
            else:pd['ncs'].append(at)
        units[ref].append(p);pd['extras'].append(p);pd['instances'].append(p)
    # All pins at identical points are electrically connected, including test points.
    symbols={};root=n('kicad_sch')
    for ref,parts in units.items():
        value=parts[0]['value'];symname=ref;definition=n('symbol',Q(symname),n('pin_names',n('offset',.4)),n('exclude_from_sim',S('no')),n('in_bom',S('yes')),n('on_board',S('yes')),prop('Reference',re.sub(r'\d+$','',ref)),prop('Value',value),prop('Footprint','USRP:'+ref,hide=True))
        if parts[0]['kind'] in ['resistor','capacitor','inductor']:definition.insert(2,n('pin_numbers',S('hide')))
        allnums=[]
        for p in parts:
            pd=pages[p['page_index']];origin=p['pos'];page=pd['raw'];sc=pd['scale']
            def lraw(rawxy):
                xx,yy=display(rawxy,page);return (round((xx-pd['x0'])*sc+25.4-origin[0],4),round(origin[1]-((yy-pd['y0'])*sc+25.4),4))
            group=n('symbol',Q(f'{symname}_{p["unit"]}_1'))
            if p['kind']=='extra':group.append(poly([(5.08,2.54),(27.94,2.54),(27.94,-7.62),(5.08,-7.62),(5.08,2.54)]))
            elif p['kind'] in ['resistor','capacitor','inductor']:
                aa,bb=[pin['inside'] for pin in p['pins']];dd=math.dist(aa,bb);ux=(bb[0]-aa[0])/dd;uy=(bb[1]-aa[1])/dd
                def along(t,z=0):return (round(aa[0]+ux*t-uy*z-origin[0],4),round(origin[1]-(aa[1]+uy*t+ux*z),4))
                if p['kind']=='resistor':group.append(poly([along(0),*[along(dd*k/8,(-1 if k%2 else 1)*.635) for k in range(1,8)],along(dd)]))
                elif p['kind']=='capacitor':
                    lo=dd/2-.508;hi=dd/2+.508
                    group.extend([poly([along(0),along(lo)]),poly([along(hi),along(dd)]),poly([along(lo,-2.032),along(lo,2.032)]),poly([along(hi,-2.032),along(hi,2.032)])])
                    if p.get('polar'):group.extend([poly([along(lo-1.27,2.032),along(lo-.254,2.032)]),poly([along(lo-.762,1.524),along(lo-.762,2.54)])])
                else:
                    ps=[along(dd*k/64,-.7*math.sin(math.pi*4*k/64)) for k in range(65)];group.append(poly(ps))
            elif p['ref'].startswith('J') and len(p['pins'])==5:
                aa=p['pins'][0]['inside'];center=(round(aa[0]-origin[0],4),round(origin[1]-aa[1],4));group.append(n('circle',n('center',*center),n('radius',1.27),stroke(),n('fill',n('type',S('none')))))
            else:
                selected=[d for d in page['drawings'] if d['seq'] in p['drawing_sequences']]
                exclude={pin.get('line_seq') for pin in p['pins']}
                if p['kind'] in ['capacitor','resistor','inductor']:exclude.update(d['seq'] for d in selected[:2])
                if p['kind'] in ['mounting_hole','test_point']:exclude.add(selected[0]['seq'])
                for dd in selected:
                    if dd['seq'] in exclude:continue
                    for item in dd['items']:
                        if item[0]=='l':group.append(poly([lraw(item[1]),lraw(item[2])]))
                        elif item[0]=='c':
                            ps=[]
                            for k in range(13):
                                t=k/12;ps.append(lraw([sum(a*item[j+1][axis] for j,a in enumerate([(1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3])) for axis in (0,1)]))
                            group.append(poly(ps))
            if p['value']=='TC1-1-13M+' and p['kind']!='extra':
                for pin in p['pins']:
                    if pin['number'] in ['1','6']:
                        xx,yy=pin['inside'];cx=(xx-origin[0]);cy=(origin[1]-yy)
                        group.append(n('circle',n('center',round(cx+.8 if pin['number']=='6' else cx-.8,3),round(cy+.8,3)),n('radius',.35),stroke(.1),n('fill',n('type',S('outline')))))
            for pin in p['pins']:
                at,inn=pin['at'],pin['inside'];dx=round(inn[0]-at[0],3);dy=round(inn[1]-at[1],3);angle=0 if dx>0 else 180 if dx<0 else 270 if dy>0 else 90
                group.append(n('pin',S(pin['type']),S('line'),n('at',round(at[0]-origin[0],3),round(origin[1]-at[1],3),angle),n('length',round(math.hypot(dx,dy),3)),n('name',Q(pin.get('name','~') or '~'),effects(.75)),n('number',Q(pin['number']),effects(.7))))
                allnums.append(pin['number'])
            definition.append(group)
        assert len(allnums)==len(set(allnums)),(name,ref,allnums)
        metadata[ref]={'value':value,'pins':allnums,'symbol_uuid':uid(name+'/'+ref+'/1'),'sheet_path':'/'+rootid+('' if parts[0]['page_index']==0 else '/'+pages[parts[0]['page_index']]['sheet_uuid']),'source_pages':sorted({p['page_index']+1 for p in parts})}
        library.append(definition);symbols[ref]=definition
    # Hidden source declarations are separate from device outputs.
    powernets={pin['net'] for ps in units.values() for p in ps for pin in p['pins'] if pin['type']=='power_in' and pin['net']}
    outnets={pin['net'] for ps in units.values() for p in ps for pin in p['pins'] if pin['type']=='power_out' and pin['net']}
    flagname='SOURCE_PWR_FLAG';flag=n('symbol',Q(flagname),n('power',S('global')),n('pin_names',n('offset',0)),n('exclude_from_sim',S('no')),n('in_bom',S('no')),n('on_board',S('no')),prop('Reference','#FLG',hide=True),prop('Value',flagname,hide=True),n('symbol',Q(flagname+'_1_1'),n('pin',S('power_out'),S('line'),n('at',0,0,90),n('length',0),n('hide',S('yes')),n('name',Q('pwr'),effects()),n('number',Q('1'),effects()))));library.append(flag)
    flags_done=set()
    for pd in pages:
        i=pd['index'];doc=n('kicad_sch',n('version',20250114),n('generator',Q('eeschema')),n('generator_version',Q('10.0')),n('uuid',Q(rootid if i==0 else uid(name+'/document/'+str(i)))),n('paper',Q('A2')),n('title_block',n('title',Q(f'{name} / source sheet {i+1}')),n('date',Q('2026-09-12')),n('rev',Q('R0')),n('company',Q('Reconstructed from Ettus Research PDF')),n('comment',1,Q('See design notes for source corrections, sourcing and RF constraints.'))))
        cache=n('lib_symbols')
        for d in library[3:]:
            if isinstance(d,list) and str(d[0])=='symbol':
                cp=copy.deepcopy(d);cp[1]=Q('USRP:'+str(cp[1]));cache.append(cp)
        doc.append(cache);path='/'+rootid+('' if i==0 else '/'+pd['sheet_uuid'])
        for p in pd['instances']:
            ref=p['ref'];pos=p['pos'];unit=p['unit'];value=p['value']
            if p['kind']=='extra':rp=(pos[0]+16.51,pos[1]-5.08);vp=(rp[0],rp[1]+1.65)
            else:
                bb=box(p['text_bbox'],pd['raw']);rp=(round(((bb[0]+bb[2])/2-pd['x0'])*pd['scale']+25.4,3),round(((bb[1]+bb[3])/2-pd['y0'])*pd['scale']+25.4,3))
                vp=(rp[0],round(rp[1]+1.65,3))
                # Use the separately printed value's location when available.
                ws=[w for w in pd['raw']['words'] if w['seq']==p['seq'] and w['text']!=ref and re.match(r'^(?:NONE|None|\d)',w['text'])]
                if p['kind'] in ['resistor','capacitor','inductor'] and ws:
                    vv=box(ws[0]['bbox'],pd['raw']);vp=(round(((vv[0]+vv[2])/2-pd['x0'])*pd['scale']+25.4,3),round(((vv[1]+vv[3])/2-pd['y0'])*pd['scale']+25.4,3))
            doc.append(n('symbol',n('lib_id',Q('USRP:'+ref)),n('at',*pos,0),n('unit',unit),n('exclude_from_sim',S('no')),n('in_bom',S('yes')),n('on_board',S('yes')),n('dnp',S('yes' if value.lower()=='none' else 'no')),n('uuid',Q(uid(name+'/'+ref+'/'+str(unit)))),prop('Reference',ref,*rp),prop('Value',value,*vp),prop('Footprint','USRP:'+ref,*pos,True),prop('Source',f'{name.lower()}.pdf page {i+1}',*pos,True),n('instances',n('project',Q(name),n('path',Q(path),n('reference',Q(ref)),n('unit',unit))))))
        segments=pd['segments'];pins=pd['pins'];bridges=[]
        # gschem permits crossing wires without a junction. Use two labelled
        # stubs at those few crossings so KiCad connectivity stays unambiguous.
        while True:
            hit=None
            for aa in segments:
                for bb in segments:
                    if aa.net==bb.net or (aa.a[1]==aa.b[1])==(bb.a[1]==bb.b[1]):continue
                    h,v=(aa,bb) if aa.a[1]==aa.b[1] else (bb,aa);xy=(v.a[0],h.a[1])
                    if on_segment(xy,h.a,h.b) and on_segment(xy,v.a,v.b):hit=(h,v,xy);break
                if hit:break
            if not hit:break
            h,v,xy=hit;candidate=next((s for s in [v,h] if min(math.dist(s.a,xy),math.dist(s.b,xy))>=2.54-1e-6),None)
            if candidate is None:raise ValueError(('Crossing too close to terminal',hit))
            s=candidate;aa,bb=sorted([s.a,s.b]);axis=0 if aa[1]==bb[1] else 1
            left=list(xy);right=list(xy);left[axis]=round(left[axis]-1.27,3);right[axis]=round(right[axis]+1.27,3);left,right=tuple(left),tuple(right)
            segments.remove(s);segments.extend([Seg(s.net,aa,left),Seg(s.net,right,bb)]);pd['labels'].extend([(s.net,left),(s.net,right)]);bridges.append({'net':s.net,'crossing':xy})
        points={p for s in segments for p in (s.a,s.b)}|{p.p for p in pins};split=set()
        for s in segments:
            pp=sorted(p for p in points if on_segment(p,s.a,s.b))
            for aa,bb in zip(pp,pp[1:]):
                if aa!=bb:split.add((s.net,aa,bb))
        segments=[Seg(*s) for s in sorted(split)]
        degree=collections.Counter(p for s in segments for p in (s.a,s.b));pinpos=collections.Counter(p.p for p in pins)
        junctions=[p for p in points if degree[p]+bool(pinpos[p])>=3]
        errors=verify(segments,pins,junctions,merge_power=False)
        (ROOT/'verification'/name/f'p{i+1}-geometry.json').write_text(json.dumps({'violations':errors,'segments':len(segments),'pins':len(pins),'labelled_crossovers':bridges},indent=2))
        if errors:raise ValueError(f'{name} p{i+1}: '+repr(errors[:20]))
        for j,s in enumerate(segments):doc.append(n('wire',n('pts',pt(*s.a),pt(*s.b)),stroke(0),n('uuid',Q(uid(name+f'/p{i+1}/wire/{j}')))))
        for j,p in enumerate(junctions):doc.append(n('junction',n('at',*p),n('diameter',0),n('color',0,0,0,0),n('uuid',Q(uid(name+f'/p{i+1}/junction/{j}')))))
        from geda_model import DSU
        ds=DSU()
        for ss in segments:ds.join(ss.a,ss.b)
        opens=collections.defaultdict(list)
        for s in segments:
            for p in (s.a,s.b):
                if degree[p]==1 and p not in pinpos:opens[(s.net,ds.find(p))].append(p)
        labels=set()
        for net,p in pd['labels']:
            opts=opens[(net,ds.find(p))]
            if opts:p=min(opts,key=lambda q:math.dist(p,q))
            labels.add((net,p))
        named={x[0] for x in labels}
        labels|={(s.net,p) for s in segments for p in (s.a,s.b) if degree[p]==1 and p not in pinpos and s.net in named}
        for j,(net,p) in enumerate(sorted(labels)):doc.append(label(net,p,name+f'/p{i+1}/label/{j}'))
        for j,p in enumerate(sorted(set(pd['ncs']))):doc.append(n('no_connect',n('at',*p),n('uuid',Q(uid(name+f'/p{i+1}/nc/{j}')))))
        for net in sorted(powernets-outnets-flags_done):
            pin=next((x for x in pins if x.net==net),None)
            if pin:
                reference='#FLG'+str(len(flags_done)+1);flags_done.add(net);at=pin.p
                doc.append(n('symbol',n('lib_id',Q('USRP:'+flagname)),n('at',*at,0),n('unit',1),n('in_bom',S('no')),n('on_board',S('no')),n('uuid',Q(uid(name+'/flag/'+net))),prop('Reference',reference,*at,True),prop('Value',flagname,*at,True),n('instances',n('project',Q(name),n('path',Q(path),n('reference',Q(reference)),n('unit',1))))))
        if i==0:
            for j,child in enumerate(pages[1:]):
                doc.append(n('sheet',n('at',469.9,round(38.1+j*27.94,3)),n('size',91.44,17.78),stroke(.15),n('fill',n('color',0,0,0,0)),n('uuid',Q(child['sheet_uuid'])),prop('Sheetname',f'Source_page_{j+2}',469.9,round(35.56+j*27.94,3)),prop('Sheetfile',child['file'],469.9,round(58.42+j*27.94,3)),n('instances',n('project',Q(name),n('path',Q('/'+rootid),n('page',Q(str(j+2))))))))
            doc.append(n('sheet_instances',n('path',Q('/'),n('page',Q('1')))))
        doc.append(n('embedded_fonts',S('no')));sexp.save_file(directory/pd['file'],doc)
        print(name,'page',i+1,'geometry verified',len(segments),'segments')
    sexp.save_file(directory/'USRP.kicad_sym',library)
    (directory/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "USRP") (type "KiCad") (uri "${KIPRJMOD}/USRP.kicad_sym") (options "") (descr "PDF-reconstructed components")))\n')
    (directory/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "USRP") (type "KiCad") (uri "${KIPRJMOD}/USRP.pretty") (options "") (descr "Project-local footprints")))\n')
    pro=directory/(name+'.kicad_pro')
    if not pro.exists():pro.write_text(json.dumps({'meta':{'filename':pro.name,'version':3}},indent=2))
    (ROOT/'verification'/name/'reconstructed-netlist.json').write_text(json.dumps({'nets':{k:sorted(v) for k,v in all_expected.items()},'components':metadata,'root_uuid':rootid},indent=2))
if __name__=='__main__':
    for name in sys.argv[1:] or ['WBX','TVRX2']:build(name)
