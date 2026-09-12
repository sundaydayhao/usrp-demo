"""Apply a documented JLC 4-layer starting stack and audit RF return planes.

The analytic impedance is a starting estimate, not an EM or coupon result.
"""
from pathlib import Path
import math,json,sys,copy
import pcbnew as p
from import_legacy_boards import ROOT,SOURCES,vec
from build_legacy_schematics import sexp,n,Q,S
def impedance(w,h=.2104,er=4.4,t=.035):
    u=w/h;tt=t/h
    du=tt/math.pi*math.log(1+4*math.e/(tt*(1/math.tanh(math.sqrt(6.517*u)))**2))
    ur=u+du*(1+1/math.cosh(math.sqrt(er-1)))/2
    aa=1+math.log((ur**4+(ur/52)**2)/(ur**4+.432))/49+math.log(1+(ur/18.1)**3)/18.7
    bb=.564*((er-.9)/(er+3))**.053
    ee=(er+1)/2+(er-1)/2*(1+10/ur)**(-aa*bb)
    ff=6+(2*math.pi-6)*math.exp(-(30.666/ur)**.7528)
    return 60/math.sqrt(ee)*math.log(ff/ur+math.sqrt(1+(2/ur)**2))
def apply(name):
    d=ROOT/'projects'/name;file=d/(name+'.kicad_pcb');b=p.LoadBoard(str(file));fps={f.GetReference():f for f in b.GetFootprints()}
    refs={'BasicRX':['J18','J19'],'BasicTX':['J48','J49'],'LFRX':['J18','J19'],'LFTX':['J48','J49'],'TVRX':[]}[name]
    reports=[];netnames=[]
    for ref in refs:
        net=next(pad.GetNetname() for pad in fps[ref].Pads() if pad.GetNumber()=='1');netnames.append(str(net));tracks=[t for t in b.GetTracks() if t.GetNetname()==net and not isinstance(t,p.PCB_VIA)]
        for t in tracks:
            if t.GetLayer()!=p.F_Cu:raise RuntimeError('RF surface change requires a separate launch design')
            t.SetWidth(p.FromMM(.37))
        pads=[pad for f in b.GetFootprints() for pad in f.Pads() if pad.GetNetname()==net]
        missing=[];sampled=0
        for t in tracks:
            a,c=t.GetStart(),t.GetEnd();steps=max(1,math.ceil(t.GetLength()/2e5))
            for k in range(steps+1):
                xy=p.VECTOR2I(round(a.x+(c.x-a.x)*k/steps),round(a.y+(c.y-a.y)*k/steps));sampled+=1
                okay=any(z.GetLayer()==p.In1_Cu and z.GetNetname()=='/AGND' and z.HitTestFilledArea(p.In1_Cu,xy) for z in b.Zones())
                if not okay:
                    # Through-hole launch antipads include pad copper plus the
                    # original plane's 0.254 mm clearance; use their actual size.
                    near_pad=any(pad.GetAttribute()==p.PAD_ATTRIB_PTH and math.hypot(xy.x-pad.GetPosition().x,xy.y-pad.GetPosition().y)<=max(pad.GetSize().x,pad.GetSize().y)/2+p.FromMM(.254)+1 for pad in pads)
                    missing.append({'xy_mm':[p.ToMM(xy.x),p.ToMM(xy.y)],'inside_launch_region':near_pad})
        reports.append({'connector':ref,'net':str(net),'trace_width_mm':.37,'length_mm':sum(t.GetLength() for t in tracks)/1e6,'reference':'In1.Cu /AGND','sample_count':sampled,'samples_without_reference_copper':missing})
    b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(file),b)
    doc=sexp.load_file(file);setup=next(x for x in doc if isinstance(x,list) and str(x[0])=='setup');setup[:]=[x for x in setup if not(isinstance(x,list) and str(x[0])=='stackup')]
    stack=n('stackup')
    for lname,typ,thick,eps in [('F.Cu','copper',.035,None),('dielectric 1','prepreg',.2104,4.4),('In1.Cu','copper',.0152,None),('dielectric 2','core',1.065,4.6),('In2.Cu','copper',.0152,None),('dielectric 3','prepreg',.2104,4.4),('B.Cu','copper',.035,None)]:
        lay=n('layer',Q(lname),n('type',Q(typ)),n('thickness',thick))
        if eps:lay.extend([n('material',Q('FR4 7628' if typ=='prepreg' else 'FR4')),n('epsilon_r',eps),n('loss_tangent',.02)])
        stack.append(lay)
    stack.extend([n('copper_finish',Q('ENIG')),n('dielectric_constraints',S('yes'))]);setup.insert(1,stack);sexp.save_file(file,doc)
    pro=d/(name+'.kicad_pro');cfg=json.loads(pro.read_text());classes=cfg['net_settings']['classes'];classes[:]=[c for c in classes if c['name']!='RF50_START'];rf=copy.deepcopy(classes[0]);rf.update({'name':'RF50_START','track_width':.37,'clearance':.2});classes.append(rf)
    cfg['net_settings']['netclass_patterns']=[{'netclass':'RF50_START','pattern':net} for net in netnames];pro.write_text(json.dumps(cfg,indent=2))
    (ROOT/'verification'/name/'rf-audit.json').write_text(json.dumps({'stackup':'JLC04161H-7628, outer 1 oz, inner 0.5 oz, nominal 1.6 mm','stack_source':'https://jlcpcb.com/impedance','calculation_source':'https://qucs.sourceforge.net/tech/node75.html','uncoated_microstrip_estimate_ohm':impedance(.37),'mask_and_launch_not_modelled':True,'rf_nets':reports},indent=2))
    print(name,[(r['connector'],len(r['samples_without_reference_copper'])) for r in reports])
if __name__=='__main__':
    for name in sys.argv[1:] or SOURCES:apply(name)
