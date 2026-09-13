"""Synchronize part choices and a reviewable sourcing BOM into the projects.

Blank MPN/LCSC fields are deliberate: no fabricated orderable part numbers.
"""
from pathlib import Path
import sys,json,csv,collections,re
from build_legacy_schematics import sexp,n,Q,prop
import pcbnew as pcb
from component_policy import update_row, EEPROM_SOURCE
ROOT=Path(__file__).resolve().parents[1]
LEGACY_VALUES={'BasicRX':{'U1':'AT24C02','T1':'ADT1-1WT+','T2':'ADT1-1WT+'},'BasicTX':{'U52':'AT24C02','T50':'ADT1-1WT+','T51':'ADT1-1WT+'},'LFRX':{'U1':'AT24C02','U2':'AD8132ARZ','U3':'AD8132ARZ'},'LFTX':{'U52':'AT24C02','U1':'AD8047ARZ','U2':'AD8047ARZ','U3':'LT3462ES6','FB1':'600R@100MHz','FB2':'600R@100MHz'},'TVRX':{'U1':'AT24C02','U4':'AD8602ARZ','U3':'LM2940IMP-5.0','Q1':'NDS355AN','Q2':'NDS355AN'}}
LEGACY_VALUES.update({'WBX':{'U202':'AT24C02','U403':'AT24C02','J109':'QTE-020-01-L-D-A'},'TVRX2':{'U1':'AT24C02','U100':'TDA18272HN/M','U140':'TDA18272HN/S'}})
def children(node,tag):return [x for x in node if isinstance(x,list) and str(x[0])==tag]
def properties(node):return {str(x[1]):str(x[2]) for x in children(node,'property')}
def setproperty(node,k,v):
    found=next((x for x in children(node,'property') if str(x[1])==k),None)
    if found:found[2]=Q(str(v))
    else:node.append(prop(k,str(v),hide=True))
def choice(name,ref,value,footprint,old):
    row={'Reference':ref,'Value':value,'Footprint':footprint,'Manufacturer':'','MPN':'','LCSC':'','Sourcing_status':'规格选型，待锁定料号','Specification':'','Source_value':old,'Evidence':''}
    if value=='AT24C02':row=update_row(name,row)
    elif ref.startswith('FB') and name=='LFTX':row.update(Manufacturer='Sunlord 顺络',MPN='GZ3216D601TF',Sourcing_status='新选磁珠；需测电源噪声与压降',Specification='1206; 600 ohm @100 MHz; 600 mA; DCR <=0.30 ohm',Evidence='https://atta.szlcsc.com/upload/public/pdf/source/20151029/1457707509886.pdf')
    elif ref.startswith('R') and not any(x in value for x in ['pF','nF','uF']):
        row.update(Manufacturer='UNI-ROYAL 厚声',Specification='0603; <=1%; >=0.1 W; 按原值采购；反馈/终端电阻需同批次')
        if value.strip() in ['0','0R','0 Ohm']:row.update(MPN='0603WAF0000T5E',LCSC='C21189',Sourcing_status='已核对目录料号',Evidence='https://www.lcsc.com/product-detail/C21189.html')
    elif ref.startswith('C') or any(x in value for x in ['pF','nF','uF']):
        row.update(Manufacturer='FH 风华高科',Specification='按项目焊盘尺寸；RF/匹配/PLL环路优先 C0G；去耦 X7R；耐压 >=16 V；保留原容差')
        if value.strip()=='0.1uF':row.update(MPN='0603B104K500NT',LCSC='C30926',Sourcing_status='已核对目录料号，0603 时采用',Specification='0603; 100 nF; X7R; 50 V; +/-10%',Evidence='https://item.szlcsc.com/31683.html')
        if value.strip()=='10pF':row.update(MPN='0603CG100J500NT',LCSC='C91367',Sourcing_status='已核对目录料号，0603 时采用',Specification='0603; 10 pF; C0G; 50 V; +/-5%',Evidence='https://www.lcsc.com/product-detail/C91367.html')
    elif ref.startswith('L'):row.update(Manufacturer='Sunlord 顺络 / FH 风华高科',Specification='RF电感须核对 Q、SRF、DCR 与偏置电流，按原值及容差；磁珠按阻抗曲线选型')
    elif value.startswith(('AD','LT','LM','MIC','MGA','HMC','GVA','NDS','XC2','TDA','MT4937')):
        row.update(MPN=value,Sourcing_status='保留原功能型号；采购需核对后缀、封装与供应状态',Specification='射频/高速/低噪声器件，不作未经验证的国产等效替换')
    elif ref.startswith('J'):row.update(Specification='按工程封装和 USRP1 接口核对插合方向、针脚与高度')
    if value.lower() in ['none','dnp']:row.update(Sourcing_status='DNP 不装',Manufacturer='',MPN='',LCSC='',Specification='保留调试/选配焊盘')
    if name in ['WBX','TVRX2']:
        audit=json.loads((ROOT/'verification'/name/'footprint-audit.json').read_text());package=audit[ref]['source']
        if ref[0] in 'RCL' and '0402' in package:
            row.update(MPN='',LCSC='',Sourcing_status='0402 按参数选型，待锁定料号',Specification=('0402; <=1%; >=1/16 W; 保留原值' if ref.startswith('R') else '0402; 匹配和调谐电容用 C0G，保留原容差；去耦用 X7R >=16 V' if ref.startswith('C') else '0402; RF调谐电感；保留原值；需核对Q和SRF曲线'),Evidence='')
        if 'Polarized bulk' in package:row.update(Manufacturer='KEMET / 同规格钽电容',MPN='',LCSC='',Sourcing_status='按容量、16 V耐压、封装及ESR选型',Specification=package+'; LT1085输出电容须满足稳定性ESR要求')
        if value=='TC1-1-13M+':row.update(Manufacturer='Mini-Circuits',MPN=value,Specification='AT224-1A; 4.5–3000 MHz; 1:1; 源符号5脚改为实际6脚，保持同名端极性',Sourcing_status='已按厂商引脚及推荐焊盘重新映射',Evidence='https://www.minicircuits.com/pdfs/TC1-1-13M+.pdf')
        if value.startswith('TDA18272'):row.update(Manufacturer='NXP',MPN=value,Sourcing_status='已停产，需原装库存或拆机；U100主调谐器，U140从调谐器',Specification=package+'; /M Leader, /S Follower',Evidence='https://www.nxp.com/products/TDA18272HN')
        if value.lower()=='none':row.update(Sourcing_status='DNP 不装',Manufacturer='',MPN='',LCSC='',Specification='保留调试/选配焊盘')
    return update_row(name,row,package if name in ['WBX','TVRX2'] else '')
