# 评审意见：GPT《Collie MC V1.1 定点修订》交付包

**评审对象**：`Collie_MC_V1.1_定点修订_交付包.zip`（2026-11-22，V1.1-Review）
**评审基线**：V1.0 六部分 + 上一轮 `REVIEW.md` + `PROMPT_FOR_GPT_V1.1_REVISION.md`
**评审结论**：**从“可评审”明显推进到“可拆任务编码”，是一份高质量的定点修订；但仍有一个 P0 级时序漏洞和几处“文档有、机器不可校验”的缺口，不能据此上机。**

**综合评分**：**91/100**（V1.0 为 87；GPT 自评 86，反而偏保守）
- 设计质量：**91**
- 实现准备度：**85–88**
- 实机安全批准：**不适用**

---

## 1. 上轮 P0/P1 的闭环情况

| 上轮问题 | V1.1 交付 | 判定 |
|---|---|---|
| **P0-1** `can_exit` 执行位置/RT 非阻塞 | 选 B：Worker 预计算 `SealedExitDecision`，RT 只读 mailbox；补 `snapshot_seq/valid_until/refuse latch`；新增时序与 SIL | **部分闭环**：合同方向正确，但“在 `step` 前发布 READY”留下新竞态（见 §2.1） |
| **P0-2** 启动 `SAFE_HOLD` 与未知支撑矛盾 | 新增 `INIT/UNKNOWN`；未知支撑默认 HAL_SAFE/disabled；禁 Q2B/B2Q/Balance/Recovery/Overlay；补复位路径 | **已修**，状态机与启动门控完整 |
| **P0-3** HAL 合同缺失 | 新增 `HAL_CONTRACT.md`（23 KB）：writer token/OS 身份、Epoch 两阶段、PREPARE_MODE、ack/reject/watchdog、双写注入、HAL-01..08 | **已修**，是这次最有价值的增量；硬件部分仍待验证 |
| **P0-4** 6 处 schema/命名不一致 | `SCHEMA_CANON.md` + `proto` + JSON Schema；统一 `nodes`、`timeout_ms/deadline_ns`、`MotionStatus` 32 字段、`sign`、双层资产状态、128 MiB | **基本已修**；仍有一处 `ExitKind` 枚举值不一致（见 §2.2） |
| **P1-1** Runner 分类维度混 | `ExecutionKind × BehaviorRole` 二维矩阵 + 唯一工厂 | **已修**，但矩阵仍是文档 + 测试硬编码，未机器化（§2.4） |
| **P1-2** Safety 优先级/失租 | Safety 独立核 S0 + FIFO92；补续租/失租/误停指标 | **已修**，指标定义清楚 |
| **P1-3** 控制模式无 bump-less | `ModeTransitionEngine` + ramp + HAL PREPARE_MODE + 状态机 | **设计已修**，但 `ModeTransitionPlan` 没进 Manifest/Schema（§2.3） |
| **P1-4** Obs/Action spec 字段不全 | 21/16 列、`transform/history_order/include_current/missing_policy_ref`、`sign` 公式、完整 16 关节 CSV | **已修**，是本轮最扎实的“可机器校验”部分 |
| **P1-5** ControlLease 无生命周期 | 7 状态机、TTL/seq/owner/scope、失租降级、准入四许可 | **已修**，与 Session/SafetyLease 的边界清楚 |

**结论**：上一轮 9 个问题，**7 个完全闭环、2 个方向正确但有残留**（P0-1 的竞态、P0-4 的枚举值）。这不是“只改文字”，而是真的补了 proto、schema、examples、测试与 HAL 合同。

---

## 2. 仍然关键的问题

### 2.1 P0：`can_exit` 在 `step` 前发布 `READY`，存在“旧 Runner 已故障/进入不可中断相位，RT 仍提交”的竞态

V1.1 的 B-P0-1 明确写：

> `can_exit` 只由 Worker 本实例线程每 10 ms tick **在 `step` 前**计算并写入预分配 `SealedExitDecision` 邮箱；`mc_rt` 5 ms tick 只做读取、校验和决策。

代码顺序也是：

```cpp
d = runner_.can_exit(...);          // 先算退出
publish_sealed_exit(...);           // 先发布 READY
(void)runner_.step(in, out);        // 再跑 step（可能改 phase / fault / 挂死）
```

