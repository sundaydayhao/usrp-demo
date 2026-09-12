"""Import original copper, correcting gEDA layer/side/outline metadata.

The native importer ignores Groups and polygons and mirrors already positioned
bottom elements. These corrections are checked against source pad coordinates.
"""
from pathlib import Path
import sys,json,re,shlex,collections
import pcbnew as pcb
import wx
APP=wx.App(False)
from build_legacy_schematics import ROOT,GEDA,SOURCES,uid

def records(text):
    """Read bracket/parenthesis gEDA PCB records including nested bodies."""
    pat=re.compile(r'^\s*(\w+)\s*([\[(])(.*?)[\])]\s*$',re.M)
    out=[];pos=0
    while (m:=pat.search(text,pos)):
        kind,delim,args=m.groups();pos=m.end()
        if kind=='Symbol':
            # Skip stroke-font records, which can contain quote characters.
            j=text.find('\n)',pos);pos=j+2 if j>=0 else pos;continue
        try:params=shlex.split(args,posix=True)
        except ValueError:continue
        body='';rest=pos
        while rest<len(text) and text[rest].isspace():rest+=1
        if rest<len(text) and text[rest]=='(':
            level=1;j=rest+1;quoted=False;escape=False
            while j<len(text) and level:
                c=text[j]
                if escape:escape=False
                elif c=='\\':escape=True
                elif c=='"':quoted=not quoted
                elif not quoted:
                    if c=='(':level+=1
                    elif c==')':level-=1
                j+=1
            body=text[rest+1:j-1];pos=j
        out.append((kind,params,body))
    return out

def vec(x,y):return pcb.VECTOR2I(round(x*1e6),round(y*1e6))
def rawvec(x,y):return vec(float(x)*.000254,float(y)*.000254)
def layer_set(layers):
    result=pcb.LSET()
    for layer in layers:result.AddLayer(layer)
    return result
def inside(p,points):
    x,y=p;hit=False
    for (xa,ya),(xb,yb) in zip(points,points[1:]+points[:1]):
        if (ya>y)!=(yb>y) and x<(xb-xa)*(y-ya)/(yb-ya)+xa:hit=not hit
    return hit

def thermal_layers(flags):
    if flags.startswith('0x'):return {i for i in range(8) if int(flags,16)&(1<<(16+i))}
    match=re.search(r'thermal\(([^)]*)\)',flags)
    if not match:return set()
    result=set()
    for item in match.group(1).split(','):
        nums=[int(x) for x in re.findall(r'\d+',item)]
        if len(nums)==1:result.add(nums[0])
        elif len(nums)==2:result.update(range(nums[0],nums[1]+1))
    return result

def flag_has(flags,name,mask):return bool(int(flags,16)&mask) if flags.startswith('0x') else name in flags

