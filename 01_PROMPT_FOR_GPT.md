# 01 Prompt for GPT（直接复制到网页版 GPT）

> 使用方式：把本文件**从“任务”一节开始**整段复制给 GPT。仓库是公开的，GPT 需要开启联网/浏览能力。若某个链接打不开，让它改读同目录的 `README.md`，或让用户粘贴对应文件。

---

## 任务

你是一名资深机器人运控软件架构师（15 年以上，做过四足/轮足/双足、硬实时控制、功能安全、量产交付）。现在为 **Collie 轮足机器人**设计 **运控（MC）服务**的完整软件架构，核心是 **Runner 框架**。

这不是文档润色，也不是写一段原则性建议。你要产出一份**可评审、可落地、可验收**的架构设计：开发能据此拆模块写代码，测试能据此设计回放与故障注入，运控能据此交付策略资产，产品/项目能据此判断范围、成本与风险。

**设计自由**：你可以自由裁决分层、进程/线程、接口形态、数据结构、状态机、配置体系与安全机制。但每个裁决必须给出理由、替代方案、代价与切换条件；不能只给结论。

**最重要的一句话**：Collie 的 Runner 框架必须做到——**一个关节出口、一套策略契约、一条可回放的每拍链路、一条不依赖推理的安全路径**。

---

## 1. 输入仓库与阅读顺序

仓库（公开）：

**https://github.com/bgzou/collie-runner-arch-review-20261122**

先读这 5 份“元文档”，它们定义了阅读方式、证据级别与必须裁决的问题：

1. [00_READ_ME_FIRST.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/00_READ_ME_FIRST.md)
2. [02_CONTEXT_BRIEF.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/02_CONTEXT_BRIEF.md)
3. [03_EVIDENCE_MAP.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/03_EVIDENCE_MAP.md)
4. [04_OPEN_QUESTIONS.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/04_OPEN_QUESTIONS.md)
5. [05_GLOSSARY.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/05_GLOSSARY.md)

然后按顺序读**核心设计输入**（这 12 份是必读，不要跳过）：

| # | 文件 | 读什么 |
|---|---|---|
| 1 | [architecture/architecture-design.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/architecture-design.md) | 第 3 章总体架构：大脑/小脑/平台三子系统职责划分、边界判据、场景协同 |
| 2 | [runner/runner-integration-master.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/runner/runner-integration-master.md) | **当前 Runner 主文档**：边界、接口、`IRunner`/`ActionBundle`、切换、配置、验收 |
| 3 | [runner/runner-interface-and-dataflow.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/runner/runner-interface-and-dataflow.md) | 字段、tensor、obs/action 规格、golden fixture |
| 4 | [system/t1-architecture-deep-dive.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/t1-architecture-deep-dive.md) | 第 0/2/3/6/8/10 章：双板三机、频率、Runner、数据链路、安全 |
| 5 | [system/motion-control-architecture-delivery.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/motion-control-architecture-delivery.md) | **简化交付方案**：Behavior/Mode/Scope、4 RPC、Lease、线程模型 |
| 6 | [architecture/security-module-architecture.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/security-module-architecture.md) | 第 12 章安全模块：需求、失效模型、分层、接口 |
| 7 | [system/three-links-safety-switching-shaping.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/three-links-safety-switching-shaping.md) | 安全/切换/整形三条链路 |
| 8 | [system/t1-safety-design.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/t1-safety-design.md) | T1 安全 4+1：五类后果、六条异常路径、八层纵深 |
| 9 | [architecture/task-engine-and-state-machine.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/task-engine-and-state-machine.md) | 第 5 章任务调度与状态机：上游如何调用 MC |
| 10 | [evidence/interfaces/MC_INTERFACE_CATALOG.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/interfaces/MC_INTERFACE_CATALOG.md) | MC 相关 `.msg/.srv` 全量定义 |
| 11 | [evidence/configs/mc_T1.yaml](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/configs/mc_T1.yaml) + [evidence/configs/action_setting.yaml](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/configs/action_setting.yaml) + [evidence/configs/action_ruler.yaml](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/configs/action_ruler.yaml) | 真机话题/服务/速度源/执行组/切换边 |
| 12 | [evidence/model-list/action-execution-runner.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/model-list/action-execution-runner.md) + [evidence/model-list/rule-graph-stats.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/model-list/rule-graph-stats.md) | 58/62/42/34/15、52 节点/197 边 |