这带来三个具体风险：

1. **相位竞态**：`step()` 可能把 Runner 从可退出相位推进到不可中断相位（例如 Q2B `TRANSFER`），但 RT 已经拿到上一步的 `READY`，在 10 ms 有效期内提交新 Epoch。
2. **故障竞态**：`step()` 可能输出 NaN、检测到支撑失效或内部 fault；但 `READY` 已经先发布，RT 可能在故障被下一拍看见之前完成提交。
3. **挂死窗口**：Worker 在发布 `READY` 后卡在 `step()`，RT 仍可在 `valid_until_ns`（10 ms）内使用这个 `READY`；现有 `test_exit_worker_hang_50ms_rt_not_block` 只测“没有决策（None）”，**没有测“先 READY 再挂死”**。

**建议修法（二选一）**：

- **推荐**：`READY` 只在 `step()` 成功返回后发布；`can_exit` 在 `step` 前只允许发布 `WAIT/REFUSE`（作为“step 挂死时也不误提交”的保险）。若希望保留“挂死也能判退出”，则 `SealedExitDecision` 增加 `last_completed_step_seq`/`runner_fault_seq`/`phase_seq`，RT 必须确认该决策来自“最近一次成功 step”，且 `phase_seq` 与当前 Runner 状态一致；`step` 进行中/挂死时强制 `WAIT`。
- 或者把 `can_exit` 做成 RT 本地纯函数（上轮的方案 A），但需要把相位/退出判据镜像到 RT；成本更高。

**验收必须新增**：`READY` 已发布 → `step` 挂死 50 ms；`READY` 已发布 → `step` 返回 NaN/fault；`READY` 已发布 → `step` 进入不可中断 phase。三种场景都要求 RT **0 次提交**、0 次旧 Epoch 接受。

这是目前唯一我认为会直接导致“切换提交错”的 P0 级残留。

### 2.2 P1：`ExitKind` 的 proto 枚举值与 C++ 枚举值不一致

- `proto/collie_mc_v11.proto`：

```proto
enum ExitKind { EXIT_UNSPECIFIED = 0; EXIT_READY = 1; EXIT_WAIT = 2; EXIT_REFUSE = 3; }
```

- `PartA-E` 的 C++：

```cpp
enum class ExitKind : uint8_t { READY, WAIT, REFUSE };
```

如果 C++ 由 proto 生成，`READY` 应为 `1`；但这段伪代码的 `READY` 是 `0`。这类“文档伪代码 vs proto 生成”不一致，正是上一轮要求消除的漂移。建议：**所有 C++ 片段不再手写枚举值，直接写 `ExitKind::EXIT_READY` 或由生成头文件引入**；并在 `check_examples.py` 加一条“proto enum 值与 C++ 伪代码一致”的检查（或删除伪代码枚举，改为引用 proto）。

### 2.3 P1：`ModeTransitionPlan` 与 Q2B/B2Q 的 phase 表没有进入 Manifest/Schema

`PartA-E` 定义了 `ModeTransitionPlan`、每个 phase 的 `mode_before/mode_after/mode_transition_plan_ref`，但：

- `runner_manifest.schema.json` 没有 `mode_transition_plan`/`phases` 字段；
- 没有 `mode_transition_plan.schema.json`；
- `examples/` 没有一份 `ModeTransitionPlan` 示例；
- `check_examples.py` 没有校验“phase 引用的 mode plan 存在且已批准”。

也就是说，**概念写清楚了，但配置无法加载/校验**。建议至少补：

```text
schemas/mode_transition_plan.schema.json
examples/demo16_mode_transition_plan.yaml
```

并在 `RunnerManifest` 增加 `phases[]` 或 `transition_plan_refs[]`；没有 plan 的 phase 必须 `DISABLED`。否则 Q2B/B2Q 的“可编码”仍然只是文档。

### 2.4 P1：HAL 能力表、Factory 矩阵仍是“文档 + 测试硬编码”