def build(name):
    source=GEDA/(SOURCES[name]+'.pcb');raw=records(source.read_text())
    project=ROOT/'projects'/name;audit=ROOT/'verification'/name
    netdata=json.loads((audit/'source-netlist.json').read_text())
    expected={(r,p):n for n,nodes in netdata['nets'].items() for r,p in nodes}
    b=pcb.LoadBoard(str(source),12)
    namemap=json.loads((audit/'kicad-net-name-map.json').read_text()) if (audit/'kicad-net-name-map.json').exists() else {}
    nets={}
    for net in netdata['nets']:
        mapped=namemap.get(net,net);ni=pcb.NETINFO_ITEM(b,('/' if mapped==net else '')+mapped);b.Add(ni);nets[net]=ni
    netreverse={str(v.GetNetname()):k for k,v in nets.items()}
    fps={f.GetReference():f for f in b.GetFootprints()};thermal=[];padchecks=[]
    # Source pads already have their world-space orientation encoded.
    for kind,args,body in raw:
        if kind!='Element':continue
        ref=args[2];f=fps[ref];ox,oy=map(float,args[4:6])
        entries=[x for x in records(body) if x[0] in ('Pad','Pin')]
        pads=list(f.Pads());used=set()
        for typ,ar,_ in entries:
            pin=ar[-2];hole=flag_has(ar[-1],'hole',8)
            candidates=[(i,p) for i,p in enumerate(pads) if i not in used and p.GetNumber()==pin and (p.GetDrillSize().x>0)==(typ=='Pin')]
            if not candidates:raise ValueError(f'{name} {ref}.{pin}: no imported pad match')
            i,p=candidates[0];used.add(i)
            if typ=='Pad':px=(float(ar[0])+float(ar[2]))/2;py=(float(ar[1])+float(ar[3]))/2
            else:px,py=map(float,ar[:2])
            p.SetPosition(rawvec(ox+px,oy+py))
            p.SetLocalClearance(0)
            p.SetLocalSolderMaskMargin(pcb.FromMM(.05))
            if typ=='Pad':
                bottom=flag_has(args[0],'onsolder',128) or flag_has(ar[-1],'onsolder',128)
                p.SetLayerSet(layer_set([pcb.B_Cu,pcb.B_Mask,pcb.B_Paste] if bottom else [pcb.F_Cu,pcb.F_Mask,pcb.F_Paste]))
            if hole:
                p.SetNumber('');p.SetNetCode(0);p.SetAttribute(pcb.PAD_ATTRIB_NPTH);p.SetSize(p.GetDrillSize())
            else:p.SetNet(nets[expected[ref,pin]]) if (ref,pin) in expected else p.SetNetCode(0)
            padchecks.append({'reference':ref,'pin':pin,'source_mm':[(ox+px)*.000254,(oy+py)*.000254],
                'actual_mm':[pcb.ToMM(p.GetPosition().x),pcb.ToMM(p.GetPosition().y)]})
            layers=thermal_layers(ar[-1])
            if typ=='Pad' and not flag_has(ar[-1],'clearline',0x200):layers.add(0 if bottom else 3)
            if layers and not hole:thermal.append({'xy':((ox+px)*.000254,(oy+py)*.000254),'layers':layers,'net':expected.get((ref,pin))})
        # Re-imported bottom silkscreen was reflected with the pads.
        if flag_has(args[0],'onsolder',128):
            for g in f.GraphicalItems():
                if hasattr(g,'GetStart') and hasattr(g,'GetEnd'):
                    st,en=g.GetStart(),g.GetEnd();g.SetStart(vec(pcb.ToMM(st.x),2*oy*.000254-pcb.ToMM(st.y)));g.SetEnd(vec(pcb.ToMM(en.x),2*oy*.000254-pcb.ToMM(en.y)))
        f.SetPath(pcb.KIID_PATH('/'+netdata['root_uuid']+'/'+netdata['symbols'][ref]))
        f.SetFPID(pcb.LIB_ID('USRP',ref));f.SetSheetfile(name+'.kicad_sch');f.SetSheetname('/')
        f.Reference().SetTextSize(vec(.8,.8));f.Reference().SetTextThickness(pcb.FromMM(.12));f.Value().SetVisible(False)
        if f.GetLayer()==pcb.B_Cu:f.Reference().SetMirrored(True)
    # KiCad uses a sequential copper mapping; gEDA's Groups says 1=solder,
    # 4=component, 2/3=inner layers. Original unused layers contain no copper.
    mapping={1:pcb.B_Cu,2:pcb.In1_Cu,3:pcb.In2_Cu,4:pcb.F_Cu}
    original_tracks=list(b.GetTracks())
    for t in original_tracks:
        if not isinstance(t,pcb.PCB_VIA):b.Remove(t)
        else:t.SetNetCode(0)
    source_tracks={}
    def trackkey(ax,ay,bx,by):return tuple(sorted(((round(ax),round(ay)),(round(bx),round(by)))))
    for k,ar,bo in raw:
        if k=='Layer' and int(ar[0]) in mapping:
            for typ,fields,_ in records(bo):
                if typ=='Line':
                    if fields[:2]==fields[2:4]:continue
                    t=pcb.PCB_TRACK(b);t.SetStart(rawvec(*fields[:2]));t.SetEnd(rawvec(*fields[2:4]));t.SetWidth(pcb.FromMM(float(fields[4])*.000254));t.SetLayer(mapping[int(ar[0])]);b.Add(t)
                elif typ=='Arc':raise ValueError('Source arc requires exact conversion')
    for kind,args,body in raw:
        if kind!='Via' or not flag_has(args[-1],'hole',8):continue
        xy=rawvec(*args[:2]);via=next((t for t in b.GetTracks() if isinstance(t,pcb.PCB_VIA) and t.GetPosition()==xy),None)
        if via:b.Remove(via)
        fp=pcb.FOOTPRINT(b);fp.SetReference('H'+str(1+sum(f.GetReference().startswith('H') for f in b.GetFootprints())));fp.SetValue('NPTH');fp.SetPosition(xy);fp.SetAttributes(pcb.FP_BOARD_ONLY|pcb.FP_EXCLUDE_FROM_BOM|pcb.FP_EXCLUDE_FROM_POS_FILES)
        hole=pcb.PAD(fp);hole.SetNumber('');hole.SetAttribute(pcb.PAD_ATTRIB_NPTH);hole.SetShape(pcb.PAD_SHAPE_CIRCLE);hole.SetDrillSize(rawvec(args[5],args[5]));hole.SetSize(hole.GetDrillSize());hole.SetLayerSet(pcb.LSET.AllCuMask());hole.SetPosition(xy);fp.Add(hole);fp.Reference().SetVisible(False);fp.Value().SetVisible(False);b.Add(fp)
    b.SetCopperLayerCount(4)
    # Discard importer polygon graphics; restore actual filled copper zones.
    for g in list(b.GetDrawings()):
        if pcb.IsCopperLayer(g.GetLayer()):b.Remove(g)
    header=next(ar for k,ar,bo in raw if k=='PCB');bw,bh=float(header[1])*.000254,float(header[2])*.000254
    for aa,bb in [((0,0),(bw,0)),((bw,0),(bw,bh)),((bw,bh),(0,bh)),((0,bh),(0,0))]:
        shape=pcb.PCB_SHAPE();shape.SetShape(pcb.SHAPE_T_SEGMENT);shape.SetLayer(pcb.Edge_Cuts);shape.SetStart(vec(*aa));shape.SetEnd(vec(*bb));shape.SetWidth(pcb.FromMM(.05));b.Add(shape)
    b.BuildConnectivity();b.GetConnectivity().PropagateNets()
    for kind,args,body in raw:
        if kind=='Via' and not flag_has(args[-1],'hole',8) and thermal_layers(args[-1]):
            xy=rawvec(*args[:2]);t=next((t for t in b.GetTracks() if isinstance(t,pcb.PCB_VIA) and t.GetPosition()==xy),None)
            if t and t.GetNetCode():thermal.append({'xy':(pcb.ToMM(xy.x),pcb.ToMM(xy.y)),'layers':thermal_layers(args[-1]),'net':netreverse[str(t.GetNetname())]})
    zones=[]
    for kind,args,body in raw:
        if kind!='Layer':continue
        layernum=int(args[0]);layer={1:pcb.B_Cu,2:pcb.In1_Cu,3:pcb.In2_Cu,4:pcb.F_Cu}.get(layernum)
        for typ,ar,polybody in records(body):
            if typ!='Polygon':continue
            if layer is None:raise ValueError('Polygon on unused layer')
            points=[(float(x)*.000254,float(y)*.000254) for x,y in re.findall(r'\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\]',polybody)]
            candidates={t['net'] for t in thermal if inside(t['xy'],points) and layernum-1 in t['layers'] and t['net']}
            zones.append({'layer':layernum,'candidates':candidates,'points':points})
    # Original polygons overlap to form contiguous plane shapes. Propagate
    # net identity only through positive-area intersections on the same layer.
    def overlap(aa,bb):
        return all(min(max(p[k] for p in aa),max(p[k] for p in bb))-max(min(p[k] for p in aa),min(p[k] for p in bb))>1e-6 for k in (0,1))
    for repeat in range(len(zones)):
        for za in zones:
            for zb in zones:
                if za['layer']==zb['layer'] and overlap(za['points'],zb['points']):za['candidates']|=zb['candidates']
    for idx,zd in enumerate(zones):
        candidates=zd.pop('candidates')
        if len(candidates)!=1:raise ValueError(f'{name} ambiguous original copper polygon L{zd["layer"]} {idx}: {candidates}')
        net=next(iter(candidates));zd['net']=net
        z=pcb.ZONE(b);z.SetLayer(mapping[zd['layer']]);z.SetNet(nets[net]);z.SetAssignedPriority(idx);z.SetLocalClearance(pcb.FromMM(.254));z.SetPadConnection(pcb.ZONE_CONNECTION_FULL);z.SetMinThickness(pcb.FromMM(.15));z.SetThermalReliefGap(pcb.FromMM(.25));z.SetThermalReliefSpokeWidth(pcb.FromMM(.25));z.Outline().NewOutline()
        for x,y in zd['points']:z.Outline().Append(round(x*1e6),round(y*1e6))
        b.Add(z)
    # Local footprint libraries retain the audited physical pin coordinates.
    fpdir=project/'USRP.pretty';fpdir.mkdir(exist_ok=True)
    plugin=pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.KICAD_SEXP)
    for f in b.GetFootprints():
        if f.GetReference().startswith('H'):continue
        local=pcb.FOOTPRINT(f);local.SetPosition(vec(0,0));local.SetPath(pcb.KIID_PATH());local.Reference().SetText('REF**')
        for p in local.Pads():p.SetNetCode(0)
        plugin.FootprintSave(str(fpdir),local)
    print(name,'filling restored zones',flush=True)
    b.BuildConnectivity();pcb.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();b.GetConnectivity().PropagateNets()
    output=project/(name+'.kicad_pcb');pcb.SaveBoard(str(output),b)
    (audit/'pcb-import-audit.json').write_text(json.dumps({'source':str(source.relative_to(ROOT)), 'pad_coordinates':padchecks,'zones':zones,'copper_layers':4,'size_mm':[bw,bh], 'footprints':len(fps),'tracks_vias':len(b.GetTracks())},indent=2))
    print(name,len(fps),'footprints',len(b.GetTracks()),'tracks/vias',len(zones),'restored copper zones')

if __name__=='__main__':
    for name in sys.argv[1:] or SOURCES:build(name)
