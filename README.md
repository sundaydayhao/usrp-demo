# USRP1 七款子板 KiCad 工程

按用户提供资料重建，每款一个独立工程。BasicRX 与 RXMOD、BasicTX 与 TXMOD 分别合并，不重复交付。所有工程保留 USRP1 接口。

2026-09-14 更新：七个工程的 8 颗 EEPROM 全部改为 **AT24C02（Microchip AT24C02C-SSHM-T / C6203）**，同步原理图、PCB 和 BOM。阻容感支持按价格与供货选择国内或国际品牌；本次锁定 12 颗国巨电阻和 38 颗三星去耦电容。详见 [器件更新说明与采购快照](COMPONENT_UPDATE.md)，EEPROM 页写长度为 8 字节。

| 工程 | 原理图 | PCB | ERC 错误 | DRC 错误 | 未连接 |
|---|---|---|---:|---:|---:|
| [BasicRX](projects/BasicRX/BasicRX.kicad_pro) | [原理图](projects/BasicRX/BasicRX.kicad_sch) | [PCB](projects/BasicRX/BasicRX.kicad_pcb) | 0 | 0 | 0 |
| [BasicTX](projects/BasicTX/BasicTX.kicad_pro) | [原理图](projects/BasicTX/BasicTX.kicad_sch) | [PCB](projects/BasicTX/BasicTX.kicad_pcb) | 0 | 0 | 0 |
| [LFRX](projects/LFRX/LFRX.kicad_pro) | [原理图](projects/LFRX/LFRX.kicad_sch) | [PCB](projects/LFRX/LFRX.kicad_pcb) | 0 | 0 | 0 |
| [LFTX](projects/LFTX/LFTX.kicad_pro) | [原理图](projects/LFTX/LFTX.kicad_sch) | [PCB](projects/LFTX/LFTX.kicad_pcb) | 0 | 0 | 0 |
| [TVRX](projects/TVRX/TVRX.kicad_pro) | [原理图](projects/TVRX/TVRX.kicad_sch) | [PCB](projects/TVRX/TVRX.kicad_pcb) | 0 | 0 | 0 |
| [TVRX2](projects/TVRX2/TVRX2.kicad_pro) | [原理图](projects/TVRX2/TVRX2.kicad_sch) | [PCB](projects/TVRX2/TVRX2.kicad_pcb) | 0 | 0 | 0 |
| [WBX](projects/WBX/WBX.kicad_pro) | [原理图](projects/WBX/WBX.kicad_sch) | [PCB](projects/WBX/WBX.kicad_pcb) | 0 | 0 | 0 |

检查状态来自 `verification/<工程名>/final-summary.json`，只说明 CAD 文件在记录时通过了哪些检查。完整说明见 [DESIGN_NOTES.md](DESIGN_NOTES.md)。

每个目录自带符号、封装、库表、采购 BOM 与预览。用 KiCad 10 打开 `.kicad_pro` 即可编辑。WBX/TVRX2 为按公开资料重新设计的 PCB，射频指标、机械插接和上电功能仍需样板验证；WBX 的 LO 变压器频率裕量、TVRX2 的 CPLD 编程文件尚未通过实物验证。

五款旧板从历史 gEDA CAD 恢复；两款复杂板从 PDF 重建。具体版本、数值差异、器件替代和工艺约束均在设计说明中列出。

WBX 为自定义六层，另外六款为四层；六层的板厂压合与阻抗确认是打样前的必要工作。检查报告保留孤立标签及历史铜线末端等警告，零错误不表示没有警告。

[审查记录](REVIEW.md)列出检查覆盖范围与未验证项目。

## 3D 模型更新

七个工程现有 578 个模型绑定（新增 198 个），全部使用工程内相对路径，并同步至本地封装库。已核对正反面预览，电路和 RF 走线保持不变。PMC 插座与 TVRX 调谐模块采用明确标注的简化外形，机械尺寸限制见 [3D 模型说明](3D_MODELS.md)。

[七款板 3D 预览 PDF](deliverables/3D-previews.pdf) · [完整工程包](deliverables/USRP1-seven-KiCad-projects.zip)
