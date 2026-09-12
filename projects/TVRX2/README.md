# TVRX2

双 TDA18272 调谐器接收板；需要正确 /M、/S 器件和已编程 CPLD。

使用 KiCad 10.0.5 验证。打开 `TVRX2.kicad_pro`，工程内包含可编辑原理图、PCB、`USRP.kicad_sym`、`USRP.pretty` 和本地库表。多页工程从同名顶层原理图进入。

ERC 错误 0，ERC 警告 14；DRC 错误 0，DRC 警告 0，未连接 0。详见检查报告。

- [采购 BOM](BOM-sourcing.csv)：实际 LCSC 编码仅在已核对型号与封装时填写；空白项仍需选型/询价。
- [预览](preview/)：原理图和 PCB 各铜层图。
- [完整设计说明](../../DESIGN_NOTES.md)：原始资料差异、USRP1 机械接口、RF 匹配、叠层、装配和样板验证限制。
- [检查证据](../../verification/TVRX2/)：ERC、DRC、网表、封装与射频检查记录。

必须连同设计说明审查。TVRX2/WBX 使用焊盘内过孔，应评审塞孔盖铜工艺。PCB 上无源器件位号可在 F.Fab/B.Fab 装配层查看。未进行实物功能或射频指标测试。
