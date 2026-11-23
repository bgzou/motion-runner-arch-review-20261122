# V1.3 50 Hz 频率修订版入口

> V1.3 = V1.2 讲解合并版 + **50 Hz 策略频率决策**。架构决策、36 个讲解 patch、V1.1 原稿都保留；本次只改频率相关合同。**P0 `can_exit` 仍未修，不能上机。**

## 1. 三分钟路线

1. [REVIEW_V1.3.md](../REVIEW_V1.3.md)：这版改了什么、哪里还没改；
2. [00_导读.md](00_导读.md)：五幕故事 + 五层/四流/三时钟（50/200/1k）；
3. [Part2_D3-D4.md](Part2_D3-D4.md) 的 `can_exit`：50 Hz 下 TTL 从 10 ms 改 25 ms；
4. [Part3_D5-D6.md](Part3_D5-D6.md) 的 D5.7：15/20 ms 预算、ZOH；
5. [Appendix_D_Concept_Deep_Dive.md](Appendix_D_Concept_Deep_Dive.md)：HAL、Manifest、8 Runner、时序、配置。

## 2. 全文与分 Part

- 全文：[Collie_MC_V1.3_Full_D0-D16_50Hz.md](Collie_MC_V1.3_Full_D0-D16_50Hz.md)
- Part1：[D0–D2](Part1_D0-D2.md)
- Part2：[D3–D4](Part2_D3-D4.md)
- Part3：[D5–D6](Part3_D5-D6.md)
- Part4：[D7–D8](Part4_D7-D8.md)
- Part5：[D9–D12](Part5_D9-D12.md)
- Part6：[D13–D16](Part6_D13-D16.md)

## 3. 合同与索引

- [HAL 合同](Appendix_A_HAL_Contract.md)
- [Schema Canon](Appendix_B_Schema_Canon.md)
- [协议/示例/测试索引](Appendix_C_Protocol_Examples_Tests.md)
- [概念解释篇](Appendix_D_Concept_Deep_Dive.md)
- [V1.3 频率自检](Appendix_E_Self_Check.md)
- [ADR-25：策略 50 Hz](../ADR-25_策略频率50Hz.md)

## 4. 50 Hz 改了什么

| 项 | V1.2（T1 基线） | V1.3（Collie 50 Hz） |
|---|---:|---:|
| 策略 | 100 Hz / 10 ms | **50 Hz / 20 ms** |
| Worker | 100 Hz / 10 ms | **50 Hz / 20 ms** |
| Worker 预算 | 7.6 / 10 ms | **15 / 20 ms** |
| `can_exit` TTL | 10 ms | **25 ms** |
| `snapshot_seq` 差 | ≤2 | **≤4** |
| 候选 deadline | tick+8 ms | **tick+15 ms** |
| `max_hold` | 10 ms | **25 ms** |
| RT | 200 Hz | **200 Hz，ZOH** |
| 黑匣子 Worker | 100 Hz / 819200 B/s | **50 Hz / 409600 B/s** |

**RT 不是插值**：50 Hz 目标在 200 Hz 下保持 4 个 tick；插值只能作为额外的、经训练/HIL 验证的整形。

## 5. 边界

- T1 的 100 Hz / 196 Hz 发布 / 10.5 ms WBC 是 T1 实证，不是 Collie 事实；
- `mc_safety` 100 Hz、SafetyLease 30 ms、HAL 15 ms、PD 1 kHz 不变；
- `can_exit` pre-step READY P0 未修；50 Hz 把窗口放大到 20 ms，切换前必须先修；
- 36/36 是 SIL/合同/Schema/文本检查，不是 HIL；
- Collie 拓扑/双足/Q2B/HAL watchdog/WCET/功能安全/密钥未签收，**不能上机**。

## 6. 独立 Deck

新版：[`04_ARCHITECTURE_REVIEW_v3_50Hz.html`](../04_ARCHITECTURE_REVIEW_v3_50Hz.html)  
讲法：[`DECK_GUIDE.md`](../DECK_GUIDE.md)  
旧版 V1.2 Deck 未上传；本地保留，仅作对照。
