# Collie MC V1.3 50 Hz 频率修订版 · 说明

> **是什么**：在 V1.2 讲解合并版上，把策略频率从 100 Hz 改为 **50 Hz（20 ms）**，同步 Worker、`can_exit` TTL、候选保持、黑匣子采样和 Deck。
> **不是什么**：不是重写架构；不是实机批准；不是把 T1 的 100 Hz 证据改成 50 Hz。**P0 `can_exit` 仍未修。**

---

## 1. 文件地图

| 文件 | 内容 |
|---|---|
| [REVIEW_V1.3.md](../REVIEW_V1.3.md) | 本次修订的审阅、改点、残留 |
| [00_READ_ME_FIRST.md](00_READ_ME_FIRST.md) | 三分钟入口 |
| [00_导读.md](00_导读.md) | 五幕故事 + 五层/四流/三时钟（50/200/1k） |
| [Collie_MC_V1.3_Full_D0-D16_50Hz.md](Collie_MC_V1.3_Full_D0-D16_50Hz.md) | 全文（6 Part + 附录 D/E） |
| [Part1_D0-D2.md](Part1_D0-D2.md) … [Part6_D13-D16.md](Part6_D13-D16.md) | 六个分 Part |
| [Appendix_A_HAL_Contract.md](Appendix_A_HAL_Contract.md) | HAL 合同（不变） |
| [Appendix_B_Schema_Canon.md](Appendix_B_Schema_Canon.md) | Schema；`ExitDecision` 序差/年龄、黑匣子预算已改 |
| [Appendix_C_Protocol_Examples_Tests.md](Appendix_C_Protocol_Examples_Tests.md) | 协议/示例/测试索引（不变） |
| [Appendix_D_Concept_Deep_Dive.md](Appendix_D_Concept_Deep_Dive.md) | 概念解释（时序/预算已改） |
| [Appendix_E_Self_Check.md](Appendix_E_Self_Check.md) | V1.3 频率自检 |
| [ADR-25](../ADR-25_策略频率50Hz.md) | 50 Hz 决策依据 |

V1.2 原稿未上传；本地保留在 `20261123_v1.2/merged/`。

---

## 2. 50 Hz 的完整口径

```text
策略推理：50 Hz / 20 ms
Worker：  50 Hz / 20 ms；预算 15 / 20 ms（5 ms 裕量）
RT：      200 Hz / 5 ms；只读最新有效候选
发布：    ZOH（一个目标保持 4 个 RT tick），不默认插值
HAL/PD：  1 kHz
Safety：  100 Hz；SafetyLease 30 ms
TTL：     can_exit 25 ms；max_hold 25 ms；candidate deadline tick+15 ms
序差：    snapshot_seq ≤4（200/50）
```

**为什么 Worker 不是 100 Hz**：50 Hz 策略每 20 ms 才产生新目标；100 Hz 只会空转，并让观测历史与训练 `dt=0.02` 不一致。只有未来出现 100 Hz 策略，才把 `period_ms` 改 10、Worker 改 100 Hz。

**为什么 RT 不是插值**：训练侧一个 action 保持 20 ms，部署也应保持；插值会改变闭环动力学。插值只能作为 `ActionCodec/ReferenceShaper` 的显式设计，经训练/HIL 验证，不是默认。

---

## 3. 改点

| 参数 | V1.2 | V1.3 |
|---|---:|---:|
| 策略/Worker | 100 Hz / 10 ms | **50 Hz / 20 ms** |
| Worker 预算 | 7.6/10 | **15/20** |
| `can_exit` TTL | 10 ms | **25 ms** |
| `snapshot_seq` 差 | ≤2 | **≤4** |
| 候选 deadline | tick+8 ms | **tick+15 ms** |
| `max_hold` | 10 ms | **25 ms** |
| 黑匣子 Worker | 819200 B/s | **409600 B/s** |
| 总黑匣子 | 870400 B/s | **460800 B/s** |
| 40 s 窗口 | 33.20 MiB | **17.58 MiB** |

已同步：Part1 进程/时序表、Part2 `can_exit` 契约、Part3 D5.7 预算、Part4 D8.1、Part5 D10.2、Part6 ADR、Appendix B/D/E、Deck。

**未改**：T1 100 Hz 实证、`mc_safety` 100 Hz、SafetyLease 30 ms、HAL 15 ms、PD 1 kHz、RT 200 Hz。

---

## 4. 必须先修 P0

`can_exit` 在 `step()` 前发布 `READY` 的竞态仍在。50 Hz 下 READY 可存活 20 ms（TTL 25 ms），比 100 Hz 的 10 ms 窗口更大。  
**在修好“READY 只在 step 成功后发布 + 完成序号/phase/fault”之前，不能开放新动作切换。**

---

## 5. 不能上机

Collie 拓扑/标定、双足支撑、Q2B/B2Q 资产、HAL 独立 watchdog、50 Hz 模型 WCET、ZOH 跟踪、功能安全、密钥均未签收。36/36 仍是 SIL/合同/Schema/文本检查，不是 HIL。
