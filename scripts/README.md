# 生成和检查脚本

交付对象是 `projects/` 中已经布好并检查过的 KiCad 工程。修改前先保存版本；不要把全部脚本按文件名顺序重跑。

- `build_*`、`import_legacy_boards.py`、`prepare_advanced_routing.py` 会重建文件或重新设置布局，只用于恢复设计的早期阶段。
- `relocate_*`、`escape_*`、`adjust_*`、`restore_*`、`complete_wbx_rf_classification.py`、`import_wbx_rf_additional.py` 是本次设计过程的专项修改记录，不是可重复运行的日常命令。
- `verify_final_projects.py <工程名>` 用 KiCad Python 检查 ERC、DRC、PCB 引脚/网络、原理图实例路径、板框外铜箔，以及复杂板的射频层和参考地。一次进程检查一块板。
- `verify_pdf_projects.py` 比较 WBX/TVRX2 与 PDF 恢复连接模型；`audit_pdf_reference_inventory.py` 独立核对 PDF 的器件清单。
- `render_previews.py`、`write_project_readmes.py` 更新预览与检查状态索引。
- 布线脚本只处理普通网络，RF 固定铜箔由独立检查保护。局部重布必须重新执行 DRC 和射频参考地检查。
- WBX 最终为六层。历史 DSN/SES 导出与导入脚本来自早期四层阶段，不能直接覆盖最终板；`expand_wbx_six_layers.py` 也是一次性迁移记录。
- `review_wbx_stack_transition.py` 比较六层迁移前后的 RF 铜箔和叠层；比较基线保存在本机检查点中，未随交付包发布。
- `export_delivery_previews.py` 导出原理图、铜层和正反面装配 PDF；`package_delivery.py` 在检查状态和 PCB 校验值吻合后打包。

KiCad 运行时为 10.0.5，脚本中的 Windows 路径按本机配置。导入交换文件时，坐标和线宽必须同时按 SES `resolution` 缩放。脚本保留了中间尝试；最终状态以 `final-summary.json` 及其 PCB SHA-256 为准。
