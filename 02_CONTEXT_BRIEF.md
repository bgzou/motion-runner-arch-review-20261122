# 02 Context Brief（给 GPT 的项目背景）

> 本文件是**二手综合**，用于让读者在 15 分钟内进入状态。事实以 `03_EVIDENCE_MAP.md` 指向的原始文件为准；本文件与原始文件冲突时，以原始文件为准。

## 1. 我们在设计什么

为 **Collie 轮足机器人**设计 **运控（Motion Control, MC）服务**的软件架构，核心是 **Runner 框架**：

- **Runner**：一个可独立加载、按固定节拍输出关节目标的策略执行单元。它可以是 RL/ONNX 策略、经典控制律、播放器、过渡策略、恢复策略或局部叠加动作。
- **Runner 框架**：Runner 的契约、生命周期、管理器、切换、数据链路、配置、安全与验收体系。
- **不是**：训练框架、导航/感知算法、云端 Agent、机械/电气设计。但必须定义与它们的接口。

Collie 的产品形态是**四足轮式 + 可直立双足**（具体关节拓扑、头/臂自由度仍未冻结）。T1 Pro 是主要对标对象，但**不能直接复用其 Action 编号、关节顺序、模型尺度、阈值**。

## 2. 为什么参考 T1 Pro

T1 Pro 是已量产的轮足可变形态机器人，其运控是**单进程 `mc` + 多 Runner `.so` + ONNX Runtime** 的成熟实现。可从真机 dump 中直接核对的证据包括：

| 事实 | 证据 |
|---|---|
| 双板：RK3576 运控板 + Orin 感知板 | 真机进程表、部署配置 |
| `mc` 单进程，约 36 线程（3 实时 + 33 普通） | 真机日志/进程表 |
| `RunnerBase` 生命周期钩子：`Configure/PreInit/Init/Trig/Run/Pause/Resume/Shutdown/EnterCheck/ExitCheck/PreRunOnce/AfterExit` | `libmc_common_runner.so` 的 `.dynsym` |
| `ActionManager` + `RunnerFactory::Load` + `TransitionTask/ResidentTask` | `libmc_manager_action.so` 符号 |
| 每个 Runner `.so` 导出 `CreateRunner/DestroyRunner` | 具体 Runner 库符号 |
| `RunnerContext` + `RunnerDataBoard` 传递动作上下文与数据槽 | `libmc_common_context.so` 符号 |
| 58 动作 / 62 执行组 / 42 RL 条目 / 34 份现役权重 / 15 经典控制 | `运控模型库/清单/` |
| 换乘图 52 节点 / 197 边 / skip 24 / 全局出口 3 | `清单/规则图-统计.md` |
| 典型 Runner 周期 10 ms；关节命令发布 ≈196 Hz；状态 50 Hz；PD/CAN 1 kHz | 配置与实测日志 |
| 7 个速度源，优先级 70–100，TTL 1000 ms | `mc_T1.yaml` |
| 11 个 MC 对外 RPC（动作/播放/预设动作/输入源/运行模型/录制） | `mc_T1.yaml` + `aimdk_msgs` |
| Action 配置：`action_setting.yaml`（Action→执行组→runner/cfg/period/priority）、`action_ruler.yaml`（合法边） | 真机配置 |
| ONNX 常见双输入：`observations[1,N]` + `observation_history[1,N*10]` | ONNX 图 + `rl/*.yaml` |

**能从二进制确认的**：类名、生命周期方法、工厂装载关系、部分数据类型。
**不能确认的**：完整 `RunnerContext` 字段、虚函数语义、每拍时序、数据所有权、C++ ABI 兼容性。不要把这些当成已知事实。

## 3. 当前 Collie 设计基线（两份文档，存在张力）

### 3.1 Runner 中心方案（`runner/runner-integration-master.md`）

核心概念：

- **一个关节出口**：`JointMux → OutputGuard → HAL`，任务/导航/安全不能绕过。
- **三类上游接口**：离散 `ActionRequest`、连续 `BodyVelocityRef`、局部 `OverlayRequest`；`SafetyEvent` 异步抢占。
- **三层静态输入 + 一个每拍输入**：
  - `RobotDescription`（关节/限位/零点/传动/外参）
  - `RunnerManifest`（Action、模型、tensor、obs/action 规格、增益、所有权、周期、守卫）
  - `ActionBundle`（primary + overlays + `owns_mask`）
  - `StepInput`（`RobotStateSnapshot` + `MotionReference` + `TransitionContext`）
- **`IRunner`**：`load / enter / can_exit / step / exit / status`。
- **模块**：`MotionApiAdapter`、`PolicyManager`、`ActionRegistry/TransitionGraph`、`VelocityArbiter`、`StateSnapshot`、`ObservationBuilder`、`InferenceBackend`、`ActionCodec`、`JointOwnershipMux`、`OutputGuard`、`MotionStatusPublisher`。
- **切换状态机**：`REQUESTED → PREPARING → WAIT_EXIT → ENTERING → TRANSITIONING → STABILIZING → RUNNING`，失败 `FAULT/SAFE`。
- **配置分层**：系统级（`velocity_sources.yaml`、`action_graph.yaml`、`safety_limits.yaml`）+ Action 级（bundle/manifest）+ 策略级（`ObsSpec.csv`/`ActionSpec.csv`）。

