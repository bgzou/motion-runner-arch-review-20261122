# V1.1 合并阅读版 · 说明

> **这是什么**：把 V1.0 的 D0–D16 结构 + V1.1 的 9 处修订合并成一套可直接通读的文档。
> **保留什么**：V1.0 原稿不动；V1.1 原始变更单/合同不动；本目录只是“阅读版”。
> **状态**：软件设计基线（可拆任务编码），**不是实机安全批准**。

---

## 1. 文件地图

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| [Collie_MC_V1.1_Full_D0-D16.md](Collie_MC_V1.1_Full_D0-D16.md) | 全文合并版（约 63 KB / 1,418 行） | 想从头读到尾时 |
| [Part1_D0-D2_执行摘要_架构总览_领域模型.md](Part1_D0-D2_执行摘要_架构总览_领域模型.md) | 一页结论、12 决策、四进程、领域/状态机 | 第一遍必读 |
| [Part2_D3-D4_Runner框架_PolicyManager.md](Part2_D3-D4_Runner框架_PolicyManager.md) | IRunner、8 类 Runner、Q2B/B2Q、ModeTransition、PolicyManager/ControlLease | 核心 |
| [Part3_D5-D6_每拍链路_上下游接口.md](Part3_D5-D6_每拍链路_上下游接口.md) | 10 ms 链路、Obs/ActionSpec、接口、HAL 摘要 | 核心 |
| [Part4_D7-D8_安全_并发实时.md](Part4_D7-D8_安全_并发实时.md) | 危害/FMEA、8 故障、安全状态机、线程/WCET | 安全必读 |
| [Part5_D9-D12_配置资产_观测回放_测试_网络安全.md](Part5_D9-D12_配置资产_观测回放_测试_网络安全.md) | 配置/Manifest/黑匣子/测试/STRIDE | 交付/测试 |
| [Part6_D13-D16_ADR_风险_路线图_评审清单.md](Part6_D13-D16_ADR_风险_路线图_评审清单.md) | 24 ADR、16 风险、P0–P5、20 checklist | 决策/排期 |
| [Appendix_A_HAL_Contract.md](Appendix_A_HAL_Contract.md) | V1.1 `HAL_CONTRACT.md` 全文 | 需要 HAL 细节时 |
| [Appendix_B_Schema_Canon.md](Appendix_B_Schema_Canon.md) | V1.1 `SCHEMA_CANON.md` 全文 | 需要字段/容量细节时 |
| [Appendix_C_Protocol_Examples_Tests.md](Appendix_C_Protocol_Examples_Tests.md) | proto/schemas/examples/tests 索引 | 编码/测试时 |

原始材料：
- V1.0：`../../20261122_6parts/`（原样保留）
- V1.1 原始包：`../Collie_MC_V1.1_20261122/`（原样保留）
- V1.1 评审：`../REVIEW_V1.1.md`

---

## 2. 建议阅读顺序

### 第一遍（约 3–4 小时）：先形成整体判断

1. `Part1` 全文；
2. `Part2` 的 D3.1–D3.5（Runner 接口/can_exit/二维工厂/模式切换）；
3. `Part3` 的 D5.1–D5.7（每拍链路/预算）；
4. `Part4` 的 D7.1–D7.6（危害/FMEA/8 故障/安全状态机）；
5. `Part6` 的 D13/D14/D16（ADR/风险/checklist）。

### 第二遍（约 4–6 小时）：按主题精读

- 接口/字段：`Part3` + `Appendix_B` + `Appendix_C`；
- HAL/唯一 writer：`Part2` §D3.5 + `Appendix_A`；
- 配置/资产：`Part5` §D9 + `Appendix_B`；
- 测试/验收：`Part5` §D11 + `Appendix_C`；
- 安全/实时：`Part4` + `Appendix_A` §3–§6。

### 第三遍（约 2–3 小时）：对照 V1.0/V1.1 与评审

