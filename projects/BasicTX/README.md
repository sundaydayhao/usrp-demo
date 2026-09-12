# BasicTX

无源宽带发射接口，保留原变压器和接口连接。

使用 KiCad 10.0.5 验证。打开 `BasicTX.kicad_pro`，工程内包含可编辑原理图、PCB、`USRP.kicad_sym`、`USRP.pretty` 和本地库表。多页工程从同名顶层原理图进入。

ERC 错误 0，ERC 警告 2；DRC 错误 0，DRC 警告 9，未连接 0。详见检查报告。

- [采购 BOM](BOM-sourcing.csv)：实际 LCSC 编码仅在已核对型号与封装时填写；空白项仍需选型/询价。
- [预览](preview/)：原理图和 PCB 各铜层图。
- [完整设计说明](../../DESIGN_NOTES.md)：原始资料差异、USRP1 机械接口、RF 匹配、叠层、装配和样板验证限制。
- [检查证据](../../verification/BasicTX/)：ERC、DRC、网表、封装与射频检查记录。

必须连同设计说明审查。TVRX2/WBX 使用焊盘内过孔，应评审塞孔盖铜工艺。PCB 上无源器件位号可在 F.Fab/B.Fab 装配层查看。未进行实物功能或射频指标测试。

## 3D 模型

PCB 和本地封装库已绑定工程内的 `3dmodels/`，无需额外安装模型库。请保留整个工程目录。

- [正反面 3D 预览](preview/3d-views.pdf)
- [模型来源、简化模型与尺寸限制](../../3D_MODELS.md)

PMC 插座是简化外形模型；TVRX 的调谐模块也为简化外形，高度按 15 mm 示意，未包含外接 F 连接器。3D 外形补充没有修改电路、焊盘或 RF 走线。
