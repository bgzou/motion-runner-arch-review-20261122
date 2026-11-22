# V1.1 架构阅读与任务入口（先读这一页）

这是 **V1.1 合并阅读版 + 讲解/Deck 任务书** 的在线入口。  
V1.0 的原始输入包仍在仓库根目录，作为历史对照；本页只指向 V1.1 的新材料。

## 1. 先读什么

| 顺序 | 文件 | 用途 |
|---|---|---|
| 1 | [PROMPT_FOR_GPT_V1.2_ALL_IN_ONE.md](PROMPT_FOR_GPT_V1.2_ALL_IN_ONE.md) | **任务书**：一次性产出 13 个交付物 |
| 2 | [Full_D0-D16.md](Full_D0-D16.md) | **V1.1 合并全文**（D0–D16，约 6.3 万字） |
| 3 | [Appendix_A_HAL_Contract.md](Appendix_A_HAL_Contract.md) | HAL 合同：唯一 writer、Epoch、watchdog |
| 4 | [Appendix_B_Schema_Canon.md](Appendix_B_Schema_Canon.md) | 字段/配置/容量唯一说明 |
| 5 | [REVIEW_V1.1.md](REVIEW_V1.1.md) | 已知 P0/P1、评审意见 |
| 6 | [Appendix_C_Protocol_Examples_Tests.md](Appendix_C_Protocol_Examples_Tests.md) | proto/schema/example/test 索引 |
| 7 | [README.md](README.md) | 合并版说明/阅读顺序/文件地图 |

分 Part（需要细化时读）：

- [Part1_D0-D2.md](Part1_D0-D2.md)
- [Part2_D3-D4.md](Part2_D3-D4.md)
- [Part3_D5-D6.md](Part3_D5-D6.md)
- [Part4_D7-D8.md](Part4_D7-D8.md)
- [Part5_D9-D12.md](Part5_D9-D12.md)
- [Part6_D13-D16.md](Part6_D13-D16.md)

启动用的短指令：[GPT_LAUNCH_PROMPT.md](GPT_LAUNCH_PROMPT.md)。

## 2. 关键边界

- **A. 报告融合包**（可并入 V1.1 报告）：`01_BIG_PICTURE`、`02_CONCEPT_DEEP_DIVE`、`03_PART_ENRICHMENT/Part1–6`、`05_INTEGRATION_GUIDE`、`06_SELF_CHECK`、`MANIFEST`。
- **B. 独立演示**（不并入报告）：`04_ARCHITECTURE_REVIEW.html`，单独打开、单独讲。
- `Full_D0-D16.md` 是阅读版；字段冲突时以 `Appendix_B` / `proto` / `schemas` 为准，HAL 冲突时以 `Appendix_A` 为准。
- `can_exit` 在 `step` 前发布 `READY` 的竞态**没有修**，见 Full 的 Part2 §D3.5 与 `REVIEW_V1.1.md` §2.1；不要假装已解决。
- 36 个测试是 SIL/合同测试，不是系统测试；不能据此上机。

## 3. 如果只读一个文件

读 [Full_D0-D16.md](Full_D0-D16.md)，但先看 `REVIEW_V1.1.md` 的 §1–§2，知道哪些是已知问题。
