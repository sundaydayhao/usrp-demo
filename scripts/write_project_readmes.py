"""Write a project index using the current verified status, without guessing."""
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parents[1];names=['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX'];rows=[]
details={'BasicRX':'无源宽带接收接口，保留原变压器和接口连接。','BasicTX':'无源宽带发射接口，保留原变压器和接口连接。','LFRX':'低频接收板，保留模拟前端和差分输出滤波网络。','LFTX':'低频发射板，保留模拟链路和电源变换；磁珠值按原 BOM 修正。','TVRX':'基于 MT4937DI5 调谐模块的接收板。旧模块采购是主要限制。','TVRX2':'双 TDA18272 调谐器接收板；需要正确 /M、/S 器件和已编程 CPLD。','WBX':'旧版 ADL5386/ADL5387 宽带收发板；默认 SMA 装配，保留两个 USRP1 接插件。'}
for name in names:
 d=ROOT/'projects'/name;vd=ROOT/'verification'/name;status=vd/'final-summary.json';s=json.loads(status.read_text()) if status.exists() else None
 if s:
  e=sum(v for k,v in s['erc'].items() if k.startswith('error:'));de=sum(v for k,v in s['drc'].items() if k.startswith('error:'));warnings=sum(v for k,v in s['erc'].items() if k.startswith('warning:'));dw=sum(v for k,v in s['drc'].items() if k.startswith('warning:'));uc=s['unconnected'];text=f'ERC 错误 {e}，ERC 警告 {warnings}；DRC 错误 {de}，DRC 警告 {dw}，未连接 {uc}。详见检查报告。'
 else:text='最终检查尚未完成；当前工作文件不代表完成状态。';e=de=uc='待检查'
 rows.append(f'| [{name}](projects/{name}/{name}.kicad_pro) | [原理图](projects/{name}/{name}.kicad_sch) | [PCB](projects/{name}/{name}.kicad_pcb) | {e} | {de} | {uc} |')
 contents=f'''# {name}\n\n{details[name]}\n\n使用 KiCad 10.0.5 验证。打开 `{name}.kicad_pro`，工程内包含可编辑原理图、PCB、`USRP.kicad_sym`、`USRP.pretty` 和本地库表。多页工程从同名顶层原理图进入。\n\n{text}\n\n- [采购 BOM](BOM-sourcing.csv)：实际 LCSC 编码仅在已核对型号与封装时填写；空白项仍需选型/询价。\n- [预览](preview/)：原理图和 PCB 各铜层图。\n- [完整设计说明](../../DESIGN_NOTES.md)：原始资料差异、USRP1 机械接口、RF 匹配、叠层、装配和样板验证限制。\n- [检查证据](../../verification/{name}/)：ERC、DRC、网表、封装与射频检查记录。\n\n必须连同设计说明审查。TVRX2/WBX 使用焊盘内过孔，应评审塞孔盖铜工艺。PCB 上无源器件位号可在 F.Fab/B.Fab 装配层查看。未进行实物功能或射频指标测试。\n'''
 (d/'README.md').write_text(contents,encoding='utf-8')
root='''# USRP1 七款子板 KiCad 工程\n\n按用户提供资料重建，每款一个独立工程。BasicRX 与 RXMOD、BasicTX 与 TXMOD 分别合并，不重复交付。所有工程保留 USRP1 接口。\n\n| 工程 | 原理图 | PCB | ERC 错误 | DRC 错误 | 未连接 |\n|---|---|---|---:|---:|---:|\n'''+ '\n'.join(rows)+'''\n\n检查状态来自 `verification/<工程名>/final-summary.json`，只说明 CAD 文件在记录时通过了哪些检查。完整说明见 [DESIGN_NOTES.md](DESIGN_NOTES.md)。\n\n每个目录自带符号、封装、库表、采购 BOM 与预览。用 KiCad 10 打开 `.kicad_pro` 即可编辑。WBX/TVRX2 为按公开资料重新设计的 PCB，射频指标、机械插接和上电功能仍需样板验证；WBX 的 LO 变压器频率裕量、TVRX2 的 CPLD 编程文件尚未通过实物验证。\n\n五款旧板从历史 gEDA CAD 恢复；两款复杂板从 PDF 重建。具体版本、数值差异、器件替代和工艺约束均在设计说明中列出。\n'''
(ROOT/'README.md').write_text(root,encoding='utf-8');print('Seven project READMEs and root index written')
with (ROOT/'README.md').open('a',encoding='utf-8') as out:
 out.write('\nWBX 为自定义六层，另外六款为四层；六层的板厂压合与阻抗确认是打样前的必要工作。检查报告保留孤立标签及历史铜线末端等警告，零错误不表示没有警告。\n\n[审查记录](REVIEW.md)列出检查覆盖范围与未验证项目。\n')