- 看 `../REVIEW_V1.1.md` 的 §1–§2；
- 对每个 P0/P1，回到本版对应章节，确认是否已合并；
- 填 [REVIEW_SHEET.md](../../../REVIEW_SHEET.md)。

---

## 3. V1.0 → V1.1 合并了什么

| 主题 | V1.1 修订 | 本版位置 |
|---|---|---|
| `can_exit` | Worker sealed `ExitDecision`，RT 只读 | Part 2 §D3.5 |
| 启动安全 | `INIT/UNKNOWN`，未知支撑不发保持 | Part 1 §D2；Part 4 §D7.4 |
| HAL 合同 | 唯一 writer token、Epoch 两阶段、PREPARE_MODE、watchdog、HAL-01..08 | 附录 A；Part 2 §D3.5、Part 4 §D8 |
| Schema | `nodes`、`timeout_ms/deadline_ns`、MotionStatus 32 字段、双层资产状态、128 MiB | Part 3/5；附录 B |
| Runner 工厂 | `ExecutionKind × BehaviorRole` 二维矩阵 | Part 2 §D3.3 |
| Safety 优先级 | S0 独立核 + FIFO92，续租/失租指标 | Part 4 §D8.1 |
| ModeTransition | ramp + HAL PREPARE_MODE + 状态机 | Part 2 §D3.5；Part 3 §D5.6 |
| Obs/Action Spec | 21/16 列、完整 16 关节、`sign` 一次变换 | Part 3 §D5.3/§D5.5 |
| ControlLease | 7 状态、TTL/seq/owner/scope、失租降级 | Part 1 §D2；Part 2 §D4.4 |

---

## 4. 你必须带进编码的残留问题

1. **P0：`can_exit` 在 `step` 前发布 `READY` 的竞态**（Part 2 §D3.5 的“审阅注记”）。
   - 现有测试只测“无决策/挂死”，没测“先 READY 再挂死/NaN/相位切换”。
   - 建议 V1.2：`READY` 只在 `step` 成功后发布；或增加 `last_completed_step_seq/phase_seq/fault_seq`，RT 只接受最近成功 step 的 `READY`。

2. **P1：`ExitKind` 枚举**
   - V1.1 PartA-E 的 C++ 伪代码是 `READY=0/WAIT=1/REFUSE=2`，proto 是 `EXIT_READY=1/WAIT=2/REFUSE=3`。
   - 本合并版 Part 2 已按 proto 改为 1/2/3；编码必须由 proto 生成，不能手写第二套。

3. **P1：`ModeTransitionPlan`/Q2B/B2Q phase 表未进 Schema**
   - 需要 `mode_transition_plan.schema.json` + `phases[]` + 示例；没有 plan 的 phase 必须 `DISABLED`。

4. **P1：Factory 矩阵/HAL 能力表是文档 + 测试硬编码**
   - 需要 `factory_matrix.yaml`、`hal_capabilities.yaml`；`backend_id` 白名单化。

5. **P2：Schema 语义缺口**
   - `Form=UNKNOWN` 下禁止 `SAFE_HOLD_IF_VERIFIED`；`BUILTIN` 不应带 path/SHA；`MODEL` 不允许空 tensor；`entry.predicates` 不能默认空；`asset.sha256` 需测试覆盖。

6. **P2：36 个测试是 SIL/合同**
   - `hal_contract_sil.py` 是 FakeHal；`init_and_lease_sil.py` 是独立模型；`check_doc_contracts.py` 是文本级。
   - 不要对外说“36 项系统测试通过”。

---

## 5. 使用边界

- **可编码**：本版足以拆 `ExitDecision`、FactoryRegistry、proto/schema 生成、ControlLease、ModeTransition、HAL 合同代理、SIL 注入任务。
- **不可上机**：Collie 拓扑、双足支撑、HAL 独立 watchdog、Q2B/B2Q 资产、RT/Safety/HAL WCET、功能安全适用性、密钥管理均未验证。
- **冲突裁决**：字段/合同冲突时，以 `proto`、`schemas`、`HAL_CONTRACT` 为准；本版是阅读版，不是字段唯一源。
