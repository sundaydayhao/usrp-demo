# AT24C02 与阻容感选型更新

2026-09-14。修改基线为 `bf6d371`；适用于 `projects/` 中七个工程。

## EEPROM

全部 8 颗 GT24C02A-2GLI-TR 改用 **Microchip AT24C02C-SSHM-T，立创 C6203**。原理图和 PCB 的 Value 显示 **AT24C02**，完整订货号保存在 MPN 属性和各工程 `BOM-sourcing.csv` 中。不要仅按通用名购买不同厂家或不同封装的 AT24C02。

| 工程 | 位号 | WP 接法 |
|---|---|---|
| BasicRX | U1 | 直接接地 |
| BasicTX | U52 | 直接接地 |
| LFRX | U1 | 经 R28（0 Ω）接地 |
| LFTX | U52 | 经 R29（0 Ω）接地 |
| TVRX | U1 | 直接接地 |
| TVRX2 | U1 | 直接接地 |
| WBX | U202、U403 | 分别接 RX、TX 数字地 |

采用窄体 SOIC-8，芯片本体 3.9 × 4.9 mm、引脚间距 1.27 mm；沿用现有焊盘、方向及 SOIC-8 3D 模型。1～8 脚依次为 A0、A1、A2、GND、SDA、SCL、WP、VCC；供电范围 1.7～5.5 V、容量 256 × 8 bit。TVRX2 U1、WBX U202/U403 的旧符号第 7 脚名称从 n/c 修正为 WP，符号库和所有原理图缓存同步。A0/A1/A2 接线及母板地址选择保持原样。依据：[Microchip 数据手册 DS20006111A](https://ww1.microchip.com/downloads/en/DeviceDoc/AT24C01C-AT24C02C-I2C-Compatible-Two-Wire-Serial-EEPROM-1Kbit-2Kbit-20006111A.pdf)。

**编程页长为 8 字节。** 写入程序每次发送长度应取 `min(剩余长度, 8 - (地址 % 8))`，不能沿用原 GT 器件的 16 字节页写假设。每次写后做 ACK polling，或等待最大 5 ms 写周期。字节写入也可以。空片仍需写入正确的 USRP1 子板识别数据；本次完成 CAD 替换，未进行 EEPROM 烧录和主板识别实测。页写与时序依据同一份 Microchip 手册的第 7 节。

## 阻容感

选型不再限定国产。BOM 和原理图隐藏属性增加 `Approved_brands`、`Sourcing_policy`：在满足参数的前提下比较含税到手价、起订量、库存和交期。Manufacturer 为“候选”且 MPN 为空的行仍未锁定具体料号，候选品牌不代表任意型号都能互换。

- 普通电阻允许国巨、Vishay、Panasonic、厚声、风华；普通陶瓷电容允许 Murata、TDK、Samsung、华新、风华、宇阳；电感与磁珠允许 Murata、TDK、Coilcraft、顺络、风华。
- 12 颗 0402 / 1 kΩ 电阻选定 **YAGEO RC0402FR-071KL，C106235**，±1%、1/16 W。TVRX2：R111、R151；WBX：R302～R307、R317、R330、R333、R334。用于原有控制、AGC 和偏置位置，阻值不变。依据：[国巨规格页](https://www.yageogroup.com/component-documentation/download/specsheet/RC0402FR-071KL)。
- 38 颗已核对为电源对地去耦的 0402 / 100 nF 电容选定 **Samsung CL05B104KO5NNNC，C1525**，X7R、16 V、±10%。TVRX2 共 5 颗、WBX 共 33 颗，具体位号见各工程 BOM 和 `component-update-review.json`。保留直流偏压降容要求。依据：[Samsung 原厂 MLCC 目录（立创镜像）](https://datasheet.lcsc.com/datasheet/pdf/02336ea48ea44ca18c72517dd3cb7b47.pdf?productCode=C1525)。
- 原有已核对的风华、厚声、顺络料号继续作为有效选项。RF 匹配、调谐及 PLL 电容保留容值、介质和容差要求；电感继续核对 Q、SRF、DCR、额定电流及频率曲线。钽电容保留封装与 ESR/稳压器稳定性约束。
- 修正部分以 R 开头、数值单位却为 pF 的源电容的采购分类说明；位号和电路不变。

### 公开价格与库存快照

以下为 2026-09-14 查询到的 LCSC 国际站产品页价格表，币种 USD，单位为美元/颗。它们用于本次选型对比，不是国内含税报价；实际采购仍按立创结算页和交期复核。没有下单。库存为页面显示值。

| 型号 / LCSC | 起订量 | 公开阶梯单价 | 页面库存 |
|---|---:|---|---:|
| [Microchip AT24C02C-SSHM-T / C6203](https://www.lcsc.com/product-detail/C6203.html) | 5 | 5+：0.2106；50+：0.1653；150+：0.1433 | 118,450 |
| [YAGEO RC0402FR-071KL / C106235](https://www.lcsc.com/product-detail/C106235.html) | 100 | 100+：0.0044；1,000+：0.0035；3,000+：0.0030 | 3,398,700 |
| [Samsung CL05B104KO5NNNC / C1525](https://www.lcsc.com/product-detail/C1525.html) | 100 | 100+：0.0046；1,000+：0.0034；3,000+：0.0029 | 12,458,200 |
| [Murata GRM155R71C104KA88D / C71629](https://www.lcsc.com/product-detail/C71629.html)，电容采购比较项，未绑定工程 | 100 | 100+：0.0052；1,000+：0.0047；3,000+：0.0045 | 2,404,200 |

同一采购数量下，查询到的三星去耦电容价格低于上述村田比较项，且库存更充足，因此本次选定三星。国巨页尾 FAQ 的价格/库存与当前产品价格表不同，本快照采用产品页价格表，不采用 FAQ 数值。

## 验证与交付

原理图实例、本地符号库和缓存、PCB、本地封装库、采购 BOM 及原理图 PDF 已同步。PCB 铜箔、过孔、焊盘、叠层、板框、位置、方向、实例路径、UUID 和既有 3D 模型均保持原样。采购候选策略记录在原理图和 BOM；8 颗 EEPROM 与 50 颗本次锁定的无源件另同步完整料号到 PCB/本地封装属性。

8 颗 EEPROM 的信号单元位号和型号文字已居中排到符号上方，修正旧标签压线或偏移的问题；其他可见文字布局不变。

机器审查记录为 `verification/<工程>/component-update-review.json`，汇总为 `verification/component-update-summary.json`。七个工程均为零 ERC 错误、零 DRC 错误、零未连接、零原理图/PCB 引脚网络不符；与基线相比警告集合不变。新增 EEPROM 原理图对比预览见 [AT24C02-review.pdf](deliverables/AT24C02-review.pdf)。

以前的 `3d-review.json` 是 3D 模型补充时的历史审查记录；本次模型保持性及当前 PCB 校验值以 `component-update-review.json` 和 `final-summary.json` 为准。PMC/TVRX 的简化 3D 外形及原有硬件/RF 待验证事项仍见 [3D_MODELS.md](3D_MODELS.md) 和 [DESIGN_NOTES.md](DESIGN_NOTES.md)。