- `RunnerFactoryRegistry` 的 `(ExecutionKind, BehaviorRole) → class_id` 矩阵只存在于 `PartA-E` 表格和 `check_examples.py` 的 `factory` 字典里；没有 `factory_matrix.yaml`/schema。
- HAL 支持哪些 `JointMode`、每关节 `kp/kd` 范围、是否有独立 watchdog，只在 `HAL_CONTRACT.md` §8 以自然语言列出；没有 `hal_capabilities.yaml`/schema。
- `runner.backend_id` 在 JSON Schema 里只是 `string`，没有白名单。

这会导致：文档改了、测试没改；或者实现者按文档写，CI 按硬编码测。建议把两者都机器化，并让 `RunnerManifest` 的 `backend_id` 引用 `hal_capabilities` 的白名单。

### 2.5 P2：Schema 语义仍有“结构合法但语义危险”的缺口

- `failure_target` 允许 `SAFE_HOLD_IF_VERIFIED`，但 `Form=UNKNOWN` 时禁止 SAFE_HOLD；JSON Schema 无法表达，需 `mcctl validate` 的跨字段规则。
- `asset.kind=BUILTIN` 时 schema 不禁止带 `path/sha256`；`SCHEMA_CANON` 说内置无路径，但 schema 没约束。
- `tensor_io.inputs/outputs` 没有 `minItems`；`MODEL` 类型可以空输入/输出，语义校验应拒绝。
- `entry.predicates` 允许空数组；某些 Action 可能允许空进入守卫，但应显式声明，不能默认。
- `check_examples.py` 没有校验 `asset.sha256`（只校了 obs/action/golden）；本次 demo 的 asset hash 实际是对的，但测试没覆盖。

这些不是架构级问题，但会让“schema 通过 ≠ 可加载”再次出现。建议在 `mcctl validate` 中补跨字段规则，并给每条规则一个负例测试。

### 2.6 P2：36/36 PASS 的含金量要正确理解

我实际运行了四个测试：

- `check_examples.py` **12/12 PASS**
- `hal_contract_sil.py` **9/9 PASS**
- `init_and_lease_sil.py` **11/11 PASS**
- `check_doc_contracts.py` **4/4 PASS**

合计 **36/36**，与 README 一致。但要指出：

- `hal_contract_sil.py` 是 **FakeHal**，不是实际 HAL 实现；它证明的是“合同分支语义”，不是设备看门狗。
- `init_and_lease_sil.py` 是 **SafetyGate/LeaseArbiter 的独立模型**，不是生产 C++。
- `check_examples.py` 里 `test_unknown_form_never_hold_or_action` 基本是局部布尔断言；`test_mode_ramp...` 测的是测试内公式，不是生产 `ModeTransitionEngine`。
- `check_doc_contracts.py` 是文本级一致性，不是编译器/生成器。

README 已经写了“纯软件合同/一致性测试”，**这个边界是诚实的**；但对外汇报时不要把它说成“36 项系统测试通过”。建议在结论里加一句“约 20 项是状态机/SIL 模型测试、12 项是 schema/样例与合同检查、4 项是文档一致性”。

### 2.7 P2：这是“变更单”，不是完整 V1.1 文档

`PartA-E` 是替换稿，按 A.1 的索引合并到 V1.0。它没有输出完整 V1.1 D0–D16。优点是避免重复、便于评审；代价是：

- 读者必须同时打开 V1.0 + V1.1 + SCHEMA_CANON + HAL_CONTRACT；
- “当前 V1.1 全文”不存在，容易在合并时漏改；
- 自动化文档检查只覆盖 PartA-E/SCHEMA_CANON，不覆盖合并后的全文。

建议下一步生成一份 **`Collie_MC_V1.1_Full_D0-D16.md`**（V1.0 + 替换文本合并版），并跑一遍全文章节/链接/字段一致性检查。否则“V1.1 是当前基线”在工程上不成立。

---

## 3. 各部分质量