def apply(name):
    # Existing reviewed projects use the metadata-only backend, preserving copper.
    if (ROOT/'projects'/name/'BOM-sourcing.csv').exists():
        from apply_current_component_policy import apply as synchronize
        return synchronize(name)
    directory=ROOT/'projects'/name;docs={p:sexp.load_file(p) for p in directory.glob('*.kicad_sch')};rows={}
    for path,doc in docs.items():
        for symbol in children(doc,'symbol'):
            pp=properties(symbol);ref=pp.get('Reference','')
            if ref.startswith('#'):continue
            old=pp.get('Source_value',pp['Value']);value=LEGACY_VALUES.get(name,{}).get(ref,pp['Value'])
            row=choice(name,ref,value,pp.get('Footprint',''),old)
            rows[ref]=row
            for k in ['Manufacturer','MPN','LCSC','Sourcing_status','Specification','Source_value','Evidence']:setproperty(symbol,k,row[k])
            setproperty(symbol,'Value',value)
        for cache in children(doc,'lib_symbols'):
            for symbol in children(cache,'symbol'):
                libid=str(symbol[1]);ref=libid.split(':')[-1].split('_')[0]
                if ref in rows:setproperty(symbol,'Value',rows[ref]['Value'])
        sexp.save_file(path,doc)
    library=sexp.load_file(directory/'USRP.kicad_sym')
    for symbol in children(library,'symbol'):
        ref=str(symbol[1]).split('_')[0]
        if ref in rows:setproperty(symbol,'Value',rows[ref]['Value'])
    sexp.save_file(directory/'USRP.kicad_sym',library)
    board=directory/(name+'.kicad_pcb')
    if board.exists():
        b=pcb.LoadBoard(str(board))
        for fp in b.GetFootprints():
            if fp.GetReference() in rows:
                row=rows[fp.GetReference()];fp.SetValue(row['Value'])
                if hasattr(fp,'SetDNP'):fp.SetDNP(row['Value'].lower()=='none')
        pcb.SaveBoard(str(board),b)
    with (directory/'BOM-sourcing.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(next(iter(rows.values()))));writer.writeheader();writer.writerows(rows[r] for r in sorted(rows,key=lambda r:(re.sub(r'\d','',r),int(re.search(r'\d+',r)[0]))))
    print(name,len(rows),'BOM rows')
if __name__=='__main__':
    for name in sys.argv[1:] or LEGACY_VALUES:apply(name)
