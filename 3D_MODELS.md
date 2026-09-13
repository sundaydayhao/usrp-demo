# 3D 模型补充说明

七个工程均已添加并校对 3D 模型。模型位于各工程的 `3dmodels/` 目录，PCB 与 `USRP.pretty` 封装库均使用 `${KIPRJMOD}/3dmodels/...`。打开工程后即可在 KiCad 3D 查看器显示，无需安装额外的 AD 或嘉立创EDA库。复制工程时应复制整个工程目录。

| 工程 | 原有模型绑定 | 当前模型绑定 | 新增 |
|---|---:|---:|---:|
| BasicRX | 0 | 26 | 26 |
| BasicTX | 0 | 20 | 20 |
| LFRX | 0 | 36 | 36 |
| LFTX | 0 | 55 | 55 |
| TVRX | 0 | 41 | 41 |
| TVRX2 | 105 | 109 | 4 |
| WBX | 275 | 291 | 16 |
| 合计 | 380 | 578 | 198 |

表中按 PCB 封装实例计数。裸安装孔、镀铜接地孔和 TVRX2 的八个蚀刻测试点不需要器件模型。DNP 器件保留模型绑定，实际显示取决于 KiCad 查看器的 DNP 显示选项。

## 模型来源

- 阻容、磁珠/电感、排针、SOIC、SOT、QFN/LFCSP 和 SMA：本机 KiCad 10 官方模型库。各 STEP 内保留作者信息；每个工程附 `3dmodels/KiCad-LICENSE.md`，遵循 [KiCad 模型库许可及设计例外](https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master/LICENSE.md)。普通封装采用外形匹配模型，颜色和顶部丝印不承诺与所采购品牌一致。
- ADT1-1WT+：嘉立创EDA/LCSC [C6835853](https://jlcpcb.com/partdetail/ADT1-1WT%2B/C6835853) 的 CD542 外形模型。模型实际外引脚与历史焊盘中心距不同，按封装中心与 1 脚方向对齐，没有为贴合焊盘而缩放外壳。
- TC1-1-13M+：嘉立创EDA/LCSC [C879854](https://jlcpcb.com/partdetail/MiniCircuits-TC1_1_13M/C879854) 的 AT224 外形模型，提供者文件名为 `XFMR-SMD_TC1-1TX`。用于对应封装外形，并不改变 BOM 的器件型号。
- WBX J109：嘉立创EDA/LCSC [C3640849](https://jlcpcb.com/partdetail/Samtec-QTE_020_01_L_D_A_KTR/C3640849)，QTE-020-01 封装外形。来源器件的镀层/包装后缀与工程不同，采用相同引脚数和高度系列的模型。系列资料见 [Samtec QTE-020-01-L-D-A](https://www.samtec.com/products/qte-020-01-l-d-a)。

每个工程的 `3dmodels/SOURCES.json` 记录原始文件和校验值，立创模型另附同名 JSON，含 LCSC 编码、模型 UUID、API 来源和 STEP 变换信息。导入模型的原作者/提供者权利保留；本工程不为这些来源模型另行声明许可。

## 两类简化模型

**PMC 插座与 MT4937DI5 的模型均明确命名为 `APPROX_DISPLAY`，不是厂家精确 CAD。** 未能取得可用的原厂 STEP 文件，因此按现有封装和可查系列资料制作了可显示、可替换的外形模型：

| 模型 | 已采用的数据 | 尚未确认或省略 |
|---|---|---|
| PMC64_APPROX_DISPLAY | 现有 PMC-REVERSE 引脚中心、定位孔和 F.Fab 外框；插座高度以 Molex 71439-0 系列的 5.3 mm 为代表值 | 实际子板插座完整料号、壳体壁形、弹片形状、插合干涉和最终堆叠高度。外框宽深为历史封装示意，不能视作厂家公差尺寸 |
| MT4937DI5_APPROX_DISPLAY | TVRX 原封装外框、信号引脚及接地脚位置；金属屏蔽壳示意 | **高度 15 mm 是显示假设**；外接 F 连接器、线缆净空和内部电路未建模，接地脚与引脚长度也是示意 |

PMC 的系列对应关系参考 [Molex 714390164](https://www.molex.com/en-us/products/part-detail/714390164) 和原厂产品规范 PS-71436-9999 中的 71439-0 系列高度表。模型用于补充外形预览，机壳、堆叠和接口碰撞设计仍应使用实际采购器件的机械图或实测尺寸。

个别芯片采用相同本体尺寸、引脚数和节距的通用模型，其模型底部裸焊盘尺寸可能与器件专用封装略有差异；PCB 的真实焊盘始终保留原工程数据。具体包括 ADL5386、ADL5387、ADA4937-2、HMC472、XC2C32A 及原先缺失文件的 40 脚 QFN、32 脚 LFCSP 模型。SMA 模型采用 5.08 mm 方形通孔脚距的 Amphenol 132134-11 外形，未据此改动实际采购 BOM。

## 对齐与验证

- 旧 gEDA 封装存在不同原点、旋转方向及底面表示方式。按引脚编号拟合旋转和位移，并通过 KiCad 原生 3D 渲染检查。TVRX 的底面器件保留旧 PCB 表示，只在 3D 变换中处理底面和板厚。
- 修复两个原本指向不存在文件的绑定：`HVQFN-40-1EP_6x6mm_P0.5mm_EP4.1x4.1mm.step` 和 `LFCSP-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm.step`，使用上述通用外形模型。
- easyeda2kicad 1.0.1 对 WRL 烘焙了位移，但会原样复制 STEP。这里将同一位移应用到 STEP，保留颜色和层级。三种立创模型的 STEP/WRL 包围盒最大差异不超过 0.001 mm。
- 对照 Git 基线 `45f46ab`，七块 PCB 及本地封装移除 `model` 节点后的语义完全相同；原理图、工程设置、RF 铜线、焊盘和器件位置保持一致。
- 重新执行 ERC、DRC 和引脚网表检查，仍为零错误、零未连接；原有警告集合没有新增或消失。模型文件路径全部可解析，PCB 与封装库绑定一致。
- 七块板正反面均用 KiCad 10.0.5 渲染并审查。每个工程附 `preview/3d-views.pdf`，总预览见 [3D-previews.pdf](deliverables/3D-previews.pdf)。

检查证据：`verification/<工程>/3d-models.json`、`3d-review.json`、`verification/3d-review-summary.json`。用于本次迁移的脚本在 `scripts/`，依赖本机 KiCad、KiSkill 解析器；立创重新获取/转换还需要 easyeda2kicad 与 cadquery-ocp。已交付的工程打开和 3D 显示不依赖这些脚本或临时目录。

2026-09-14 的 AT24C02 器件更新已另外核对：本节记录的 578 个模型绑定、模型文件和变换均保持不变。该次更新的当前 PCB 校验值及证据见各工程 `component-update-review.json`；此前 `3d-review.json` 保留为历史专项审查记录。