**HTML 对照（重要）**：第 3 章与第 5 章另有独立 HTML 渲染版——[architecture/architecture-design.html](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/architecture-design.html)、[architecture/task-engine-and-state-machine.html](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/task-engine-and-state-machine.html)。它们保留了版式、表格与图，适合确认结构；但**正文论证以对应 `.md` 为权威文本**，不要只读 HTML 而漏掉 Markdown 中的证据与注释。

**选读（需要时再打开）**：

- 需求原文：[requirements/requirements-scenarios.txt](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/requirements/requirements-scenarios.txt)
- 对外接口说明：[system/motion-external-interfaces.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/motion-external-interfaces.md)
- T1 4+1 全文：[system/t1-4plus1-architecture.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/system/t1-4plus1-architecture.md)
- T1 MC 拆解：[runner/t1-mc-decomposition.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/runner/t1-mc-decomposition.md)
- T1 硬件/OS/SDK：[reference/t1-pro-orin-rk-analysis.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/reference/t1-pro-orin-rk-analysis.md)、[reference/t1-pro-developer-sdk-analysis.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/reference/t1-pro-developer-sdk-analysis.md)
- 参考实现：[reference/quadruped-software-architecture.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/reference/quadruped-software-architecture.md)
- 安全/任务/感知的原始章节：[architecture/task-engine-and-state-machine.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/task-engine-and-state-machine.md)、[architecture/sensor-preprocessing-and-perception.md](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/architecture/sensor-preprocessing-and-perception.md)
- 图表：[evidence/diagrams/strategy-switching.png](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/diagrams/strategy-switching.png)、[evidence/diagrams/strategy-chain.png](https://github.com/bgzou/collie-runner-arch-review-20261122/blob/main/evidence/diagrams/strategy-chain.png)

如果某个 GitHub 页面打不开：改读仓库根目录的 `README.md`（有完整索引），或让用户把对应 `.md` 原文粘贴给你。**不要因为少读一份就降低交付完整度**。

---

## 2. 设计对象与边界

### 2.1 在范围内

- Collie 运控服务的**运行时架构**：Runner 契约、PolicyManager、Action/Behavior 编排、切换、观测/动作适配、推理后端、关节合成、安全出口、状态发布。
- **上下游接口**：任务引擎/App/SDK、导航/跟随/运镜/遥控、安全/系统模式、HAL/电机/IMU/状态估计。
- **配置与资产体系**：RobotDescription、RunnerManifest、ActionBundle、ObsSpec/ActionSpec、版本与校验。
- **实时与并发**：进程/线程、调度、队列、内存、WCET、降级。
- **安全**：失效模型、分层防线、安全状态机、急停/跌倒/失联/超时/NaN/越界、恢复。
- **可观测/回放/测试/验收**：日志、指标、黑匣子、golden fixture、故障注入、HIL。
- **网络安全**：信任边界、鉴权、签名、重放、审计、OTA/模型供应链。
- **落地路径**：从现有 `roboparty_deploy` / T1 参考迁移的阶段、里程碑、回滚。

### 2.2 不在范围内（但必须定义接口）

- 策略训练、奖励设计、Sim2Real 训练流程；
- 导航/路径规划/跟随/避障算法；
- 感知/VIO/SLAM/人脸/语音；
- 云端 Agent/大模型；
- 机械/电气/电机固件设计；
- App/UI 业务逻辑。

### 2.3 必须显式声明的假设

Collie 以下事实尚未冻结，你必须在文档开头列出你的假设，并给验证方法：

- 关节拓扑（腿/轮/头/臂数量与自由度）、关节顺序、零点/方向/限位；
- 双足直立是静态锁止还是动态平衡；
- 计算平台、OS、实时能力、推理后端（CPU/GPU/NPU）；
- 是否复用 `roboparty_deploy`；
- Q2B/B2Q 是否有自研权重/轨迹；
- 载荷/地形/楼梯的产品范围。

---

## 3. 你必须裁决的问题

`04_OPEN_QUESTIONS.md` 列了 14 个问题。你**不能回避**，每个都要在正文中给出决策。至少覆盖：

1. **统一抽象**：Runner 中心 vs Behavior/Mode/Scope；如何用一套最小概念表达连续、一次性、过渡、叠加、安全五类行为。
2. **进程/线程/实时部署**：单进程多线程 vs 多进程 vs 混合；控制环、安全出口、推理、服务/日志的边界；核绑定、优先级、WCET。
3. **关节拓扑与双足形态**：`RobotDescription` 如何表达；是否需要 Balance/WBC；静态锁止如何退化。
4. **过渡策略**：Q2B/B2Q 的 phase、守卫、完成判据、超时、回退；为什么不能用线性插值。
5. **叠加与所有权**：`owns_mask`、冲突检查、混合/优先级、主策略退出时的 overlay 处理。
6. **对外接口**：3 类领域接口 vs 4 个 RPC；幂等、三态、超时、背压、TTL、断流。
7. **安全架构**：安全内核 + Lease vs OutputGuard + 分层防线；谁有权切安全态；故障锁存/复位；硬件急停独立性。
8. **推理后端**：多输入/多输出、模型校验、超时、异常、预热、版本回滚。
9. **配置/资产**：schema、目录、版本、SHA、加载顺序、灰度、兼容矩阵。
10. **观测/动作规格**：ObsSpec/ActionSpec 的逐维字段；训练/部署如何共同签收；golden fixture。
11. **可观测/回放**：每拍记录什么、体积预算、黑匣子、隐私。
12. **网络安全**：STRIDE、信任边界、鉴权/签名/重放/审计/调试接口。
13. **测试/验收**：单测/回放/切换图/故障注入/HIL/场景；门槛与签收人。
14. **迁移路径**：从 `roboparty_deploy`/T1 到 Collie 的阶段、双跑、回滚。

对每个问题，至少给：**决策 / 理由 / 替代方案 / 代价 / 切换条件 / 验证方法**。

---

## 4. 交付物（必须全部完成）

### D0 执行摘要与决策表（1 页）

- 一段话说明架构；
- 12 条关键决策表：`编号 | 决策 | 理由 | 替代方案 | 代价 | 状态（建议/待定）`；
- 给非软件背景决策者的“5 分钟版”：这套架构为什么这样分层、最坏会坏在哪、还需要他们拍板什么。

### D1 架构总览

- 系统上下文图（Collie MC 与任务/导航/安全/HAL/云的关系）；
- 容器/进程图（进程、线程、IPC、共享内存、DDS/ROS 边界）；
- 模块图（API Adapter、PolicyManager、Registry、Arbiter、Snapshot、ObsBuilder、Inference、Codec、Mux、Guard、Status）；
- 部署图（计算单元、网络、存储、日志）；
- 每条连线标注：方向、协议、频率、延迟预算、失败行为。

### D2 领域模型

- 限界上下文、聚合、实体/值对象；
- `Action` / `Behavior` / `Runner` / `ActionBundle` / `Session` / `Epoch` / `Ownership` 的精确关系；
- 两到三张状态机：Action 生命周期、切换、安全状态；
- 术语表（与 `05_GLOSSARY.md` 对齐，冲突时说明）。

### D3 Runner 框架详细设计

必须给出：

- `IRunner` 的 C++ 签名（含前置/后置条件、线程安全、异常/错误码、`noexcept` 约定）；
- 生命周期状态机：`Created → Loaded → Entered → Running → Exiting → Exited → Faulted`，以及 `can_exit` 与 `enter` 的守卫；
- 类图：`IRunner`、`RlLocomotionRunner`、`TransitionRunner`、`BalanceRunner`、`ClassicalPoseRunner`、`RecoveryRunner`、`PlaybackRunner`、`OverlayRunner`；`ObservationBuilder`、`InferenceBackend`、`ActionCodec`；
- 至少 3 条时序图：①四轮行走单拍；②`QuadStop → Q2B → BipedBalance → B2Q` 切换；③急停/反馈过期抢占；
- 至少 5 个 Runner 的“接口卡”：输入参考、反馈、输出、进入/退出、失败、必交配置；
- 伪代码：`step()`、`can_exit()`、`enter()`、超时/异常处理；
- 明确：谁拥有历史缓冲、谁清空、切换时哪些状态保留/丢弃。

### D4 PolicyManager / ActionGraph / ActionBundle

- Action 注册与预加载；
- ActionGraph/TransitionGraph 的 schema、校验、非法边拒绝、全局安全出口；
- 请求仲裁：来源优先级、幂等键、排队/拒绝/抢占；
- 切换状态机与原子移交：`REQUESTED → PREPARING → WAIT_EXIT → ENTERING → TRANSITIONING → STABILIZING → RUNNING`，失败 `FAULT/SAFE`；
- `ActionBundle`：primary/overlay/owns_mask、冲突检查、组合矩阵；
- 对外阶段语义：受理/切换中/稳定/失败，`switch_ready` 的定义；
- 状态发布：`MotionStatus` 字段与频率。

### D5 每拍数据链路

- `RobotStateSnapshot`：多源时间戳、有效性、时间对齐、丢帧/倒退/NaN 处理；
- `ObservationBuilder`：块顺序、缩放、裁剪、滤波、历史帧、首帧规则、模型 tensor 绑定；
- `InferenceBackend`：多输入/多输出、名称/shape/dtype 校验、超时、异常；
- `ActionCodec`：裁剪、scale、default、gain、activation、逐关节模式；
- `JointMux`：主/叠加合成、所有权、冲突；
- `OutputGuard`：位置/速度/力矩/变化率/增益/反馈新鲜度/急停/超时/NaN，失效替代；
- **一张 10 ms 控制环时序图**：采样→快照→观测→推理→解码→合成→限幅→发布，标每段预算与超时策略；
- 说明 100 Hz 推理与 200 Hz 关节发布如何解耦，过期输出如何处理；
- 数据所有权与零拷贝边界（谁分配、谁释放、是否实时安全）。

### D6 上下游接口

给一张**字段级接口表**，至少覆盖：

| 方向 | 接口 | 传输 | 频率/时效 | 关键字段 | 失败语义 |
|---|---|---|---|---|---|
| 任务→MC | ActionRequest / SetBehavior | RPC | 事件 | request_id, action_id, params, deadline, preempt | 拒绝/排队/超时 |
| 导航→MC | BodyVelocityRef / SetVelocity | Topic/RPC | 10–50 Hz + TTL | source, seq, stamp, vx, vy, wz, frame | 过期归零/降级 |
| 安全→MC | SafetyEvent / SetSafety | RPC/事件 | 异步 | kind, severity, latched | 立即抢占/锁存 |
| MC→HAL | JointTargetArray | Topic/共享内存 | 100–200 Hz | name, mode, q, dq, tau, kp, kd, enabled | 拒收/故障 |
| HAL→MC | JointStateArray / IMU | Topic | 200–1000 Hz | name, q, dq, tau, temp, valid, stamp | 过期/缺失 |
| MC→任务/HMI | MotionStatus / Events | Topic | 50 Hz/事件 | state, phase, switch_ready, fault | 状态单调 |

并给出：

- 领域 IDL（C++ struct）与 ROS msg 的映射；
- 错误码规范（分段：参数/状态/安全/资源/内部）；
- 幂等、重试、背压、限流、断流；
- 上游来源优先级与权限矩阵；
- 时间基准与坐标约定（`frame_id`、单位、符号）。

### D7 安全设计

- 安全目标与危害清单（至少 8 类：跌倒、失控、超速、越界、过流/过温、通信断流、模型异常、误注入）；
- FMEA 表：失效模式 → 检测 → 反应 → 残余风险；
- 分层防线：硬件急停 → HAL 保护 → OutputGuard → 安全内核 → Runner 自身守卫 → 系统模式；
- 安全状态机：`NORMAL / DEGRADED / SAFE_HOLD / DAMPING / ESTOP / RECOVERY`，迁移条件、锁存、复位；
- 8 个故障场景的逐步走查（含“推理挂死”“反馈过期”“NaN”“切换中急停”“双足失稳”“通信断流”“越权请求”“模型加载失败”）；
- 与功能安全/认证的关系（如适用），哪些是 SIL/PL 诉求，哪些只是工程防线；
- 安全出口的独立性证明：为什么急停不依赖 ONNX、不依赖任务引擎、不依赖日志线程。

### D8 并发与实时性

- 进程/线程表：名称、职责、周期、优先级、核绑定、栈/队列、超时；
- 同步原语：锁/无锁队列/原子/条件变量；哪些路径禁止锁/禁止动态分配/禁止阻塞；
- 内存：预分配、池、最大尺寸、OOM 策略；
- WCET 预算：每段最坏耗时、总预算、抖动、超期检测与降级；
- 启动/关闭顺序：HAL → 状态估计 → MC → 任务 → 导航；关闭反向；
- 过载策略：丢帧/降频/拒绝新请求/进安全态；
- 与 ROS/DDS 执行器的关系（回调线程 vs 控制线程）。

### D9 配置与资产

- `RobotDescription` schema；
- `RunnerManifest` schema（YAML + JSON Schema），字段含：action、runner 类、模型/轨迹路径与 SHA、tensor IO、ObsSpec/ActionSpec、增益、所有权、周期、进入/退出守卫、失败目标；
- `ActionBundle` schema；
- 系统级配置：`velocity_sources.yaml`、`action_graph.yaml`、`safety_limits.yaml`；
- 目录规范、加载顺序、校验器、错误处理；
- 版本与兼容矩阵、灰度、回滚、现场升级；
- 一份完整示例（一个 Action 的 manifest + spec 片段）。

### D10 可观测性与运维

- 日志：分级、字段、采样、落盘、轮转、体积预算；
- 指标：每拍耗时、推理耗时、超期、队列深度、切换次数/时长、故障码、CPU/内存；
- Trace：`request_id`/`action_epoch` 贯穿；
- 黑匣子：故障前后 N 秒的输入/输出/状态；
- 离线回放：数据格式、工具链、与 golden fixture 的关系；
- 告警与 dashboard；隐私与数据安全。

### D11 测试与验收

- 测试金字塔：单元（codec/guard/manifest）、回放（golden）、切换图、故障注入、HIL、场景；
- 测试矩阵：模型 × Action × 故障 × 平台；
- 每条验收的通过门槛与证据；
- 故障注入清单：超时、NaN、过期、越界、丢帧、急停、模型加载失败、通信断流、切换中故障；
- 真机开放边的安全试验与签收；
- 回归策略与 CI。

### D12 网络安全

- 信任边界与数据流；
- STRIDE 威胁表；
- 鉴权/授权/来源白名单；
- 请求签名/防重放/限速；
- 模型与配置签名、供应链；
- 调试接口/日志脱敏；
- 审计与入侵检测；
- 与功能安全的关系（网络安全事件如何触发安全态）。

### D13 ADR 清单

至少 12 条，每条：`编号 | 背景 | 选项 | 决策 | 后果 | 状态`。至少覆盖：统一抽象、进程模型、关节出口、切换状态机、安全内核、推理后端、配置体系、观测规格、回放、网络安全、迁移路径、测试策略。

### D14 风险与未决问题

表：`风险/未决 | 概率 | 影响 | 缓解 | 责任方 | 验证方法 | 截止`。至少 10 条。

### D15 实施路线图

- 阶段划分（如 P0 骨架/影子模式、P1 单 Action、P2 切换、P3 安全联锁、P4 多形态）；
- 每阶段：目标、交付物、依赖、退出条件、风险门；
- 人力/工期粗估（按角色，不要求精确）；
- 与现有 `roboparty_deploy` 的代码边界与迁移步骤；
- 回滚方案。

### D16 评审 checklist（给非软件背景决策者）

20 个“是/否”问题，例如：

- 是否只有一个模块能写关节？
- 急停是否不依赖推理/任务/日志？
- 切换失败是否有明确回退？
- 反馈过期是否一定进安全态？
- 新策略上线是否只需配置+资产，不改代码？
- 每个 Action 是否有 golden fixture？
- 是否能回放故障现场？
- 模型/配置是否能追溯版本？
- 越权请求是否被拒绝？
- 是否有 WCET 预算与超期策略？

每项给“不过的风险”。

---

## 5. 质量要求与评分 rubric

总分 100，**低于 85 分先自行补全再输出**：

| 维度 | 分值 | 判定 |
|---|---|---|
| 完整性（D0–D16 全覆盖） | 15 | 缺一项扣 2 分 |
| 决策明确（每个争议有选择/理由/替代） | 15 | 出现“视情况而定”扣 3 分/处 |
| 接口可实施（字段/单位/时效/失败语义） | 15 | 缺单位或失败语义扣 2 分/处 |
| 安全（失效模型/分层/状态机/独立性） | 15 | 只写“加看门狗”扣 10 分 |
| 实时与并发（线程/预算/过载） | 10 | 无 WCET/超期策略扣 5 分 |
| 可测试（golden/故障注入/门槛） | 10 | 无验收门槛扣 5 分 |
| 可运维（日志/指标/回放） | 5 | — |
| 一致性（术语/图/表/接口不矛盾） | 5 | 自相矛盾扣 2 分/处 |
| 证据使用（引用 E/R/I/P/X，区分事实/假设） | 5 | 把 T1 数值当 Collie 事实扣 3 分/处 |
| 可读性（非软件背景能懂） | 5 | 只有术语堆砌扣 3 分 |

在最后输出一张自评分表，并列出你主动补全的 3 个最大缺口。

---

## 6. 输出方式（重要）

网页版可能截断，请**分 6 部分**输出，每部分自成完整章节：

- **Part 1**：D0 执行摘要 + D1 架构总览 + D2 领域模型 + 完整目录；
- **Part 2**：D3 Runner 框架 + D4 PolicyManager/ActionBundle；
- **Part 3**：D5 数据链路 + D6 上下游接口；
- **Part 4**：D7 安全 + D8 并发/实时；
- **Part 5**：D9 配置/资产 + D10 可观测 + D11 测试 + D12 网络安全；
- **Part 6**：D13 ADR + D14 风险 + D15 路线图 + D16 checklist + 自评分。

要求：

1. **不要只给目录/提纲**；每一节都要有实质内容、接口、表、图或伪代码。
2. 用 **Mermaid** 画图（flowchart / sequenceDiagram / stateDiagram-v2 / classDiagram），至少 12 张。
3. 用 **C++ 伪代码**给关键接口与 `step()`，不要只写自然语言。
4. 表格优先于长段落；每个表有标题与列含义。
5. 首次出现的术语用一句话解释，并与 `05_GLOSSARY.md` 一致。
6. 事实标 `【事实 E#】`，假设标 `【假设】`，建议标 `【建议】`，待定标 `【待定】`。
7. 不要复制 T1 的 Action 数字、关节顺序、模型尺度、阈值；只复用结构与约束。
8. 不要用“高内聚低耦合”“视业务而定”“后续再细化”作为结论；给默认方案。
9. 每部分结尾写：`本部分完成度：xx% / 待补：...`。

**现在开始 Part 1。不要等我确认，不要先提问；信息不足时做最合理假设并标注。**
