# WBX

旧版 ADL5386/ADL5387 宽带收发板；默认 SMA 装配，保留两个 USRP1 接插件。

使用 KiCad 10.0.5 验证。打开 `WBX.kicad_pro`，工程内包含可编辑原理图、PCB、`USRP.kicad_sym`、`USRP.pretty` 和本地库表。多页工程从同名顶层原理图进入。

ERC 错误 0，ERC 警告 6；DRC 错误 0，DRC 警告 22，未连接 0。详见检查报告。

- [采购 BOM](BOM-sourcing.csv)：实际 LCSC 编码仅在已核对型号与封装时填写；空白项仍需选型/询价。
- [预览](preview/)：原理图和 PCB 各铜层图。
- [完整设计说明](../../DESIGN_NOTES.md)：原始资料差异、USRP1 机械接口、RF 匹配、叠层、装配和样板验证限制。
- [检查证据](../../verification/WBX/)：ERC、DRC、网表、封装与射频检查记录。

必须连同设计说明审查。TVRX2/WBX 使用焊盘内过孔，应评审塞孔盖铜工艺。PCB 上无源器件位号可在 F.Fab/B.Fab 装配层查看。未进行实物功能或射频指标测试。