| 文件 | 评价 | 分数 |
|---|---|---:|
| `PartA-E` 主修订稿 | 9 项都有“问题/决策/替代/替换文本/验收”；决策明确，替换文本可直接用 | 92 |
| `HAL_CONTRACT.md` | 本轮最大增量：writer token、Epoch 两阶段、PREPARE_MODE、ack/reject、watchdog、双写注入、HAL-01..08；工程味很足 | 93 |
| `SCHEMA_CANON.md` | 字段/单位/错误/容量/双层状态统一，能作为生成源；仍有少量语义校验未落 | 91 |
| `proto/collie_mc_v11.proto` | 结构清楚，覆盖核心消息；`ExitKind` 枚举值与 C++ 伪代码不一致 | 88 |
| `schemas/*.json` | JSON Schema 2020-12 结构完整；跨字段语义需 `mcctl` 补 | 89 |
| `examples/*` | 16 关节完整、hash 正确、CANDIDATE/非物理；asset hash 未被测试覆盖 | 90 |
| `tests/*` | 36 个 SIL/合同测试，方向正确；部分测试是局部断言/Fake 模型 | 84 |

---

## 4. 评分

| 维度 | 满分 | V1.0 | V1.1 | 说明 |
|---|---:|---:|---:|---|
| 完整性 D0–D16 | 15 | 15 | 14 | 变更单覆盖全部 P0/P1，但不是完整全文 |
| 决策明确 | 15 | 13 | 14 | 9 项都有默认选择；硬件项标待定 |
| 接口可实施 | 15 | 12 | 14 | proto/schema/字段时效强；mode plan/HAL capability 未机器化 |
| 安全 | 15 | 13 | 14 | INIT/HAL/Lease 闭环到软件；电气/失稳未验证 |
| 实时与并发 | 10 | 8 | 8 | 5/10/30/15ms 合同清楚；pre-step READY 竞态扣分 |
| 可测试 | 10 | 9 | 9 | 36 个 SIL；真实 HIL/WCET 未做 |
| 可运维 | 5 | 5 | 4 | 黑匣子/指标/HAL 观测点明确；数据规模待测 |
| 一致性 | 5 | 3 | 4 | 6 处旧冲突已修；`ExitKind` 等新不一致 |
| 证据使用 | 5 | 4 | 5 | T1 只作参考，16 关节明示非 Collie |
| 可读性 | 5 | 5 | 5 | 变更索引/验收/责任清楚 |
| **总分** | **100** | **87** | **91** | 设计质量；实现准备度 85–88 |

> GPT 自评 86 比我的 91 更保守，这是好事；差异主要来自“我把 proto/schema/HAL 合同视为真实增量”，而 GPT 对未上机证据扣得更重。两者都同意：**不能上机**。

---

## 5. 下一步建议（按优先级）

1. **P0**：修 `can_exit` 的 pre-step READY 竞态；新增“READY 已发布 → step 挂死/NaN/进入不可中断 phase”三类测试，要求 RT 0 次提交。
2. **P1**：统一 `ExitKind` 枚举（proto 为准，删除手写 C++ 值），并在 CI 检查“proto enum ↔ 生成头文件”一致。
3. **P1**：补 `mode_transition_plan.schema.json` + `phases` 字段 + 示例；没有 plan 的 phase 必须 DISABLED。
4. **P1**：补 `factory_matrix.yaml`、`hal_capabilities.yaml` 及 schema；`backend_id` 白名单化。
5. **P2**：补 `mcctl` 跨字段语义校验（SAFE_HOLD under UNKNOWN、BUILTIN 路径、空 tensor、空 predicates、asset hash）。
6. **P2**：生成完整 `V1.1_Full_D0-D16.md`，合并 V1.0 + 替换文本，作为唯一当前基线。
7. **P2**：把 36 个 SIL 分成“状态机模型 / schema 样例 / 文档一致性”三类汇报，避免被误解为系统测试。

---

## 6. 结论

**V1.1 是一次成功的定点修订**：它没有重写架构，而是把上一轮最影响编码的 9 个洞补成了“合同 + proto + schema + 示例 + SIL 测试”。`HAL_CONTRACT`、`SCHEMA_CANON`、16 关节完整示例是实打实的增量。

**可以开始编码，但不能上机。** 编码前先修掉 `can_exit` 的 pre-step READY 竞态——这是目前唯一会直接导致“切换提交错”的 P0；其余是“机器可校验性”和“合并全文”的工程完善。

**建议给 GPT 的下一轮**：只做 V1.2 的 P0/P1 小修（pre-step 竞态、ExitKind、mode plan schema、factory/HAL capability schema），不要再扩写架构。