### 3.2 简化交付方案（`system/motion-control-architecture-delivery.md`）

核心概念：

- **只有两种行为**：`CONTINUOUS` / `ONE_SHOT`；**三个作用域**：`ALL / LEGS / UPPER`。
- **4 个 RPC**：`SetVelocity`、`SetBehavior`、`GetState`、`SetSafety`；2 个流：State 50 Hz、Events。
- **3 条实时线程 + 2 条普通线程**（相对 T1 的 36 线程）。
- **Lease（许可）**：安全内核发给控制环的“可以输出”凭证，50 ms 有效。
- **1 个安全内核 + 阶梯降级**；1 种 `.mref` 轨迹格式。

### 3.3 张力点（GPT 必须裁决）

| 问题 | Runner 中心 | 简化交付 |
|---|---|---|
| Action 的表达 | `ActionBundle`（primary + overlay + ownership） | `Behavior + Scope`（同域互斥、跨域并行） |
| 过渡策略 | 独立 `TransitionRunner`，phase 驱动 | `ONE_SHOT` + `return_to` |
| 叠加 | `OverlayRunner` + `owns_mask` + 冲突检查 | `Scope=UPPER` 与 `LEGS` 并行 |
| 对外 RPC 数 | 三类领域接口 + 适配器 | 4 个 RPC |
| 复杂度 | 接近 T1，表达力强 | 概念少，但可能盖不住过渡/叠加/故障 |

**要求**：不要简单二选一后忽略另一份；给出统一模型，说明如何用一套最小概念同时表达连续、一次性、过渡、叠加、安全五类行为，并给出迁移/裁剪路径。

## 4. 已识别的关键工程约束

1. **单一关节写入者**：同一关节同一时刻只能有一个主 Runner；叠加必须显式 `owns_mask` 并做冲突检查。
2. **安全独立于推理**：急停、反馈过期、NaN/Inf、越界、推理超时，必须在不依赖 ONNX 返回的情况下进入安全输出。
3. **反馈时效**：各传感器独立时间戳；过期/倒退/缺字段/NaN 必须故障化，不能用全零代替。
4. **命令时效**：`step()` 有确定截止时间；过期输出不能沿用为新命令；速度源有 TTL，断流归零。
5. **切换原子性**：移交电机写入权是原子步骤；旧 Runner 的 `can_exit` 只表示可交出，目标 Runner 仍须通过 `enter` 守卫。
6. **加载期拒绝**：关节拓扑、模型 hash、tensor 名称/shape/dtype、obs 配方、输出模式不匹配，拒绝启动/拒绝开放 Action。
7. **配置不可散落**：系统级配置不得复制进每个 Runner；一个 Action 的完整资产必须可版本化、可校验。
8. **可回放**：每拍输入、tensor、原始输出、解码后目标、限幅/故障原因都要能记录并离线复现。

## 5. 当前未冻结的 Collie 事实（必须标假设）

| 项 | 现状 | 对设计的影响 |
|---|---|---|
| 关节拓扑（腿/轮/头/臂数量与自由度） | 未冻结；T1 是 14 关节 | `RobotDescription`、`owns_mask`、控制模式、HAL 接口 |
| 双足直立是静态锁止还是动态平衡 | 需求表述冲突 | 是否需要 `BalanceRunner`、WBC、后轮接触判据 |
| Q2B/B2Q 是否有自研权重/轨迹 | 未确认 | `TransitionRunner` 的 phase、守卫、回退 |
| 头/臂是否与平衡争用关节 | 未确认 | 叠加接口或重训练 |
| 载荷/地形/楼梯 | 未验证 | 策略域、限速、验收门槛 |
| 计算平台与 OS | 未冻结（T1 为 RK3576 + Linux/RT） | 进程/线程、实时性、推理后端 |
| 是否复用 `roboparty_deploy` | 候选 | 迁移成本、代码边界 |

## 6. 读者应产出的东西

不是“文档润色”，而是一份**可评审、可落地、可验收**的 Runner 框架软件架构设计：

- 能在评审会上让运控/软件/测试/产品各自找到自己的接口与责任；
- 能让开发据此拆任务、排期、写代码；
- 能让测试据此设计回放、故障注入与 HIL；
- 能让非软件背景的决策者看懂“为什么这样分层、代价是什么、还缺什么”。

## 7. 事实、假设、建议的写法

全文统一使用：

- **【事实】**：有原始文件/符号/配置可直接核对；
- **【假设】**：Collie 尚未冻结，设计中先按此假设，需标注验证方法；
- **【建议】**：架构选择，需评审拍板；
- **【待定】**：需要实验/标定/产品输入，不能在本轮闭环。

不要用模糊的“视情况而定”结束一个决策；给默认方案、替代方案与切换条件。
