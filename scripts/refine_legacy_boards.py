"""Documented manufacturing edits after geometric source import.

No global rerouting; preserve the source copper except listed local repairs.
"""
from pathlib import Path
import sys,json,math
import pcbnew as p
from import_legacy_boards import ROOT,SOURCES,vec

def refine(name):
    d=ROOT/'projects'/name;path=d/(name+'.kicad_pcb');b=p.LoadBoard(str(path));changes=[]
    settings=json.loads((d/(name+'.kicad_pro')).read_text())
    settings['board']={'design_settings':{'rules':{'min_clearance':.1775,'min_track_width':.1775,'min_through_hole_diameter':.25,'min_via_annular_width':.15,'min_via_diameter':.55,'min_copper_edge_clearance':.25,'min_silk_text_height':.8,'min_silk_text_thickness':.12,'min_silk_clearance':.1}}}
    settings['net_settings']={'classes':[{'name':'Default','clearance':.1775,'track_width':.254,'via_diameter':.8,'via_drill':.4,'diff_pair_width':.254,'diff_pair_gap':.254,'diff_pair_via_gap':.25,'microvia_diameter':.3,'microvia_drill':.1}],'meta':{'version':4}}
    (d/(name+'.kicad_pro')).write_text(json.dumps(settings,indent=2))
    ds=b.GetDesignSettings();ds.m_MinClearance=p.FromMM(.1775);ds.m_CopperEdgeClearance=p.FromMM(.25)
    def move_joint(old,new,layer=None):
        a,c=vec(*old),vec(*new)
        for t in b.GetTracks():
            if isinstance(t,p.PCB_VIA):
                if layer is None and t.GetPosition()==a:t.SetPosition(c)
            elif layer is None or t.GetLayer()==layer:
                if t.GetStart()==a:t.SetStart(c)
                if t.GetEnd()==a:t.SetEnd(c)
        changes.append({'junction_from_mm':old,'junction_to_mm':new,'layer':layer})
    if name=='LFRX':
        move_joint((54.864,19.558),(54.5592,19.6596))
        # Increase the two local digital breakout clearances from 5 mil to 7 mil.
        for netname,y,newy,xlimit in [('/io_rx_05',37.211,37.2872,8),('/io_rx_13',7.874,7.7978,13)]:
            selected=[t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()==netname and t.GetLayer()==p.In2_Cu and t.GetStart().y==p.FromMM(y) and t.GetEnd().y==p.FromMM(y)]
            points={tuple((p.ToMM(q.x),p.ToMM(q.y))) for t in selected for q in (t.GetStart(),t.GetEnd())}
            for x,yy in points:move_joint((x,yy),(x,newy),p.In2_Cu)
    if name=='TVRX':
        fp=next(f for f in b.GetFootprints() if f.GetReference()=='U2');pad=next(q for q in fp.Pads() if q.GetNumber()=='22')
        pad.SetSize(vec(3.9,3.9));changes.append({'pad':'U2.22','diameter_mm':3.9,'reason':'retain tuner mounting drill while clearing board edge'})
    # Retain all source package outlines/text as assembly documentation.
    # New readable reference text is placed clear of pads and other text.
    for f in b.GetFootprints():
        for g in f.GraphicalItems():
            if g.GetLayer() in (p.F_SilkS,p.B_SilkS):g.SetLayer(p.F_Fab if g.GetLayer()==p.F_SilkS else p.B_Fab)
        f.Value().SetVisible(False)
    for g in b.GetDrawings():
        if g.GetLayer() in (p.F_SilkS,p.B_SilkS):g.SetLayer(p.Dwgs_User)
    occupied={p.F_Cu:[],p.B_Cu:[]}
    for f in b.GetFootprints():
        for pad in f.Pads():
            box=pad.GetBoundingBox();r=[p.ToMM(box.GetX())-.18,p.ToMM(box.GetY())-.18,p.ToMM(box.GetRight())+.18,p.ToMM(box.GetBottom())+.18]
            for side in occupied:
                if pad.IsOnLayer(side):occupied[side].append(r)
    outline=b.GetBoardEdgesBoundingBox();bounds=[p.ToMM(outline.GetX())+.5,p.ToMM(outline.GetY())+.5,p.ToMM(outline.GetRight())-.5,p.ToMM(outline.GetBottom())-.5]
    def intersects(a,c):return a[0]<c[2] and a[2]>c[0] and a[1]<c[3] and a[3]>c[1]
    for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
        if f.GetAttributes()&p.FP_BOARD_ONLY:continue
        field=f.Reference();field.SetVisible(True);field.SetLayer(p.B_SilkS if f.GetLayer()==p.B_Cu else p.F_SilkS);field.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));field.SetMirrored(f.GetLayer()==p.B_Cu);field.SetTextSize(vec(.8,.8));field.SetTextThickness(p.FromMM(.12))
        side=f.GetLayer();bb=field.GetBoundingBox();w=p.ToMM(bb.GetWidth())/2+.12;h=.58;cx=p.ToMM(f.GetPosition().x);cy=p.ToMM(f.GetPosition().y)
        found=None
        for radius in [.8,1.3,1.8,2.5,3.2,4,5,6,8,10,12,16,20]:
            for ang in [-90,90,0,180,-45,45,135,225]:
                x=cx+radius*math.cos(math.radians(ang));y=cy+radius*math.sin(math.radians(ang));r=[x-w,y-h,x+w,y+h]
                if r[0]>=bounds[0] and r[1]>=bounds[1] and r[2]<=bounds[2] and r[3]<=bounds[3] and not any(intersects(r,c) for c in occupied[side]):found=(x,y,r);break
            if found:break
        if not found:raise RuntimeError(name+' cannot place reference '+f.GetReference())
        field.SetPosition(vec(*found[:2]));occupied[side].append(found[2])
    b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(path),b)
    # Synchronize audited footprint libraries after local mechanical edits.
    plugin=p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP)
    for f in b.GetFootprints():
        if f.GetAttributes()&p.FP_BOARD_ONLY:continue
        local=p.FOOTPRINT(f);local.SetPosition(vec(0,0));local.SetPath(p.KIID_PATH());local.Reference().SetText('REF**')
        for pad in local.Pads():pad.SetNetCode(0)
        plugin.FootprintSave(str(d/'USRP.pretty'),local)
    (ROOT/'verification'/name/'local-repairs.json').write_text(json.dumps(changes,indent=2));print(name,'refined',len(changes),'local copper/mechanical repairs')
    # SaveBoard writes its loaded project settings. Apply the new reviewed
    # rule values afterwards, so they are not replaced by the old defaults.
    current=json.loads((d/(name+'.kicad_pro')).read_text())
    current['board']['design_settings']['rules'].update(settings['board']['design_settings']['rules'])
    current['net_settings']=settings['net_settings']
    (d/(name+'.kicad_pro')).write_text(json.dumps(current,indent=2))
if __name__=='__main__':
    for name in sys.argv[1:] or SOURCES:refine(name)
