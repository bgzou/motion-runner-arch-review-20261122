# Collie MC V1.3 50 Hz 频率修订版

> 在 V1.2 讲解合并版上，把策略频率统一为 **50 Hz（20 ms）**：Worker 50 Hz、RT 200 Hz ZOH、15/20 ms 预算、25 ms TTL。T1 的 100 Hz 证据保留，不改写。

## 先看

1. [评审意见](REVIEW_V1.3.md)
2. [合并版入口](merged/00_READ_ME_FIRST.md)
3. [合并版说明](merged/README.md)

## 报告

- [全文：Collie_MC_V1.3_Full_D0-D16_50Hz.md](merged/Collie_MC_V1.3_Full_D0-D16_50Hz.md)
- [导读](merged/00_导读.md)
- [Part1](merged/Part1_D0-D2.md)｜[Part2](merged/Part2_D3-D4.md)｜[Part3](merged/Part3_D5-D6.md)｜[Part4](merged/Part4_D7-D8.md)｜[Part5](merged/Part5_D9-D12.md)｜[Part6](merged/Part6_D13-D16.md)
- 附录：[A HAL](merged/Appendix_A_HAL_Contract.md)｜[B Schema](merged/Appendix_B_Schema_Canon.md)｜[C 协议索引](merged/Appendix_C_Protocol_Examples_Tests.md)｜[D 概念解释](merged/Appendix_D_Concept_Deep_Dive.md)｜[E 频率自检](merged/Appendix_E_Self_Check.md)

## 独立 Deck

- **V1.3 新版（50 Hz）**：[04_ARCHITECTURE_REVIEW_v3_50Hz.html](04_ARCHITECTURE_REVIEW_v3_50Hz.html)
- [Deck 使用说明](DECK_GUIDE.md)
- 渲染截图：[五层主图](evidence/deck_02_50hz.png)｜[50Hz/200Hz 时间轴](evidence/deck_04_50hz_timeline.png)
- 旧 V1.2 Deck：未上传；本地保留在 `20261123_v1.2`（100 Hz 基线，仅作对照）

## 决策依据

- [ADR-25：Collie 策略推理采用 50 Hz](ADR-25_策略频率50Hz.md)
- [T1 100 Hz 证据](../runner/t1-mc-decomposition.md)（保留对照）

## 边界

- `can_exit` pre-step READY 的 P0 仍是 **未修**；50 Hz 把窗口从 10 ms 放大到 20 ms，切换前必须先修。
- 50 Hz 的 15/20 ms 是目标预算，不是 Collie 实测 WCET；ZOH 的 4:1 保持需 HIL。
- 36/36 是 SIL/合同/Schema/文本检查，不是系统/HIL。
- 拓扑/双足/Q2B/HAL watchdog/功能安全/密钥未签收，**不能上机**。
- V1.2 原稿未上传；本地保留在 `20261123_v1.2/merged/`。
