# Not included in this repository

为了控制仓库体积并聚焦架构评审，以下内容**没有上传**；文档中指向它们的链接会跳转到本页。

| 未包含内容 | 原项目路径 | 为什么不需要 |
|---|---|---|
| `roboto_origin-main/`（约 2.1 GB） | `03_参考库/roboto_origin-main/` | 外部开源参考实现；关键结论已摘录到 `runner/runner-integration-master.md` §9 |
| ONNX 权重（640 份，约 848 MB） | `04_真机与模型数据/运控模型库/真机/**/模型/` | 架构评审只需清单、tensor 规格与配置，不需要权重本体 |
| 真机二进制/固件（约 1.5 GB） | Z 盘 `software/<app>/bin/` | 未复制；Runner 结论来自只读符号检查 |
| SDK 示例源码树（OpenCV 等） | `03_参考库/qiliang_T1Pro报告库/docs/primebot/sdk_t1-v1.0.0.0/examples/` | 与运控架构无关 |
| 早期站点 HTML/文本报告 | `03_参考库/历史分析报告/` | 结论已收敛到当前主文档 |
| 历史生成脚本 | `06_工具脚本/` | 一次性文档生成脚本，不是生产代码 |
| 旧版本快照 | `99_归档/` | 仅追溯 |

## 需要时怎么办

- 需要核对某条真机配置：优先看 `evidence/configs/` 与 `evidence/model-list/`；
- 需要核对接口字段：看 `evidence/interfaces/MC_INTERFACE_CATALOG.md`；
- 需要核对 T1 架构：看 `system/t1-architecture-deep-dive.md` 与 `reference/`；
- 仍缺的内容，请让项目方从本地原路径提供，**不要凭空补数**。
