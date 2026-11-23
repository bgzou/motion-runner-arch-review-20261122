# Collie 运控服务软件架构 V1.3 50 Hz 频率修订版（D0–D16）

> **版本**：V1.3 50 Hz 频率修订版　**日期**：2026-11-23　**状态**：V1.1 架构 + V1.2 讲解 + 50 Hz 频率决策；非实机安全批准。

> **频率基线**：训练侧 `dt=0.02`（50 Hz）。Collie 首版：**50 Hz 策略 / 50 Hz Worker / 200 Hz RT / ZOH 发布 / 15/20 ms 预算 / 25 ms TTL**。完整决策见 [ADR-25](../ADR-25_策略频率50Hz.md)。
>
> **T1 对照**：T1 部署默认 100 Hz，`BIPED_NPZ_MIMIC` 例外 50 Hz；T1 的 100 Hz 证据保留，不改写为 Collie 事实。

> **来源**：V1.0 六部分（`../../20261122_6parts/`）+ V1.1 定点修订（`../../20261122_v1.1/Collie_MC_V1.1_20261122/`）+ V1.2 讲解包。
> **性质**：V1.1 架构 + V1.2 导读/概念解释/36 个 Part 补丁 + V1.3 频率修订；HAL/SCHEMA 为附录 A/B，协议索引为 C，概念解释为 D，自检为 E。
> **保留**：V1.0/V1.1/V1.2 原稿均未改动；V1.2 原稿未上传；本地保留在 `20261123_v1.2/merged/`。

> **已知残留（必读）**：`can_exit` 在 `step` 前发布 `READY` 的竞态尚未修；50 Hz 把窗口从 10 ms 放大到 20 ms，必须先修再开放切换（见 Part 2 §D3.5 与 [V1.1 评审 §2.1](../../v1.1/REVIEW_V1.1.md)）。

## 全文目录

| Part | 内容 | 文件 |
|---|---|---|
| Part 1 | D0–D2 执行摘要、架构总览、领域模型 | [`Part1_D0-D2.md`](Part1_D0-D2.md) |
| Part 2 | D3–D4 Runner 框架、PolicyManager | [`Part2_D3-D4.md`](Part2_D3-D4.md) |
| Part 3 | D5–D6 每拍链路、上下游接口 | [`Part3_D5-D6.md`](Part3_D5-D6.md) |
| Part 4 | D7–D8 安全、并发实时 | [`Part4_D7-D8.md`](Part4_D7-D8.md) |
| Part 5 | D9–D12 配置资产、观测回放、测试、网络安全 | [`Part5_D9-D12.md`](Part5_D9-D12.md) |
| Part 6 | D13–D16 ADR、风险、路线图、评审清单 | [`Part6_D13-D16.md`](Part6_D13-D16.md) |

**附录**：[A. HAL 合同](Appendix_A_HAL_Contract.md)｜[B. Schema Canon](Appendix_B_Schema_Canon.md)｜[C. 协议/示例/测试索引](Appendix_C_Protocol_Examples_Tests.md)｜[D. 概念解释](Appendix_D_Concept_Deep_Dive.md)｜[E. 自检](Appendix_E_Self_Check.md)

## 与 V1.0 / V1.1 的关系

- **V1.0**：完整底稿，保留作历史对照；其中 9 处已被 V1.1 替换。
- **V1.1 变更单**：`PartA-E` + `HAL_CONTRACT` + `SCHEMA_CANON` + `proto/schemas/examples/tests`；是字段/合同的权威源。
- **本合并版**：V1.1 架构 + V1.2 讲解补丁；字段/合同冲突时，仍以 `proto/schemas/HAL_CONTRACT` 为准。

## 阅读建议

1. 先读 Part 1（一页结论 + 12 决策）和 Part 2（Runner 框架）。
2. 再读 Part 3（每拍链路/接口）和 Part 4（安全/实时）。
3. 最后读 Part 5（配置/测试/网安）和 Part 6（ADR/风险/checklist）。
4. 需要字段细节时查附录 B；需要 HAL 行为时查附录 A；需要 proto/示例/测试时查附录 C。

---


<!-- BEGIN_V12: FRONT-BIG-PICTURE -->
# 导读：从一句“站起来”到一条安全关节命令

> `[V1.2-解释]` 此文用于建立理解，不改 V1.1 的进程、安全或接口决策。故事中的动作均为讲解样例；未签发的 Q2B/B2Q、双足平衡、恢复动作维持 `DISABLED`。

## 1. 五幕故事：同一台机器人、同一条链

**第一幕：上电，先不动。** HAL 从设备读关节、IMU、总线健康，MC 的安全状态从 `INIT` 开始，形态 `Form=UNKNOWN`。平台没有确认支撑/姿态时，RT **不**发“保持刚才的位置”，HAL 使用已定义的低能量安全输出（具体能力【待定】）。安全自检通过后，平台才可能签发许可。**谁→谁**：HAL 反馈 → RT Snapshot → Safety 判定 → Gateway 更新可执行范围。

**第二幕：“站起来”。** Task Engine 发 `SetBehavior(quad_stand)`，Gateway 验 Session 和 ControlLease，再按 ActionGraph 找合法 Action，加载并准备 `ActionBundle/RunnerManifest`。Worker 生成候选，RT 检查 Epoch、反馈、SafetyLease、Guard，HAL 验唯一写权限才接受新关节目标。真正“站稳”要等支撑与稳定窗口满足才报 `RUNNING/stable`，不是 RPC `ACCEPTED` 就算。**谁→谁**：Task → Gateway → Worker → RT → HAL → 电机；反馈反向回来。

**第三幕：“跟我走”。** Task 允许 `quad_drive`，导航按 10–50 Hz 给 `BodyVelocityRef`，每条速度带来源、seq、TTL 和 ControlLease。Gateway 验资源权限，RT VelocityArbiter 选择当前有效来源，Worker 50 Hz 使用速度参考算腿/轮候选，RT 200 Hz 在有效窗内整形后发布。导航断流时不是重复上一条“前进”，而是 TTL 到期后按获批制动路径停止。**谁→谁**：Nav → Gateway/RT 参考 → Worker 计算 → RT 发令 → HAL。

**第四幕：“转成双足讲解”。** PolicyManager 按图准备 `quad_drive→quad_stop→q2b→biped_balance`。旧 Runner 的退出判据必须新鲜，目标资源/首拍、安全许可、HAL `pending_epoch` 必须齐全，RT 才允许切换；Q2B 的 phase 要看实际支撑、姿态、净空，不是计时到就成功。双足稳定后，若手势关节与平衡关节的 mask 冲突，不能让 Overlay 抢写，而要由平衡 Runner 消费手势参考。随后 `b2q` 回四足。**谁→谁**：Task → PolicyManager 规划 → Worker 预备 → RT 原子提交 → HAL 确认；本段动作目前【待定/禁用】。

**第五幕：途中急停、复位。** 硬件急停直接走设备链；SafetyKernel 锁存故障、撤销 SafetyLease，RT 不再采纳普通候选，HAL/驱动器独立保护。复位是“回到 `INIT/UNKNOWN`、重新自检和授权”，不是重放急停前的 `B2Q` 或旧速度。**谁→谁**：急停硬件 → 驱动/HAL；同时 Safety → RT；人工复位 → INIT → 检测 → 重新准入。

## 2. 五层主图：四流、三时钟、一条铁律

```mermaid
flowchart TB
  A["① 意图与权限\nTask / Nav / PlatformSafety\nSession / ControlLease"]
  B["② 编排\nmc_gateway：PolicyManager / Graph / Bundle"]
  C["③ 计算 50 Hz / 20 ms【建议】\nmc_runner_worker：Obs / Runner / Backend / Codec"]
  D["④ 实时执行 200 Hz / 5 ms【建议】\nmc_rt：Snapshot / Arbiter / Epoch / Mux / Guard"]
  E["⑤ 设备 目标约 1 kHz【待定】\nHAL / driver / 电机轮 / IMU"]
  A -->|"ActionRequest：事件；失败拒绝/排队"| B
  A -->|"VelocityRef：10–50 Hz + TTL；过期停车"| D
  B -->|"preload/enter/prepare：非RT"| C
  B -->|"切换请求：异步；失败保留旧Epoch"| D
  D -->|"Snapshot：50 Hz，只读；过期失效"| C
  C -->|"Candidate：50 Hz + deadline；迟到丢弃"| D
  D -->|"唯一 HalCommand 200 Hz；拒收保护"| E
  E -->|"Feedback 200–1000 Hz；失联保护"| D
  S["mc_safety：SafetyLease\n100 Hz + 严重故障异步"] -->|"许可/撤销；超期禁正常输出"| D
  E -.->|"设备健康；失联不续租"| S
  H["物理急停"] -.->|"独立保护，不等推理"| E
```

**四流不是四个进程**：① Action 流决定“做哪个动作”；② Velocity 流持续改变“走多快”；③ Feedback 流把设备真实状态送回来；④ Safety 流使其他三流受到约束，严重时直接禁止输出。四流交汇在 RT，但 RT 不负责产品意图决策。

**三个时钟**：Worker 20 ms 产生一次候选，RT 每 5 ms 可能使用最近未过期候选，设备层目标循环约 1 ms。它们**不是同一个同步函数**；RT 不等待 Worker 的新结果。50/200 Hz 和 1 kHz 均是【设计建议/目标平台待证】。

**铁律**：**只有 `mc_rt` 可写正常 HAL 关节命令**。Gateway 管准入；Worker 只提候选；Safety 只收紧/撤销运动许可；HAL 可独立拒收和保护，硬件急停独立。

## 3. 一张概念关系地图：每个词回答不同问题

```mermaid
flowchart LR
  B["Behavior\n用户要什么"] --> A["Action\n执行哪个定义"]
  G["Gateway\n入口/鉴权"] --> P["PolicyManager\n谁来编排"]
  P --> AG["ActionGraph\n能从哪到哪"]
  P --> A --> BU["ActionBundle\n主任务和叠加如何组装"]
  BU --> R["Runner\n每拍怎么计算"]
  M["RunnerManifest\n加载/输出合同"] --> R
  K["ExecutionKind+BehaviorRole\n机制+角色"] --> R
  O["ObsSpec\n输入维度如何排"] --> R
  AS["ActionSpec\n输出如何解码"] --> R
  S["Snapshot\n这一拍看见什么"] --> R
  R --> T["mc_rt\n唯一提交出口"]
  T --> J["JointMux\n关节归谁"] --> OG["OutputGuard\n允许发多少"] --> H["HAL\n设备协议/拒收/保护"]
  Q["Session\n身份"] --> G
  CL["ControlLease\n运动资源控制权"] --> P
  SL["SafetyLease\n当前许可"] --> OG
  E["ActionEpoch\n新旧切换版本"] --> T
  GL["Golden\n训练部署对不对"] --> R
  BB["黑匣子\n事后回放"] -.-> S
  BB -.-> T
  BB -.-> H
  MS["mc_safety\n故障与撤许可"] --> SL
```

**读图顺序**：先从 `Behavior` 沿主链读到 HAL；再看 Graph/Manifest/Spec 是怎样附在主链上的；最后看四个许可、Golden、黑匣子作为横向约束。`Runner` 不等于进程，`Manifest` 不等于模型文件，`Epoch` 不等于会话。

## 4. 责任矩阵：谁做、谁绝不能做、失败谁兜

| 主体 | 负责 | 不能做 | 它失败时谁兜底 |
|---|---|---|---|
| Task / Nav | 意图、规划速度、场景条件 | 不可发关节命令 | Gateway 鉴权/TTL；Safety/HAL |
| 平台 Safety | 系统模式、业务安全边界、急停流程 | 不能绕过 HAL/本地准入 | MC Safety + HAL/硬件链 |
| `mc_gateway` | RPC、Session/ControlLease、Graph、Registry、切换准备 | 不直接发候选电机目标、不占 RT | RT 继续合法旧 Epoch 或停止；TTL |
| `mc_runner_worker` | Obs、模型/经典策略、Codec、封存决策 | 不直接下发关节、不阻塞 RT | RT 截止/Guard；HAL 看门狗 |
| `mc_rt` | 5 ms Snapshot、速度仲裁、Epoch、Mux、Guard、唯一正常 writer | 不等模型/IPC、不做磁盘 I/O | HAL 设备 watchdog/硬件急停 |
| `mc_safety` | 故障锁存、SafetyLease、保护等级 | 不成为第二正常 writer、不替代硬件急停 | RT 失租保护；HAL/硬件 |
| HAL / 驱动 | 协议适配、权限、seq/deadline/CRC 校验、模式/限额/看门狗 | 不决定产品 Behavior，不推理 ONNX | 驱动硬件保护/物理急停【待验证】 |

## 5. 从“站起来”到电机的 13 步

| # | 谁 | 输入 → 输出 | 关键对象 | 失败/超时 |
|---:|---|---|---|---|
| 1 | Task → Gateway | `SetBehavior(quad_stand)` → 收到请求 | `ActionRequest.header` | 超时/重放拒绝 |
| 2 | Gateway | 身份与来源检查 | `Session` | 越权拒绝 |
| 3 | Gateway/PolicyManager | 申请运动资源 → 授予/等待 | `ControlLease` | 冲突/过期不入队 |
| 4 | PolicyManager | 检查当前 Action 到目标的合法路径 | `ActionGraph` | 无边/禁用返回 REJECTED |
| 5 | Registry | 解析 Bundle/Manifest 与发布状态 | `ActionBundle`, `RunnerManifest` | Asset BROKEN/未批准拒绝 |
| 6 | Worker loader | 规格/hash/拓扑/Golden/预热 | `ObsSpec`,`ActionSpec` | 不能加载不替代默认模型 |
| 7 | RT/Safety | 校验形态支撑和当前安全许可 | `Snapshot`,`SafetyLease` | UNKNOWN 不允许运动 |
| 8 | Worker | `enter` → 首候选准备 | `IRunner`,`RunnerOutput` | 准备失败旧 Epoch 不变 |
| 9 | Worker → RT | 封存退出决策并发布候选 | `SealedExitDecision`,`CandidateHeader` | 过期 WAIT；**已知 READY 竞态 P0** |
| 10 | RT ↔ HAL | 异步 `PREPARE_EPOCH` → 状态镜像 | `pending_epoch`,`switch_tx_id` | 未准备不提交；RT 等待=0 |
| 11 | RT | 同拍读 Exit/Guard/Lease、提交新 Epoch | `ActionEpoch`,`JointMux` | 条件不足维持合法旧动作/保护 |
| 12 | RT → HAL | 经 Guard 的 200 Hz 命令 | `HalCommand` | 拒收锁存；不重发旧 seq |
| 13 | HAL → 电机 → RT | 实际执行/ACK/反馈、稳定窗 | `HalStatus`,`RobotStateSnapshot` | 失 ACK/失反馈保护；稳定后才报告成功 |

上表是**跨多个 5 ms/20 ms 周期**的流程，不表示 13 步必须在同一控制拍完成。任何“合法路径”都不能代替真实物理支撑判断。

## 6. 四把钥匙：认人、占资源、允许运动、写设备

| 钥匙 | 类比 | 谁签发/检查 | 过期、撤销或失败 |
|---|---|---|---|
| `Session` | 门禁证：你是谁 | 可信平台/网关建立，Gateway 验身份；请求/源 seq 绑定 | 新请求/新速度拒绝，不能凭旧身份继续抢资源 |
| `ControlLease` | 方向盘钥匙：谁现在控制这个 scope | PolicyManager/资源仲裁签发，Gateway/RT 检查 source、lease ID、TTL | 拒新引用，当前动作按批准停车/过渡 fallback；**不是直接自由落体** |
| `SafetyLease` | 安全员盖章：此刻准许哪些控制模式 | `mc_safety` 10 ms 续发，RT 每 5 ms 检查 | 失租阻断正常输出；不依赖 ONNX |
| `HAL writer lease` | 车钥匙：谁能碰设备接口 | HAL 用 OS 权限+私有 token 授权，设备校验 | HAL 拒收、超时独立保护；不能仅靠填对 `writer_id` |

**为什么不能合并**：一名已登录用户也可能没拿到导航资源；拿到资源也可能已触发安全禁止；安全允许也不意味着任何进程都能直接写电机。四把钥匙分别防不同问题，发放者和时效都不同。

## 7. 5 个盒子：2 分钟复述卡

```text
任务/导航/安全 → Gateway 编排 → Worker 计算 → RT 唯一出口 → HAL 执行
你想做什么     谁有权、何时换     关节候选怎么算   每5ms能否发     电机能否接受
```

推荐复述：**“Task 发意图，Gateway 查身份和资源并选 Action；Worker 根据反馈和策略资产算候选；RT 是唯一能把候选变成关节指令的地方，它检查 Epoch、安全和限幅；HAL 再校验权限和设备合同，真正给驱动器。Safety 不等模型，硬件急停也不等软件。”**

## 8. 白话术语速查（固定五行）
### 01. `Behavior`
- **是什么**：面向产品的能力名。
- **为什么**：可稳定对外承诺，不暴露具体模型。
- **不是什么**：不是一个特定 ONNX。
- **例子**：“跟我走”映射到四轮行走。
- **位置**：D0/D2；Gateway。

### 02. `Action`
- **是什么**：一次被注册的可执行动作定义。
- **为什么**：决定动作范围、入口与合法切换。
- **不是什么**：不是一次执行实例。
- **例子**：quad_stop 是一个 Action，跑几次是不同 execution。
- **位置**：D2/D4；PolicyManager。

### 03. `ActionBundle`
- **是什么**：主 Runner 与可选 Overlay 的组合计划。
- **为什么**：声明谁负责哪些关节。
- **不是什么**：不是多份目标直接相加。
- **例子**：四足站立主 Runner 加头部点头 Overlay。
- **位置**：D4.3；Registry/RT。

### 04. `Runner`
- **是什么**：每拍计算候选关节目标的执行对象。
- **为什么**：用同一生命周期接纳不同算法。
- **不是什么**：不是电机驱动，也不是单独进程。
- **例子**：WheelDriveRunner 根据速度与反馈算轮腿指令。
- **位置**：D3；Worker。

### 05. `RunnerManifest`
- **是什么**：某个 Runner 的加载和执行合同。
- **为什么**：防模型、关节映射、时序不一致。
- **不是什么**：不是策略权重本身。
- **例子**：quad_stop 的 class、mask、后端、hash、退出守卫。
- **位置**：D9.3；Registry/Worker。

### 06. `ExecutionKind`
- **是什么**：Runner 采用的计算机制。
- **为什么**：决定加载 ONNX、经典算法或轨迹引擎。
- **不是什么**：不是产品动作类别。
- **例子**：四轮行走若用 ONNX，kind=ONNX。
- **位置**：D3.3；FactoryRegistry。

### 07. `BehaviorRole`
- **是什么**：Runner 在动作链的用途。
- **为什么**：决定输入参考/守卫/输出职责。
- **不是什么**：不是具体神经网络结构。
- **例子**：Q2B 的 role=TRANSITION。
- **位置**：D3.3；FactoryRegistry。

### 08. `ObsSpec`
- **是什么**：按维度定义模型输入的配方。
- **为什么**：让训练与部署读同一顺序/单位/历史。
- **不是什么**：不是只写一个观测总维数。
- **例子**：关节角第 5 维在 tensor index=4。
- **位置**：D5.3/附录 B；Worker。

### 09. `ActionSpec`
- **是什么**：按维度定义模型输出如何解码。
- **为什么**：避免模型符号/增益/模式错配。
- **不是什么**：不是 HAL 的物理限幅。
- **例子**：模型输出 0.2 经 sign/scale/default 转 q。
- **位置**：D5.5/附录 B；Codec。

### 10. `PolicyManager`
- **是什么**：决定当前动作及如何切换的编排器。
- **为什么**：让切换有路径、准备和失败处理。
- **不是什么**：不在 RT 里跑推理。
- **例子**：跟随变双足需先 quad_stop 后 q2b。
- **位置**：D4；Gateway。

### 11. `ActionGraph`
- **是什么**：合法 Action 与切换边的注册图。
- **为什么**：禁止从任意动作直接跳任意动作。
- **不是什么**：不包含 ESTOP 等安全状态。
- **例子**：quad_drive→quad_stop→q2b。
- **位置**：D4.2；Gateway。

### 12. `Gateway`
- **是什么**：进入运控服务的可信入口进程。
- **为什么**：把上游调用变成受权的领域请求。
- **不是什么**：不产生关节目标。
- **例子**：收到站起来先验 Session/Lease。
- **位置**：D1/D6；mc_gateway。

### 13. `Worker`
- **是什么**：运算候选策略的非 RT 进程。
- **为什么**：让模型慢或挂死不拖住发布线程。
- **不是什么**：不拥有设备写权限。
- **例子**：每 20 ms 计算一次动作候选。
- **位置**：D1/D3/D5；mc_runner_worker。

### 14. `mc_rt`
- **是什么**：具有硬截止目标的关节发布进程。
- **为什么**：在固定拍检查并执行唯一提交。
- **不是什么**：不等待模型或 RPC。
- **例子**：5 ms 验 Epoch/Guard 后发 HalCommand。
- **位置**：D1/D8；mc_rt。

### 15. `mc_safety`
- **是什么**：本机独立运动安全核进程。
- **为什么**：不依赖推理撤销许可并锁存故障。
- **不是什么**：不是第二个普通关节 writer。
- **例子**：发现 IMU 失效时不续 SafetyLease。
- **位置**：D2.4/D7；mc_safety。

### 16. `HAL`
- **是什么**：硬件抽象层：设备协议、权限、看门狗与反馈边界。
- **为什么**：阻止无效或无人授权的命令进入设备。
- **不是什么**：不是策略算法，也不等于纯驱动。
- **例子**：拒绝旧 epoch 或旧 seq 的 HalCommand。
- **位置**：D6.8/附录 A；device_hal。

### 17. `Session`
- **是什么**：已认证的调用者会话。
- **为什么**：防冒名与跨会话重放。
- **不是什么**：不是运动资源独占权。
- **例子**：导航带 session_id 发速度。
- **位置**：D2/D6；Gateway。

### 18. `ControlLease`
- **是什么**：某运动资源在一段时间内的独占控制权。
- **为什么**：防多个授权来源同时控制方向盘。
- **不是什么**：不是 SafetyLease。
- **例子**：遥控抢占导航需先撤旧租并确认停车。
- **位置**：D2.5/D4.4；Gateway/RT。

### 19. `SafetyLease`
- **是什么**：安全核定期签发的运动许可。
- **为什么**：保证安全核失活会使正常输出停止。
- **不是什么**：不是用户授权。
- **例子**：每 10 ms 刷新，30 ms 未续失效【建议】。
- **位置**：D7.4/D8；Safety→RT。

### 20. `HAL writer lease`
- **是什么**：HAL 验证的唯一正常设备写者能力。
- **为什么**：防双写、假冒 writer_id。
- **不是什么**：不是由 Gateway 发的 ControlLease。
- **例子**：只有 mc_rt 持有 OS 认可的写能力。
- **位置**：附录 A；HAL。

### 21. `ActionEpoch`
- **是什么**：RT 每次动作原子移交增加的版本号。
- **为什么**：防旧候选和旧 HAL 命令混进新动作。
- **不是什么**：不是模型推理拍号。
- **例子**：q2b 接管之后，旧 quad_stop epoch 被拒。
- **位置**：D4.5/附录 A；RT。

### 22. `Snapshot`
- **是什么**：RT 汇总同一拍有效反馈的不可变视图。
- **为什么**：防 Worker 同时读到新 IMU/旧关节值。
- **不是什么**：不是无时间信息的状态数组。
- **例子**：含 snapshot_seq/每源 age、valid。
- **位置**：D5.2；RT→Worker。

### 23. `JointMux`
- **是什么**：按 ownership 组合 Primary 与 Overlay。
- **为什么**：让每个关节只收到一个明确的控制来源。
- **不是什么**：不是随意加权求和。
- **例子**：Balance 承重关节不能被挥手覆盖。
- **位置**：D4.3/D5.6；RT。

### 24. `OutputGuard`
- **是什么**：发布前验证安全包络与时效。
- **为什么**：阻止 NaN、越界、过期候选发到 HAL。
- **不是什么**：不是能保证机器人不跌倒的万能算法。
- **例子**：候选中一个承重关节 NaN → 整包失败。
- **位置**：D5.6/D7；RT。

### 25. `Golden`
- **是什么**：固定输入与期望输出的签收向量。
- **为什么**：检测训练/部署维度或公式错位。
- **不是什么**：不是现场轨迹日志。
- **例子**：已知 obs 输入应得到指定 codec 输出。
- **位置**：D9/D10/D11；训练+软件。

### 26. `黑匣子`
- **是什么**：预分配的逐拍故障记录环。
- **为什么**：把现场故障变成可重放的数据。
- **不是什么**：不是同步写盘的日志线程。
- **例子**：保存故障前 30 s + 后 10 s【建议】。
- **位置**：D10；RT 环/日志异步。

### 27. `Form=UNKNOWN`
- **是什么**：上电后形态或支撑未可信确认。
- **为什么**：避免直接保持未知姿势。
- **不是什么**：不是一个可以执行的动作。
- **例子**：INIT 不能直接进入 Q2B/Balance/Recovery。
- **位置**：D2.4/D7.4；Safety。

### 28. `switch_ready`
- **是什么**：当前动作已稳定且满足可交接条件。
- **为什么**：防上游误判“已受理”为“已可切”。
- **不是什么**：不是 action_done。
- **例子**：双足摇摆虽 RUNNING 也可为 false。
- **位置**：D4.6；Status。

### 29. `SIL/HIL`
- **是什么**：软件模型测试/真实设备接口在环测试。
- **为什么**：区分合同测试与物理行为证据。
- **不是什么**：不是彼此可替代的验收。
- **例子**：FakeHal PASS 不证明真实 watchdog。
- **位置**：D11/附录 C；测试。

### 30. `ModeTransition`
- **是什么**：控制模式及增益的有界切换状态机。
- **为什么**：限制位置/力矩/增益突变。
- **不是什么**：不是切换一个 enum 值。
- **例子**：POSITION→TORQUE 需 PREPARE_MODE 与 ramp。
- **位置**：D5.6/附录 A；RT/HAL。

## 9. 三段阅读路径（最短）

| 想弄懂什么 | 先读 | 再读 |
|---|---|---|
| 谁决定动作、谁能发电机 | Part 1 D1.2–D2.1 | Part 3 D6.1–D6.2；附录 A §1–3 |
| 为什么可换 Runner 而不能随意换 | Part 2 D3.3–D3.7 | Part 5 D9.1–D9.6；附录 B §4–5 |
| 系统坏时会发生什么 | Part 1 D2.4–D2.5 | Part 4 D7.4–D8.5；附录 A §5–6 |

**最快的 3 节**：`D1.2 进程与连接` → `D3.7 三条时序` → `D9.1 四级配置`；看完能把“谁在哪、先后怎样、靠什么文件运行”串起来。

> `[V1.2-审阅注记]` `can_exit` 的 pre-step READY 竞态仍为 P0：本文只解释其风险，**没有替换实现**。详见 `REVIEW_V1.1.md` §2.1。

完成度：100%（五幕故事、五层/四流/三时钟、概念地图、责任、13 步、四钥匙、30 词速查）。未完成/假设：频率/时限是 V1.1 建议值；多形态仍禁用。
<!-- END_V12: FRONT-BIG-PICTURE -->

# Collie 运控服务软件架构 V1.3 — Part 1（D0–D2）

<!-- BEGIN_V12: P1-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：先定“谁管什么”

```mermaid
flowchart LR
 A["Task/Nav/Safety：意图"] --> B["Gateway：编排"] --> C["Worker：Runner"] --> D["RT：唯一关节出口"] --> E["HAL：设备"]
 B -.-> T["本 Part D0–D2\n决策/进程/责任区/状态"]
```

**四个解释盒（为什么／是什么／不是什么／故事中怎样／误解）**：

| 概念 | 为什么有它、是什么 | 不是什么 | Running Example | 易错点 |
|---|---|---|---|---|
| Behavior/Action | 把“跟我走”业务与具体控制实现分开 | 不是直接调用 ONNX | 跟随对应 quad_drive | 不能把 Behavior 当 Runner 类 |
| 四进程 | 把网络、推理、RT、安全独立调度 | 不是四个控制器同时发电机 | Worker 计算，RT 唯一发布 | 进程数量≠逻辑模块数量 |
| 五个责任区 | 明确谁拥有身份、编排、候选、关节、安全 | 不是五个微服务 | “站起来”跨五个区交接 | 上下文≠线程 |
| INIT/UNKNOWN | 上电支撑未知时不输出位置保持 | 不是 SAFE_HOLD 的别名 | 开机先 HAL_SAFE，确认后站立 | 不能用上一拍位置推测安全 |

**小故事**：上电以后 `Form=UNKNOWN`，即使 Task 发来站立请求，Gateway 可以记录请求，但 PolicyManager 必须等待入场准入，RT 不允许未知支撑下的保持。反馈/形态确认后，才能按 ActionGraph 准备站立 Action。

**怎么读 D0/D1/D2 的表**：先看 D0 的“决策/代价”，它回答为何这样做；D1.2 看“进程/周期/断链”，它回答放在哪；D2.1 看“唯一负责/不能做”，它回答谁有权。50/200 Hz 是【建议】而非 Collie 实测；双足和 HAL 能力是【待定】。
<!-- END_V12: P1-OVERVIEW-01 -->

> **版本**：V1.1 合并阅读版　**日期**：2026-11-22　**状态**：软件设计基线（可编码），非实机安全批准
>
> **来源**：V1.0 六部分（`output/20261122_6parts/`）+ V1.1 定点修订（`PartA-E`、`HAL_CONTRACT.md`、`SCHEMA_CANON.md`、`proto/`、`schemas/`、`examples/`、`tests/`）。
>
> **读法**：本版把 V1.1 的 9 处修订合并进 V1.0 的章节结构；详细字段/合同以附录 A（HAL）、附录 B（Schema）为准。V1.0 原文保留，仅作历史对照。
>
> **已知残留**：`can_exit` 在 `step` 前发布 `READY` 的竞态尚未修（见 Part 2 的“审阅注记”与 `REVIEW_V1.1.md` §2.1）；本版如实保留，不假装已解决。

---

## 0. 一页结论

Collie 运控采用“**Behavior 对外、Action 配置化、ActionBundle 组合、Runner 执行、PolicyManager 编排、RT 唯一关节出口、SafetyKernel 独立许可**”的结构。

四个 MC 进程：

| 进程 | 职责 | 能否写 HAL |
|---|---|---|
| `mc_gateway` | RPC/权限/PolicyManager/Registry/ActionGraph/请求仲裁 | 否 |
| `mc_runner_worker` | ObsBuilder / Runner / Inference / Codec，按 50 Hz 计算候选 | 否 |
| `mc_rt` | 200 Hz 快照、速度仲裁、切换提交、JointMux、OutputGuard、唯一发布 | **唯一正常写入者** |
| `mc_safety` | SafetyKernel / Lease / Fault / 安全状态机 | 否（只收紧许可） |

外加 `device_hal`（设备合同、独立看门狗/保护）。硬件急停不经过软件。

**一句话原则**：一个关节出口、一套策略契约、一条可回放的每拍链路、一条不依赖推理的安全路径。

---

## D0. 执行摘要与 12 条关键决策

| ID | 决策 | 理由 | 替代方案 | 代价/状态 |
|---|---|---|---|---|
| ADR-01 | Behavior（产品能力）与 Runner（执行单元）分开 | 接口不受模型变更影响 | 仅 Runner 或仅 Behavior | 多一层映射；【建议】 |
| ADR-02 | ActionBundle = 单 Primary + 可选 Overlay slots | 五类行为共用组合机制 | 一 Action 一类一线程 | 组合校验成本；【建议】 |
| ADR-03 | Gateway / Worker / RT / Safety 混合多进程 | 推理挂死不阻塞发布 | 单进程多线程 | IPC/部署成本；【建议，待平台验证】 |
| ADR-04 | 只有 `mc_rt` 有正常 HAL 写权限 | 消除双写与不确定覆盖 | 每 Runner 写 HAL | 统一仲裁点；【建议】 |
| ADR-05 | 50 Hz 策略、200 Hz 关节发布（ZOH） | 与训练 dt=0.02 对齐；分离推理与发令实时性 | 100 Hz 空转；50→100 插值 | 【V1.3 决策】 |
| ADR-06 | 双足先按动态平衡接口设计 | 不隐含机械静态锁止 | 全用姿态位控 | 需平衡资产；【待定】 |
| ADR-07 | Q2B/B2Q 使用独立 TransitionRunner | 形态过渡需相位、支撑与退路 | 位置线性插值 | 独立资产/验收；【建议】 |
| ADR-08 | bitmask 逐关节所有权，默认不做同关节混合 | 禁止叠加抢写 | Scope 粗分/最后写者赢 | 需训练协商；【建议】 |
| ADR-09 | 四个稳定 RPC + 两个流；内部保留三类领域输入 | 限制外部 ABI 变化 | 暴露每个 Runner API | Adapter 维护；【建议】 |
| ADR-10 | 本地 SafetyKernel + OutputGuard + HAL + 硬件链 | 不能依赖模型运行 | 单看门狗/单安全进程 | 状态/复位协议；【建议】 |
| ADR-11 | Manifest + 逐维 ObsSpec/ActionSpec + Golden | 检出训练/部署错位 | 仅 ONNX + 参数数量 | 算法交付增加；【建议】 |
| ADR-12 | 独立 MC 仓；从旧代码阶段迁移 | 可独立编译/回滚 | 旧节点里加 switch(model) | 建骨架成本；【建议】 |
| ADR-13 | 冷启动 `INIT` + `Form=UNKNOWN`，未知支撑不发保持 | 未知姿态下位置保持可能危险 | 直接 SAFE_HOLD | 启动变慢；【建议】 |
| ADR-14 | ControlLease 独立于 Session/SafetyLease | 运动资源需要独占所有权 | 只靠优先级 | 租约协议成本；【建议】 |

### 非软件背景决策者 5 分钟版

架构把“谁可以让机器人做什么”（平台任务）、“当前用哪个动作”（MC PolicyManager）、“动作怎么算”（Runner）、“什么命令真的能写电机”（OutputGuard/HAL）分开。新增动作主要是交付资产，不是改整机软件；同一套接口可回放、回滚、故障注入。最大风险是双足/变形失稳、模型与本体映射错、软件挂死后继续输出旧命令。必须拍板：关节拓扑、双足支撑形式、HAL/硬件急停能力、首发载荷/地形、实时计算平台。

---

<!-- BEGIN_V12: P1-D0-QUIZ -->
#### [V1.2-解释] D0 读完自测

1. Behavior 与 Runner 为什么分离？
2. 何谓“一个关节出口”？
3. 50/200Hz 是事实还是目标？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P1-D0-QUIZ -->

## D1. 架构总览

### D1.1 上下文

```mermaid
flowchart TB
  U["用户/App/SDK/云"] -->|"任务事件"| TE["平台 Task Engine / SystemMode"]
  AG["大脑 Agent"] -->|"结构化意图"| TE
  TE -->|"ActionRequest RPC"| MC["Collie MC Service"]
  NAV["导航/跟随/运镜"] -->|"BodyVelocityRef 10–50 Hz"| MC
  RC["授权遥控"] -->|"速度约 50 Hz"| MC
  PS["平台安全"] -->|"SafetyEvent 异步"| MC
  MC -->|"HalCommand 200 Hz"| HAL["device_hal"]
  HAL -->|"JointState/IMU 200–1000 Hz"| MC
  HAL <-->|"CAN/EtherCAT"| HW["电机/轮/IMU"]
  MC -->|"MotionStatus 50 Hz + Events"| TE
  MC -->|"诊断"| HDS["HDS/日志"]
  PS -.->|"独立硬件急停"| HW
```

### D1.2 进程与连接

| 连接 | 周期/预算 | 断链措施 |
|---|---|---|
| Gateway→RT 切换邮箱 | 事件，≤1 个 5 ms tick 可见 | 请求超时，活动 Epoch 不变 |
| Gateway→Worker 资源操作 | 准备期，不占 RT | 新 Action 不加载，旧动作不中断 |
| HAL→RT 反馈 SHM | 200–1000 Hz；读取 ≤0.2 ms | 无效数据触发 Guard |
| RT→Worker 快照 | 50 Hz，零分配读视图 | 过期快照不得推理 |
| Worker→RT 候选 | 50 Hz，截止 Worker tick+15 ms | 不积压，迟到拒绝 |
| Safety→RT Lease | 100 Hz + 异步严重故障 | 失租立即退出正常输出 |
| RT→HAL 命令 | 200 Hz，单写者 | HAL 15 ms 看门狗（待验证） |
| HAL→Safety 设备健康 | ≥100 Hz | 不续租 |

`mc_rt` 不执行模型加载、同步推理、ROS 回调、文件写入或等待锁。Worker 输出带 `(boot_id, action_epoch, tick_id, snapshot_seq, deadline_ns, manifest_hash)`；RT 只采用当前 Epoch、未过期、完整且有限的候选。

### D1.3 逻辑模块

<!-- BEGIN_V12: P1-D1.3-MODULE-MAP -->
#### [V1.2-解释] D1.3 “逻辑模块”应该怎样映射到机器上

**模块**回答“某段代码负责什么”；**进程**回答“故障隔离在哪里”；**线程**回答“什么时候运行”。下表不增加进程：

| 模块 | 进程/线程 | 输入→输出 | 不能做 |
|---|---|---|---|
| MotionApiAdapter / PolicyManager / ActionGraph | `mc_gateway` / rpc & orchestration | 已鉴权 ActionRequest→准备事务 | 等 RT 返回/发关节 |
| Registry / ManifestValidator | Gateway + Worker loader | 静态资产→可预加载 Runner | 实时热加载 |
| ObsBuilder / Runner / Inference / Codec | `mc_runner_worker` / 50 Hz step | Snapshot+Ref→Candidate | 写 HAL |
| Snapshot / VelocityArbiter / SwitchCoordinator | `mc_rt` / 200 Hz | HAL反馈+最新速度/事务→有效状态+Epoch | 同步等待Worker |
| JointMux / ModeTransition / OutputGuard | `mc_rt` / 200 Hz | 候选→唯一合法 JointTarget→HalCommand | 直接改业务 Graph |
| SafetyKernel | `mc_safety` / 100 Hz | 反馈健康/平台限制→SafetyLease | 第二正常 writer |
| HAL 接收/设备适配 | `device_hal` / 设备周期 | HalCommand→驱动+ACK | 选 Behavior |

**具体串联**：Task 的“站起来”先到 Gateway 取图和租约；Worker 准备候选；RT 在 5ms 拍决定提交；HAL 最后拒绝/接受。这个过程不是跨进程同步调用链；Worker 卡住，RT 不等。

`[V1.2-审阅注记]` V1.1 D1.2 的 50/200/1000 Hz 为设计目标，不能由这张模块映射表推断实际硬件能力。
<!-- END_V12: P1-D1.3-MODULE-MAP -->

`MotionApiAdapter → PolicyManager/Registry/Graph → SwitchCoordinator`；`HAL → Snapshot → ObservationBuilder → Runner/Inference → ActionCodec → JointMux → OutputGuard → HalCommand`；`SafetyKernel → OutputGuard`；`MotionStatusPublisher` 旁路。

**正常主链**：HAL → 快照 → 逐维观测 → Runner（需要时推理）→ 解码 → 所有权合成 → 安全限幅 → 唯一 HAL 命令。模型运行库失效也不能跳过后两级。

### D1.4 安全链

`Worker` 只产生候选；`mc_safety` 发短时 Lease；`OutputGuard` 每拍检查；`mc_rt` 唯一发令；HAL/驱动器/硬件急停逐级兜底。`SAFE_HOLD` 是“经过特定形态验证的受控保持”，不是任意姿态的默认输出。

---

<!-- BEGIN_V12: P1-D1-QUIZ -->
#### [V1.2-解释] D1 读完自测

1. 逻辑模块和进程是一回事吗？
2. 哪一条线在 Worker 挂死时不能阻塞？
3. HAL 怎样阻止第二个 writer？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P1-D1-QUIZ -->

## D2. 领域模型

### D2.1 五个限界上下文

| 上下文 | 聚合根/对象 | 唯一负责 | 不能做 |
|---|---|---|---|
| Motion API | `Session`, `ActionRequest` | 身份、权限、请求回执 | 改写当前关节 |
| Motion Orchestration | `ActionExecution`, `ActionGraph` | 路径、准备、切换阶段 | 绕过 RT 直接提交 |
| Runner Runtime | `RunnerInstance`, `RunnerManifest` | 生命周期、模型/轨迹、候选 | 自行订阅/发 HAL |
| Joint Control | `RobotStateSnapshot`, `Ownership`, `JointTargetArray` | 时间对齐、合成、Epoch、输出 | 业务仲裁 |
| Motion Safety | `SafetyState`, `SafetyLease`, `Fault` | 本地严重故障、降级/复位 | 擅自降低平台急停 |

**关键对象**：`Behavior` 对外能力；`Action` 配置化执行定义；`ActionBundle` 组合；`Runner` 内部执行单元；`RunnerManifest` 静态契约；`Session` 来源会话；`ControlLease` 运动资源独占权；`ActionEpoch` 接管代数；`Ownership` 关节位图；`StepInput` 每拍输入；`RunnerOutput` 候选输出。

### D2.2 Runner 生命周期

`Created → Loaded → Entered → Running → Exiting → Exited → Faulted`。

- `load` 非实时校验/预分配；
- `enter` 只准备，不提交 HAL/RT Epoch；
- `can_exit=READY` 只代表旧 Runner 可交出；
- `step` 在 Worker 预算内产候选，不保证被 RT 采用；
- `exit` 在 RT 撤销 Epoch 后执行；
- `Faulted` 不授权自恢复。

### D2.3 切换状态机

`REQUESTED → PREPARING → WAIT_EXIT → ENTERING → TRANSITIONING → STABILIZING → RUNNING`；失败 `FAULT/SAFE`。

- 提交前失败：旧 Runner 仍有效则保留旧 Action；
- 一旦提交新 Epoch：禁止未经验证直接回旧策略；
- `TRANSITIONING → STABILIZING` 必须由物理判据触发，不是计时器；
- `switch_ready` 仅在“稳定 + 无切换 + 安全允许 + 可退出”时为真。

### D2.4 安全状态机（V1.1 合并）

```mermaid
stateDiagram-v2
 [*] --> INIT
 INIT --> DAMPING: 支撑未知/反馈不完整/标定未就绪
 INIT --> SAFE_HOLD: 支撑+姿态+反馈可信
 INIT --> NORMAL: 仅显式允许 boot_motion 且全部准入
 DAMPING --> INIT: 授权自检且硬件不在急停
 SAFE_HOLD --> NORMAL: 完整许可与运动准入
 NORMAL --> DEGRADED: 可控异常
 DEGRADED --> NORMAL: 恢复窗口+许可
 NORMAL --> SAFE_HOLD: 可验证安全停车
 DEGRADED --> SAFE_HOLD: 已停稳且可保持
 NORMAL --> DAMPING: 失稳/反馈不足
 DEGRADED --> DAMPING: 风险升级
 SAFE_HOLD --> DAMPING: 支撑/反馈失效
 NORMAL --> ESTOP: 严重故障/硬件急停
 DEGRADED --> ESTOP: 严重故障/硬件急停
 SAFE_HOLD --> ESTOP: 严重故障/硬件急停
 DAMPING --> ESTOP: 严重故障/硬件急停
 INIT --> ESTOP: 严重故障/硬件急停
 ESTOP --> INIT: 物理复位+维护授权+自检
 SAFE_HOLD --> RECOVERY: 环境/形态/资产/人工许可
 DAMPING --> RECOVERY: 仅确认当前形态/支撑后
 RECOVERY --> SAFE_HOLD: 恢复完成+支撑确认
 RECOVERY --> DAMPING: 失败/失去反馈
 RECOVERY --> ESTOP: 严重故障
```

**未知形态（Form=UNKNOWN）禁止**：Q2B、B2Q、Balance、Recovery、全部 TransitionRunner、正常四轮移动/受力姿态/Overlay。不得用上一次请求推断 Form。

### D2.5 ControlLease（V1.1 合并）

<!-- BEGIN_V12: P1-D2.5-FOUR-KEYS -->
#### [V1.2-图] 四钥匙放在完整路径上

```mermaid
flowchart LR
 T["Task/Nav"] --> S["Session\n认人"] --> C["ControlLease\n占运动scope"] --> G["Gateway\n编排"] --> W["Worker\n算候选"] --> R["RT\n验SafetyLease"] --> H["HAL\n验writer lease"]
 M["mc_safety"] -.->|"短时许可"| R
```

**四个时效不可以合并**：会话失效阻断新的来源；ControlLease 失效触发获批制动/phase fallback；SafetyLease 失效禁正常关节候选；HAL writer 失效设备拒收，实际输出依赖硬件保护。遥控抢占导航必须撤旧租并确认停车，不能仅把 source priority 改成 90。
<!-- END_V12: P1-D2.5-FOUR-KEYS -->

`ControlLease` 是某个运动资源的独占控制权，独立于 `Session` 与 `SafetyLease`：

`IDLE → REQUESTED → GRANTED → RENEWING → REVOKING → REVOKED/EXPIRED`

- 正常运动同时要求：有效 Session + 有效 ControlLease + 有效 SafetyLease + HAL normal writer lease；
- 同一 scope 任一时刻最多一个 `GRANTED/RENEWING` owner；
- 抢占必须先撤旧租、停车/保护确认，再授予新 owner；
- 失租时按 Action 类型降级：四轮制动、Q2B/B2Q phase fallback、Balance 走已验证安全平衡/降能、无资产则 HAL 保护。

### D2.6 Q1–Q3 裁决

| 问题 | 决策 | 替代方案 | 切换条件 |
|---|---|---|---|
| Q1 抽象 | Behavior→Action→Bundle→Runner | 仅 Behavior+Scope | 永远没有组合/过渡可裁剪 Bundle |
| Q2 进程 | Gateway+Worker+RT+Safety | 单进程多线程 | 实时 MCU + 完整故障证明可合并 Worker |
| Q3 双足 | 默认动态平衡接口，静态锁止可替换 | 全 ClassicalPose | 本体证实全工况静态锁止 |

---

**Part 1 完成度：100%（D0–D2 合并稿）；待补：Collie 拓扑、双足支撑、HAL/急停能力、平台 WCET。**



---



<!-- BEGIN_V12: P1-D2-QUIZ -->
#### [V1.2-解释] D2 读完自测

1. 五个限界上下文如何走完站立请求？
2. Form=UNKNOWN 为什么不能 SAFE_HOLD？
3. 四种许可哪一种管资源独占？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P1-D2-QUIZ -->

# Collie 运控服务软件架构 V1.3 — Part 2（D3–D4）

<!-- BEGIN_V12: P2-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：选择动作，并只提交一次

```mermaid
flowchart LR
 G["Gateway：PolicyManager/Graph"] --> W["Worker：Runner/Manifest/候选"] --> R["RT：Epoch/JointMux"] --> H["HAL"]
 V["ControlLease/Session"] -.-> G
 S["SafetyLease"] -.-> R
```

| 解释盒 | 为什么／是什么 | 不是什么 | Running Example | 常见误解 |
|---|---|---|---|---|
| Runner | 不同算法共用 load/enter/step/exit 接口 | 不是一个进程或一个电机 writer | 四轮 ONNX 与 Q2B 使用不同 Runner | 类名不是工厂判据 |
| Manifest | 静态身份、输入输出和守卫合同 | 不是 ONNX 文件本身 | Q2B 无真实资产则 DISABLED | “有模型”不等于可加载 |
| ActionGraph | 合法动作间的有向边 | 不是安全状态图 | Drive→Stop→Q2B | Graph 通过不等于支撑通过 |
| Epoch | RT 本地切换的唯一版本号 | 不是直接给 Worker 切权限 | Q2B 提交后旧 Drive 候选失效 | PREPARE 不等于 COMMIT |
| ControlLease | 正常运动 scope 的独占权 | 不是 SafetyLease/设备 writer | Nav 失租先停车再换 RC | 有优先级不等于可同时授租 |

**小故事**：“变双足”到达 Gateway 时，系统先查 Session/ControlLease/合法边和资源，Worker 提前准备 Q2B，RT 每 5 ms 检查候选/退出判据/SafetyLease/HAL pending，全部满足才换 Epoch；目前 Q2B 未获真实批准，动作入口必须拒绝。

**怎么读 D3/D4**：D3.3 的两维表先按“怎么计算”找行、再按“要完成什么”找列；D4.4 先看“来源权限”，再看租约；D4.5 先分 PREPARE 与 COMMIT。`can_exit` pre-step READY 已知 P0 **未修**。
<!-- END_V12: P2-OVERVIEW-01 -->

> 合并说明：本 Part 以 V1.1 的 `IRunner`、`SealedExitDecision`、二维 Runner 工厂、ModeTransition、PolicyManager/ControlLease 为准；V1.0 的 ActionBundle/切换骨架保留。  
> **审阅注记**：V1.1 的 `can_exit` 在 `step()` 前发布 `READY`，存在“旧 Runner 已故障/进入不可中断相位，RT 仍提交”的竞态；本文保留 V1.1 原设计并在 §D3.5 标注，修法见 `REVIEW_V1.1.md` §2.1。

---

## D3. Runner 框架详细设计

### D3.1 内部 ABI 与插件边界

`IRunner` 是 Worker **进程内**的 C++ 接口；跨进程只用版本化、固定布局 IPC，不传 `std::vector`、虚表或裸指针。首版推荐把已审核 Runner 静态链接进 Worker，避免运行时随意装入第三方 `.so`；若用动态库，必须提供版本化 C 入口工厂。

| 方法 | 调用线程 | 资源/时效 | 前置/后置/失败 |
|---|---|---|---|
| `load()` | Worker loader（非 RT） | 允许模型 I/O 与预分配 | Created、manifest/robot 校验；失败→Faulted，无设备输出 |
| `enter()` | Worker 实例线程 | 不等待外部服务/磁盘 | Loaded/Exited；快照/形态/安全准入有效；失败→Faulted |
| `can_exit()` | Worker 实例线程，**每 tick 在 step 前** | 只读已冻结输入与内部相位；计入 15 ms | 输出 sealed `kind/reason/snapshot_seq/valid_until/retry_not_before`；不得同步 IPC |
| `step()` | Worker 50 Hz | ≤ `worker_budget_ns`；禁止磁盘/无界阻塞 | 返回候选或错误；不保证被 RT 采用 |
| `exit()` | Worker 实例线程 | 不阻塞 RT；大资源释放转 loader | RT 已撤销 Epoch；失败锁存 Faulted |
| `status()` | 非阻塞只读 | 常数时间 | 返回状态副本 |

线程安全：每个 `RunnerInstance` 的 `enter/can_exit/step/exit` 由同一 Worker 线程串行调用；不同实例可并行，但不能共享可写历史/滤波/后端会话。异常必须在 Worker 包装层捕获，不跨 `noexcept` 传播。RT 从不调用 `IRunner`。

### D3.2 类型与 C++ 签名

```cpp
using TimeNs = uint64_t;
using ActionEpoch = uint64_t;
using TickId = uint64_t;
using JointMask = uint64_t;   // 首版 ≤64 关节

enum class Errc : uint32_t {
  Ok=0, InvalidManifest=1001, TopologyMismatch=1002, BadTensor=1003,
  InvalidState=2001, GuardWait=2002, GuardRefuse=2003,
  StaleFeedback=3001, SafetyDenied=3002, Timeout=4001,
  ResourceExhausted=4002, Internal=5001
};

enum class ExitKind : uint8_t { READY=1, WAIT=2, REFUSE=3 }; // 与 proto EXIT_READY/WAIT/REFUSE 对齐

struct ExitDecision {
  ExitKind kind;
  uint32_t reason_code;
  uint64_t snapshot_seq;
  uint64_t valid_until_ns;
  uint64_t retry_not_before_ns;
};
struct SealedExitDecision {
  Uuid boot_id; ActionEpoch action_epoch; Uuid runner_instance_id;
  uint64_t seal_seq; uint64_t snapshot_stamp_ns; ExitDecision data;
};

struct JointTarget {
  uint16_t index; uint8_t mode; bool enabled;
  float q_rad, dq_radps, tau_nm, kp, kd;
};
struct RunnerOutput {
  ActionEpoch epoch; TickId tick_id; TimeNs snapshot_stamp_ns, deadline_ns;
  JointMask owns_mask; uint16_t target_count; JointTarget* preallocated_targets;
  uint16_t phase_id; bool done, exit_ready; uint32_t fault_code;
};
struct StepInput {
  const RobotStateSnapshot& state;
  const MotionReference& reference;
  const TransitionContext& transition;
  TickId tick_id; TimeNs deadline_ns;
};

class IRunner {
public:
  virtual ~IRunner() noexcept = default;
  virtual Status load(const RunnerManifest&, const RobotDescription&, LoadContext&) noexcept = 0;
  virtual Status enter(const EnterContext&) noexcept = 0;
  virtual ExitDecision can_exit(const RobotStateSnapshot&, const MotionReference&) const noexcept = 0;
  virtual Status step(const StepInput&, RunnerOutput&) noexcept = 0;
  virtual Status exit(ExitReason) noexcept = 0;
  virtual RunnerStatus status() const noexcept = 0;
};
```

`JointTarget*` 只在 Worker 内有效；跨 IPC 用固定 `MAX_JOINTS=64` 容量 + 实际 `joint_count`。候选外层 `CandidateHeader` 携带 `manifest_hash/boot_id/epoch/tick_id/snapshot_seq/deadline`。

### D3.3 八类 Runner 与二维工厂（V1.1）

<!-- BEGIN_V12: P2-D3.3-EIGHT-MATRIX -->
#### [V1.2-解释] 八类 Runner 到底是哪八类、怎样唯一选

| 场景 | `(ExecutionKind,BehaviorRole)` | class | 什么时候用 / 为什么 | 不能误用作 |
|---|---|---|---|---|
| 经典四轮 | CLASSICAL,LOCOMOTION | WheelDriveRunner | 经典轮腿速度控制 | ONNX 通用承载 |
| RL 四轮 | ONNX,LOCOMOTION | RlLocomotionRunner | 动态速度策略 | 只因为“Wheel”改类 |
| Q2B/B2Q | ONNX/CLASSICAL/PLAYBACK,TRANSITION | TransitionRunner | phase/接触/退路 | 线性插值过渡 |
| 动态双足 | ONNX/BALANCE 或 CLASSICAL/BALANCE | BalanceRunner | 持续稳定控制 | 静态 Pose 替代 |
| 已确认静态站姿 | CLASSICAL,POSE | ClassicalPoseRunner | 有限姿态/增益控制 | 未知支撑保持 |
| 受限恢复 | ONNX/CLASSICAL,RECOVERY | RecoveryRunner | 安全批准+净空检查 | 用户任意翻身 |
| 轨迹播放 | PLAYBACK,POSE | PlaybackRunner | 已验时标轨迹 | 持续闭环平衡 |
| 手势 | CLASSICAL/PLAYBACK,OVERLAY | OverlayRunner | 仅不冲突 mask | 覆盖 Balance 的承重臂 |

**选择方法**：确定训练/经典/轨迹机制→确定行为角色→在 Registry 查 **唯一** class/backend 白名单→检查 Manifest/资产签发/owns_mask→实例化。二维格不等于 24 个可用实现；同一个 TransitionRunner 可以承载多种 backend。所有 Q2B/B2Q/Balance/Recovery 目前无 Collie 实证资产，仍禁用。
<!-- END_V12: P2-D3.3-EIGHT-MATRIX -->

RunnerManifest 不再只靠 `class_id` 猜算法，而是两个正交字段：

- `ExecutionKind`：`ONNX / CLASSICAL / PLAYBACK / COMPOSITE`
- `BehaviorRole`：`LOCOMOTION / TRANSITION / BALANCE / POSE / RECOVERY / OVERLAY`

| kind \ role | LOCOMOTION | TRANSITION | BALANCE | POSE | RECOVERY | OVERLAY |
|---|---|---|---|---|---|---|
| ONNX | RlLocomotionRunner | TransitionRunner | BalanceRunner | — | RecoveryRunner | OverlayRunner |
| CLASSICAL | WheelDriveRunner | TransitionRunner | BalanceRunner | ClassicalPoseRunner | RecoveryRunner | OverlayRunner |
| PLAYBACK | — | TransitionRunner | — | PlaybackRunner | — | OverlayRunner |
| COMPOSITE | — | TransitionRunner | — | — | — | OverlayRunner |

工厂规则：`(execution_kind, behavior_role) → class_id` 唯一；`backend_id` 必须在白名单；不匹配直接 `MANIFEST_CLASS_MISMATCH`，不做模糊回退。四轮 ONNX 策略选 `(ONNX, LOCOMOTION) → RlLocomotionRunner`，`behavior_id` 仍是四轮移动；不要因为类名不是 `WheelDriveRunner` 就认为角色不同。

### D3.4 八类 Runner 接口卡

| Runner | 参考/反馈 | 输出/所有权 | 进入/退出/完成 | 失败/必交资产 |
|---|---|---|---|---|
| WheelDriveRunner | vx/vy/wz；轮速/腿/IMU/接触 | 腿+轮位置/速度/力矩，mask 声明 | 四轮支撑稳定进入；零速/滑移/姿态稳定退出 | 滑移/反馈异常→停车/安全；轮腿映射、速度域、Obs/ActionSpec、制动包络 |
| RlLocomotionRunner | 速度参考、关节/IMU、历史动作、观测历史 | 模型定义的逐关节目标 | 张量有效/预热；按停止/接触窗退出 | 超时/NaN→无候选；模型、tensor IO、逐维规格、Golden |
| ClassicalPoseRunner | 姿态/高度、关节/IMU | 位置+增益，必要时轮制动 | 姿态包络；误差/低速保持窗 | 超时/过流→SAFE；插值曲线、增益、限位、完成窗 |
| TransitionRunner | Q2B/B2Q 请求、phase 参考、关节/IMU/接触/轮速 | 相位相关目标，通常独占承重关节 | 初态包络+净空；阶段判据；终态接触/姿态保持 | 失败只走 phase 可行回退或 DAMPING；相位表、模型/轨迹、phase guard、超时/回退、Golden |
| BalanceRunner | 姿态/速度、IMU、轮接触、关节/估计 | 承重/姿态目标 | 双足支撑有效；可退出需姿态/轮速满足 | 失衡→保护；动态支撑域、失稳阈值、输出模式、扰动测试 |
| RecoveryRunner | 安全授权、倒地方向、净空、反馈 | 受限恢复轨迹/策略 | 安全授权+场地清空；固定重试上限 | 超时/净空变化→DAMPING；可恢复姿态集、次数、Golden |
| PlaybackRunner | `.mref` 时标/关节参考、反馈 | 轨迹目标、限定 mask | 起点误差/速度；时间轴完成+跟踪误差稳定 | 越界/超时→停用；轨迹、采样、增益、校验和 |
| OverlayRunner | 手势/头臂参考、主 Runner 稳定态、关节反馈 | 仅拥有的局部 mask | 主动作允许组合、mask 不冲突；主退出前撤销 | 冲突/失联→同步取消；组合白名单、返回中性、时间窗 |

首版对 Q2B/B2Q/Balance/Recovery/表演 `enabled=false`；缺 Collie 资产和物理证据时任何调用返回 `ACTION_NOT_RELEASED`，不能用 T1 资产替代。

### D3.5 `enter / can_exit / step` 契约

**V1.1 决策**：Worker 每 20 ms tick 在 `step` 前计算 `can_exit` 并封存 `SealedExitDecision`；RT 每 5 ms 只读 mailbox，校验 `boot/epoch/runner_instance/seal_seq/snapshot_seq/valid_until`，不等待 Worker。

```cpp
// Worker：先算退出，再发布，再跑 step（V1.1 原设计）
void RunnerWorker::on_20ms_tick(const StepInput& in) noexcept {
  const auto now = in.state.snapshot_robot_time_ns;
  ExitDecision d;
  if (refuse_latched_) d = {ExitKind::REFUSE, REASON_LATCHED, 0, 0, 0};
  else if (last_exit_.kind == ExitKind::WAIT && now < last_exit_.retry_not_before_ns)
    d = {ExitKind::WAIT, last_exit_.reason_code, 0, 0, last_exit_.retry_not_before_ns};
  else d = runner_.can_exit(in.state, in.reference);
  d.snapshot_seq = in.state.snapshot_seq;
  d.valid_until_ns = min(now + 25'000'000ULL, config_.exit_decision_ttl_deadline_ns(in.state));
  d.retry_not_before_ns = (d.kind == ExitKind::WAIT)
      ? max(d.retry_not_before_ns, now + 25'000'000ULL) : 0;
  if (d.kind == ExitKind::REFUSE) refuse_latched_ = true;
  last_exit_ = d;
  publish_sealed_exit(boot_id_, active_epoch_, instance_id_, ++seal_seq_, d, now);
  (void)runner_.step(in, preallocated_output_); // 可能挂死
}

// RT：每个 5 ms tick，只读，不等待
ExitKind SwitchCoordinator::read_exit_nonblocking(const RtSnapshot& s,
                                 const PreparedSwitch& p, TimeNs now) noexcept {
  SealedExitDecision e;
  if (!exit_mailbox_.try_read_sealed(e)) return ExitKind::WAIT;
  if (e.boot_id != boot_id_ || e.action_epoch != active_.epoch ||
      e.runner_instance_id != active_.runner_id) return ExitKind::WAIT;
  if (e.data.snapshot_seq > s.snapshot_seq ||
      (s.snapshot_seq - e.data.snapshot_seq) > 4ULL) return ExitKind::WAIT;
  if (now > e.data.valid_until_ns || now < e.snapshot_stamp_ns ||
      (now - e.snapshot_stamp_ns) > 25'000'000ULL) return ExitKind::WAIT;
  if (active_.exit_refuse_latched) return ExitKind::REFUSE;
  if (e.data.kind == ExitKind::REFUSE) { active_.exit_refuse_latched = true; return ExitKind::REFUSE; }
  if (e.data.kind == ExitKind::WAIT) return ExitKind::WAIT;
  return current_rt_support_guard(s) && target_preflight_valid(p,s)
      ? ExitKind::READY : ExitKind::WAIT;
}
```

> **审阅注记（P0 残留）**：`can_exit` 在 `step` 前发布 `READY`。如果 `step` 把相位推进到不可中断、输出 NaN/fault、或挂死，RT 仍可能在 `valid_until`（25 ms）内用“上一步的 READY”提交新 Epoch。现有 `test_exit_worker_hang_50ms_rt_not_block` 只测“无决策”，没测“先 READY 再挂死”。建议 V1.3：`READY` 只在 `step` 成功返回后发布；或给 `SealedExitDecision` 加 `last_completed_step_seq/phase_seq/fault_seq`，RT 只接受“最近成功 step”的 `READY`，step 进行中/挂死强制 `WAIT`。详见 `REVIEW_V1.1.md` §2.1。

### D3.6 历史与状态保留

每个 `RunnerInstance` 独占 `RunnerContext`：Obs 历史、滤波状态、`previous_action`、RNN hidden、Transition phase。`enter` 按 manifest `initial_fill` 重置；`exit` 冻结/销毁。跨策略保留只允许 manifest 明示且 ObsSpec hash/频率/坐标/历史顺序一致。`ActionEpoch` 由 RT 单调递增；`Safety fault latch` 不随 Runner 改变。

### D3.7 三条关键时序

<!-- BEGIN_V12: P2-D3.7-ARROWS -->
#### [V1.2-解释] 三图该从哪条箭头读起

| 图 | 先看参与者 | 核心 1→2→3→4→5 | 必须补上的失败支路 |
|---|---|---|---|
| 正常单拍 | HAL/RT/Worker/Inference | 反馈→Snapshot→Obs/推理→候选→RT Guard/HAL | Worker 慢/NaN/旧 epoch→丢弃，不阻塞 RT |
| Q2B 切换 | Task/Policy/Worker/RT/HAL | 请求→Graph路径→目标预热→`PREPARE_EPOCH`→RT提交 | 任一 guard/ACK/Lease 失效→WAIT 或保护 |
| 急停/反馈过期 | EStop/Safety/RT/HAL | 硬件直接保护→Safety锁存→撤Lease→RT禁候选→设备保护 | RT自身死亡→HAL独立watchdog |

**读图六步**：①找触发者；②看横向参与者；③按纵轴读请求/异步回执；④把每条箭头翻译成具体结构；⑤记住 RT 仍每 5 ms 自己运行；⑥写明超时、拒绝、设备失联分支。50 Hz Worker 与 200 Hz RT 不同步等待；约 1 kHz 驱动是【待定】。

`[V1.2-审阅注记][P0-必须闭环]` V1.1 `D3.5` 在 `step()` 前封存 READY，之后 step 可能进入不可中断 phase/NaN/挂死；RT 即使校验 `valid_until` 仍可能错误提交。必须先补“已 READY→step 挂死50ms/NaN/phase变更→RT 0次提交/旧 Epoch 0次接受”的生产路径测试。推荐只在 `step` 成功完成后发布 READY 并绑定完成/phase/fault 序号；**本补丁仅标注，不修改 V1.1 行为**。
<!-- END_V12: P2-D3.7-ARROWS -->

```mermaid
sequenceDiagram
  participant H as HAL
  participant R as mc_rt
  participant W as Worker
  participant I as Inference
  H-->>R: joint/IMU
  R->>R: snapshot/ref/epoch/deadline
  R->>W: snapshot + ref
  W->>W: Obs + history
  W->>I: named tensors
  I-->>W: outputs
  W-->>R: candidate + SealedExitDecision
  R->>R: epoch/age/Guard/Lease
  R-->>H: HalCommand 200Hz
```

```mermaid
sequenceDiagram
  participant T as Task
  participant P as PolicyManager
  participant R as mc_rt
  participant W as Worker
  T->>P: SetBehavior(BIPED_STAND)
  P->>P: Graph: Drive→Stop→Q2B→Balance
  P->>W: preload/enter targets
  P->>R: Request switch
  R->>R: read sealed can_exit + Guard + Lease + HAL pending_epoch
  R->>R: atomic commit new Epoch
  R-->>T: TRANSITIONING/STABILIZING/RUNNING
```

```mermaid
sequenceDiagram
  participant E as E-stop/Sensor
  participant S as mc_safety
  participant R as mc_rt
  participant H as HAL
  E-->>H: hardware stop (direct)
  E-->>S: latch
  S-->>R: revoke lease
  R->>R: stop accepting candidates
  R-->>H: safety target if applicable
  H->>H: independent protection
```

---

<!-- BEGIN_V12: P2-D3-QUIZ -->
#### [V1.2-解释] D3 读完自测

1. ONNX四轮 Action 对应哪一个 Runner 类？
2. can_exit 的 pre-step READY 为什么仍是 P0？
3. Runner 能在 step 中直接发电机吗？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P2-D3-QUIZ -->

## D4. PolicyManager、ActionGraph、ActionBundle

### D4.1 注册表与预加载

| 注册表 | 主键 | 内容 |
|---|---|---|
| BehaviorRegistry | behavior_id | 业务能力→Action/权限 |
| ActionRegistry | action_id@version | Bundle/Manifest/拓扑/release 状态 |
| RunnerFactoryRegistry | (execution_kind,behavior_role) | class_id/backend/能力 |

加载顺序：RobotDescription/校准 → Bundle/Manifest → 模型/轨迹 SHA 与 Tensor IO → Obs/ActionSpec → mask/组合矩阵 → 预分配 → 预热 → Golden smoke → `AVAILABLE`。`release.status` 与 `runtime.asset_state` 分开：`DISABLED/CANDIDATE/APPROVED` vs `UNLOADED/LOADING/AVAILABLE/ACTIVE/BROKEN`。热加载不在 P0。

### D4.2 ActionGraph

根为 `nodes`（只含 Action，不含 `INIT/SAFE_HOLD/DAMPING/ESTOP/RECOVERY`），边字段 `from/to/cost/guard/max_duration_ms/on_timeout`。安全抢占无条件旁路图。

```yaml
schema_version: '1.1'
nodes: [quad_stand, quad_drive, quad_stop, q2b, biped_balance, b2q]
edges:
  - {from: quad_drive, to: quad_stop, cost: 1, guard: [feedback_fresh],
     max_duration_ms: 1500, on_timeout: DAMPING}
  - {from: quad_stop, to: q2b, cost: 3,
     guard: [support_valid, clearance_token_fresh],
     max_duration_ms: 2000, on_timeout: DAMPING}
```

启动校验：引用存在、Action/Bundle 兼容、guard 已注册、无重复/自环、P1 禁用动作不在 P0 路径、所有边有限 deadline 与故障目标、安全抢占保留。运行期默认带风险权重最短合法路径，但实时 guard 不能被路径权重替代。

### D4.3 ActionBundle 与 Ownership

`ActionBundle = primary + overlay_slots + combination_rules`。必须检查：`primary_mask & overlay_mask == 0`；overlay 之间不重叠；未声明关节 `enabled=false` 或由显式 neutral/fallback owner 提供；同一关节不能同时 POSITION/TORQUE；平衡需要头/臂反作用力时，让 Balance 接收手势参考，而不是第二路覆盖。

Overlay 只在主策略 `RUNNING && stable && allowed` 时进入；主策略退出前先停新 overlay、回中性姿态；超时则阻止普通切换或进安全。运行中禁止动态改所有权，必须新 Bundle + 新 Epoch。

组合矩阵（初版）：QuadStand 允许非承重头/臂；QuadWheelDrive 仅经测试的头/受限臂；QuadStop/Q2B/B2Q 默认拒绝；BipedBalance 仅 mask 不争用且联合验证；Recovery/Safety 只允许内部保护。

### D4.4 请求仲裁、来源与 ControlLease

<!-- BEGIN_V12: P2-D4.4-LEASE-BOUNDARY -->
#### [V1.2-解释] “有优先级”为什么不等于“拿到方向盘”

| 情况 | Gateway 结果 | RT 行为 | 谁兜底 |
|---|---|---|---|
| Nav lease 有效、速度 seq/TTL 有效 | 允许同 scope 的当前 owner | 接纳有效速度参考 | Guard/HAL |
| 遥控请求抢占 | 先 REVOKE Nav、停车/稳定后授权 RC | 在切换窗口禁止两来源同时生效 | Safety/HAL |
| Nav 失联超 TTL | ControlLease 不续或过期 | 无新有效速度，按批准制动 | HAL/硬件 |
| SafetyLease 已过期 | 即使 ControlLease 有效也不能继续正常运动 | 拒绝正常候选 | HAL看门狗 |

ControlLease 的角色是资源仲裁，SafetyLease 是此刻运动许可，HAL writer lease 是对设备的独占写入；三个“Lease”不能合并。
<!-- END_V12: P2-D4.4-LEASE-BOUNDARY -->

| 来源 | Action | Velocity | Overlay | 限制 |
|---|---|---|---|---|
| 硬件急停 | — | — | — | 最高，硬件独立 |
| PlatformSafety | 保护性取消 | 限速/停止 | 取消 | 安全约束不参与普通优先级 |
| 本地授权遥控 | 授权站立/停止 | 是 | 有限 | priority 90，需 ControlLease |
| Task Engine | 是 | 授权会话 | 是 | priority 60，任务级仲裁 |
| 导航/跟随 | 否 | 是 | 否 | priority 50，需任务授权 |
| SDK/App | 经 Task | 经网关 | 经 Task | priority 40，不能直达 RT |

**ControlLease**：`IDLE→REQUESTED→GRANTED→RENEWING→REVOKING→REVOKED/EXPIRED`；字段 `lease_id,session_id,boot_id,owner_source_id,seq,scope,ttl_ms,expires_mono_ns,priority,state`。同一 scope 最多一个 owner；抢占先 `REVOKE` 旧租并确认停车/保护，再授予新租；失租时禁止新速度/新 Action，按 Action 走制动/phase fallback/安全平衡/HAL 保护。TTL 初值 500 ms、续租 ≤150 ms（待压测签发）。

幂等键 `(source_id,session_id,request_id)`；同键不同 payload → `IDEMPOTENCY_CONFLICT`。每 source 最多 8 个 Action 排队，总 32；速度只保留最新 seq；断流按 TTL 制动归零。

### D4.5 原子切换

`REQUESTED → PREPARING → WAIT_EXIT → ENTERING → TRANSITIONING → STABILIZING → RUNNING`。

1. PolicyManager 准备目标 Action/首候选，Worker 完成 `enter`，旧 Action 仍活动；
2. RT 读取旧 Runner 的 sealed `ExitDecision` + 目标首候选 + SafetyLease + HAL `pending_epoch`；
3. 全部有效时 RT 在 5 ms 拍边界原子提交 `active_epoch`，发第一条新 Epoch `HalCommand`；
4. HAL 原子 `pending_epoch→active_epoch`，旧 Epoch 永久失效；
5. 提交后新 Epoch 被拒/ACK 超期/HAL 非 ACTIVE：只能本地保护/撤权，不能普通回旧策略。

`switch_ready=true` 当且仅当：`phase==RUNNING`、物理稳定窗成立、无切换事务、反馈有效、安全允许、`can_exit` 对新快照 READY、overlay 满足退出。

### D4.6 MotionStatus

50 Hz 状态 + 事件。字段以 `proto` 为准：`boot_id/request_id/execution_id/session_id`、`seq/action_epoch/stamp_robot_ns`、`current/target_action`、`phase/transition_phase/form`、`stable/switch_ready/action_done`、`active_primary/overlays`、`effective_velocity/source/age`、`safety_state/latched_fault`、`feedback/inference_age`、`release_id/manifest_sha256`、`control_lease_id/state`、`hal_state/last_ack_seq/last_reject_reason`。`age_ms=UINT32_MAX` 表示未知，不填 0；HAL 失联为 `HAL_UNKNOWN`。

### D4.7 Q4/Q5 裁决

| 问题 | 决策 | 替代方案 | 切换条件 |
|---|---|---|---|
| Q4 过渡 | Q2B/B2Q 各有独立 TransitionRunner、phase、接触/姿态守卫、phase fallback；无资产禁用 | 位置线性插值/倒放 | 本体证实准静态且全 phase 可验证时可用经典 Transition |
| Q5 叠加 | 主/overlay 精确 mask，静态预检 + RT 复核，主退出则 overlay 停 | Scope 粗分/最后写覆盖 | 共享关节改为单个 WBC Runner 消费 overlay 参考 |

---

**Part 2 完成度：100%（D3–D4 合并稿）；待补：Q2B/B2Q 资产与 phase 回退、模式切换物理包络、真实 RT/HAL 时序。**



---



<!-- BEGIN_V12: P2-D4-QUIZ -->
#### [V1.2-解释] D4 读完自测

1. ActionGraph nodes 能放 ESTOP 吗？
2. ControlLease 被抢占时能立刻采用新速度吗？
3. 新 Epoch HAL 拒收能直接回旧 Runner 吗？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P2-D4-QUIZ -->

# Collie 运控服务软件架构 V1.3 — Part 3（D5–D6）

<!-- BEGIN_V12: P3-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：用同一份反馈计算、合成、发令

```mermaid
flowchart LR
 H["HAL 反馈"] --> S["RT Snapshot"] --> O["Worker ObsSpec"] --> I["Inference/Runner"] --> C["ActionCodec"] --> M["RT JointMux/Guard"] --> H
```

| 解释盒 | 为什么／是什么 | 不是什么 | Running Example | 常见误解 |
|---|---|---|---|---|
| Snapshot | 一拍的不可变、带时效反馈 | 不是裸关节数组 | 跟随使用含 age/valid 的 joint+IMU | 数值为零不等于无效 |
| ObsSpec | 按训练定义对齐 tensor | 不是只写输入维度 | 四轮 ONNX 把速度/关节按索引排列 | 历史顺序错模型仍可能返回数 |
| ActionSpec | 将 raw 输出转关节参考 | 不是安全限位 | `sign` 转一次规范方向 | `direction` 不能在 Codec 再执行 |
| JointMux/Guard | 合成所有权并限幅 | 不是“哪个输出最新就用哪个” | 手势不能覆盖承重关节 | Guard 不保证动态站稳 |
| HAL 合同 | 设备端验 seq/epoch/权限/时限 | 不是一个 JointTarget 字段表 | 过期命令拒收不续狗 | 软件 PASS 不等于固件已实现 |

**小故事**：导航产生速度，但 Worker 只接收到有效参考和 Snapshot；在 50 Hz 给出候选。RT 200 Hz 独立检查年龄与安全许可；只有合法目标形成 HalCommand，HAL 才可能让轮转动。断流时旧速度 TTL 失效并进入已批准制动路径。

**怎么读 D5/D6**：D5.7 的 15/20 ms 与 2.1/5 ms 是分开的预算，不能相加当同一同步调用；D6 接口先看字段单位/时效，再看拒收。1 kHz 设备频率与时统/驱动能力为【待定】。
<!-- END_V12: P3-OVERVIEW-01 -->

> 合并说明：本 Part 以 V1.1 的 `SCHEMA_CANON`、`proto`、`HAL_CONTRACT`、16 关节 Obs/Action 示例为准；V1.0 的逐拍链路与接口表保留。  
> 字段唯一权威：`proto/collie_mc_v11.proto`；配置唯一权威：`schemas/*.schema.json`；HAL 唯一权威：`HAL_CONTRACT.md`。

---

## D5. 每拍数据链路

### D5.1 时间、数据身份与单调性

系统同时记录三种时间：

- `sample_mono_ns`：采集设备本地单调时间，用于本机延迟/顺序；
- `robot_time_ns`：跨板同步映射后的统一时基，用于对齐；
- `wall_utc_ns`：只用于审计/显示，禁止用于控制过期判断。

跨板必须实测 PTP 或等效时钟映射的 offset/抖动/失锁；不能假设两台主机的 `CLOCK_MONOTONIC` 可直接相减。时间同步失效时，停止使用需要跨板精确对齐的动态参考；HAL/IMU 的本地安全监控仍须工作。所有关键参考/候选有独立 deadline，不能靠“新消息到达”延长旧数据生命期。

### D5.2 RobotStateSnapshot

Snapshot 是**同一控制拍的不可变输入**，由 RT 预分配双缓冲/序列锁生成；Worker 只读。每类传感器保留采样时刻、seq、年龄、有效位、时间同步质量；全零不等于 invalid。

```cpp
constexpr size_t MAX_JOINTS = 64;
struct JointSample {
  uint16_t joint_index;               // 校验 RobotDescription
  float q, dq, tau;                   // rad / rad/s / N*m（直线关节用 variant）
  float motor_temp_c, winding_temp_c, voltage_v, current_a;
  bool valid;
};
struct ImuSample {
  float quat_wxyz[4];                 // body->reference
  float omega_radps[3];               // body FLU
  float acc_mps2[3];                  // 明确是否含重力
  bool valid;
};
struct RobotStateSnapshot {
  uint64_t boot_id_hi, boot_id_lo, tick_id;
  uint64_t snapshot_seq;              // V1.1 新增；同一 boot 内 == tick_id
  uint64_t snapshot_robot_time_ns;
  uint32_t joint_count;
  JointSample joints[MAX_JOINTS];
  ImuSample imu;
  uint64_t joints_sample_ns, imu_sample_ns, contacts_sample_ns;
  uint64_t joints_age_ns, imu_age_ns, contacts_age_ns;
  uint64_t joint_valid_mask;
  uint32_t form, support_state, estimator_quality;
  float wheel_slip_ratio[4];
  uint32_t fault_bits;
};
```

| 输入 | 默认对齐 | 失效判据（初始建议） | 反应 |
|---|---|---|---|
| 关节 q/dq/tau | 按 joint_index 映射；相同 producer_seq 不重复用新帧 | age>15 ms、序号倒退、缺失承重关节、NaN/Inf | Snapshot invalid；Guard 禁正常输出 |
| IMU | 四元数归一化/范数检查；相邻有效才 slerp，否则最近有效+年龄 | age>15 ms、方向非法、不同步、NaN/Inf | Balance/过渡禁用；按形态保护 |
| 接触/支撑 | 明确估计器版本/置信度/延迟 | age>30 ms 或低可信 | 禁依赖支撑的新进入/转换 |
| 机身速度/里程计 | 估计器值+协方差/质量/stamp，不用期望速度代替 | 时基不可信/质量不达标 | 降级或拒绝该 Action |
| 温度/电压/电流 | 设备序号与健康；允许慢更新但不延缓严重故障 | HAL/本体标定；断流 invalid | Safety/HAL 降级、驱动保护 |
| 避障/净空许可 | source/场景/范围/issued/expiry/签名 | TTL 到期/形态不匹配 | 新过渡拒绝或撤销授权 |

对齐优先用 `snapshot_robot_time_ns` 前后包围样本显式插值；不得为掩盖断流任意外推。超过 `max_age` 拒绝关键观测；optional 维度也必须与训练一致的 `missing_policy`。Snapshot 建立后不再修改；双缓冲写方等待无读者或版本化环形块，不能覆盖 Worker 正在读的内存。

### D5.3 ObservationBuilder 与 ObsSpec

```mermaid
flowchart LR
  H["HAL 反馈 joint/IMU/contacts"] --> S["Snapshot：时间+有效性"]
  C["VelocityArbiter"] --> R["MotionReference：来源+TTL"]
  S --> M["Name→index / 关节映射"]
  R --> X["坐标变换+速度整形"]
  M --> F["训练定义的滤波"]
  F --> B["ObsSpec 逐块构造"]
  X --> B
  P["Runner 私有历史/prev_action"] --> B
  B --> V["finite/单位/clip/scale/shape"]
  V --> T["命名 tensor + 历史帧"]
  T --> I["InferenceBackend"]
```

**ObsSpec 21 列**：

`tensor_name,index,block,element,source,source_field,joint_or_axis,unit,frame,transform,offset,scale,clip_min,clip_max,filter_id,history_lag,history_order,include_current,initial_fill,missing_policy_ref,dtype`

- `transform`：`IDENTITY / CENTER_SCALE_CLIP / SCALE_CLIP / ANGLE_WRAP_SCALE_CLIP / QUAT_TO_GRAVITY_SCALE_CLIP`；`CENTER_SCALE_CLIP` 为 `clamp((x-offset)*scale,min,max)`。
- `history_order`：`OLDEST_TO_NEWEST/NEWEST_TO_OLDEST`；`include_current` 严格 boolean；`history_lag=0` 表示当前 Worker tick；`initial_fill`：`REPEAT_FIRST/ZEROS/REFERENCE/ASSET`。
- `missing_policy_ref` 指向已批准策略（如 `STRICT_INVALID`），不得运行时填零；跨板不同步直接 INVALID。
- `(tensor_name,index)` 唯一且 0 连续；总数与 tensor IO 声明一致；同一 joint 明确 `source_field=q`，方向在 SensorAdapter 归一化。

### D5.4 InferenceBackend

启动检查：模型 SHA256/签名、backend ABI、provider/opset、tensor 逐名称/shape/dtype、量化参数、最大内存、输出有限性；预热至少 N=100 次（建议），记录 p50/p99/max；首版同模型会话串行推理。GPU/NPU 若有非确定性延迟、异步阻塞或设备 reset，不得直接进 RT；Worker 可崩溃隔离。超时调用不能保证中断 ONNX，依赖 RT 丢弃过期候选。运行时版本切换只在安全状态完成，回退到已签名上一完整 Release。

### D5.5 ActionCodec

```cpp
for (size_t i=0; i<spec.action_dims; ++i) {
  const auto& ch=spec.channels[i]; // joint/index/mode/sign/scale/default...
  float a0 = activate(raw[i], ch.activation);
  float a1 = clamp(a0, ch.raw_clip_min, ch.raw_clip_max);
  float a2 = float(ch.sign) * a1;             // 仅一次：模型输出→规范关节方向
  float value = ch.default_value + ch.scale * a2;
  switch(ch.mode) {
    case POSITION: out[ch.index].q_rad = value; break;
    case VELOCITY: out[ch.index].dq_radps = value; break;
    case TORQUE:   out[ch.index].tau_nm = value + ch.tau_ff; break;
    default: return error(UNSUPPORTED_MODE);
  }
  out[ch.index].mode = ch.mode;
  out[ch.index].kp = ch.kp; out[ch.index].kd = ch.kd;
  out[ch.index].enabled = ch.owns;
}
// RobotDescription.direction 仅在 HAL 适配电机命令/反馈边界执行一次。
```

`ActionSpec` 16 列：`tensor_name,tensor_index,joint_name,mode,unit,scale,default,raw_clip_min,raw_clip_max,activation,kp,kd,tau_ff,limit_profile,owns,sign`。

- `sign ∈ {-1,+1}`、`scale>=0`、`activation=IDENTITY/TANH`；`default` 在机器人规范关节坐标系；
- 唯一公式：`activation → raw_clip → sign → default+scale*value`；TORQUE 再加 `tau_ff`；
- `sign` 是“训练输出→规范关节正方向”，Codec 执行一次；`RobotDescription.direction` 是“规范关节→电机坐标”，HAL 执行一次；反馈反向变换也在 HAL 一次；
- `raw_clip` 是模型域处理，不是安全限位；Guard/HAL 另查 q/dq/tau/kp/kd、估计扭矩、变化率、模式。

### D5.6 JointMux、OutputGuard 与 ModeTransition

合成规则：只接受当前 Epoch 的 Primary；Overlay 必须在允许 slot 且 mask 互不重叠；未覆盖关节只能由 Bundle 显式 neutral/fallback owner 提供，不能沿用旧命令；同一关节不能同时 POSITION/TORQUE；平衡需头/臂反作用力时，走 Balance 参考输入，不让 Overlay 覆盖。

Guard 检查：安全授权/ESTOP、反馈新鲜度、输出身份/时效、数值有限性、位置/速度、加速度/jerk/步进、力矩/电流/温度、控制模式/增益、支撑/形态/切换、HAL 写权限/确认。失败按 `form × support × fault` 查验收表；无有效替代则 HAL/硬件保护；软件不能用“循环保持旧目标”实现无限期安全保持。

**ModeTransition（V1.1）**：在 JointMux 与 OutputGuard 之间增加 `ModeTransitionEngine`，仍属 `mc_rt`，不增加进程：

```cpp
struct ModeTransitionPlan {
  uint64_t mode_plan_id;
  JointMask joint_mask;
  ControlMode from_mode, to_mode;
  uint64_t window_ns;
  float max_command_q_rate_radps;
  float max_command_dq_rate_radps2;
  float max_tau_rate_nmps;
  float max_kp_rate_per_s, max_kd_rate_per_s;
  uint32_t stable_window_ms;
  ControlMode approved_rollback_mode;
  uint32_t phase_id;
};
```

状态：`HOLD_OLD → RAMP_DOWN → NEUTRAL_TRANSFER → RAMP_UP → VERIFY → ACTIVE_NEW`，失败 `ROLLBACK/FAULT`。`u=clamp((t-t0)/window,0,1)`，`r(u)=3u²−2u³`；逐 5 ms 再强制 q/dq/tau/kp/kd 变化包络。模式位只在 `NEUTRAL_TRANSFER` 切换；HAL 必须异步 `PREPARE_MODE` 并以同一 `mode_plan_id` 原子接受首帧。没有 plan 的 mode 对直接 `MODE_TRANSITION_NOT_APPROVED`；Q2B/B2Q 每个 phase 必须声明 `mode_before/mode_after/plan_ref`，未批准不运行。

### D5.7 20 ms/200 Hz 预算

<!-- BEGIN_V12: P3-D5.7-TIME-READ -->
#### [V1.2-解释] 20 ms 控制链不等于“推理后才运行 5 ms RT”

```text
Worker: |—— Obs 0.8 —— Model ≤12 —— Codec 0.5 —— 其余 ≤1.7 ——|（15 / 20ms【建议】）
RT:     |—— 2.1 / 5ms ——|      |—— 2.1 / 5ms ——|      |—— ... ——|
HAL:    |—— 目标设备循环约1ms【待定】——|...  不接受非法seq/epoch/deadline
```

RT 只读**已就绪且未过期**候选；Worker 在 RT 第一次取数时仍算着也不会被等待。超过 `deadline` 后丢弃候选，旧候选只能在获批 `max_hold_ns` 内使用并整形，之后走安全路径。2.1/15 ms 是各自线程预算，**不是 Collie 实测 WCET**。
<!-- END_V12: P3-D5.7-TIME-READ -->

| 阶段 | 预算 | 超期 |
|---|---:|---|
| 快照接收/格式检查 | 0.2 ms | 当前 tick 无效 |
| 观测+历史+滤波 | 0.8 ms | 推理无效 |
| 模型计算/同步 | 12.0 ms | 丢弃过期输出 |
| ActionCodec | 0.5 ms | 候选无效 |
| Overlay 计算 | 0.6 ms | 取消 Overlay；primary 依赖则整包失败 |
| 有限性/守卫/发送 | 0.9 ms | 不发布候选 |
| **合计** | **15/20 ms** | 5.0 ms 裕量 |

RT 5 ms 预算：Snapshot 0.2、校验 0.2、仲裁/整形 0.15、候选/epoch 0.2、Mux 0.25、整形/增益 0.35、Guard 0.30、HAL 发布 0.25、统计 0.20 = **2.10/5 ms**，保留 2.9 ms。Worker 截止与 RT 周期不完全对齐；端到端最大时延必须由 timestamp 回放/示波器测量。两次发布之间只允许在 manifest `max_hold_ns` 内使用上一个有效候选并整形；超出年龄/Epoch/反馈无效立即失效。

### D5.8 内存与零拷贝

HAL 反馈 rings、Snapshot rings、Tensor I/O、Runner history/filter、Candidate buffers、Guard/Joint command、黑匣子 rings 全部启动/加载时预分配。RT→HAL 专用 SHM 固定槽位+序号+CRC/length；RT 不动态分配/不加锁/不写盘；黑匣子满时丢旧非关键记录并计数，不阻塞 RT。

---

<!-- BEGIN_V12: P3-D5-QUIZ -->
#### [V1.2-解释] D5 读完自测

1. Snapshot 为什么需要每源时间戳？
2. sign 与 RobotDescription.direction 分别在哪执行？
3. RT 为什么不能等 15ms Worker 推理结束？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P3-D5-QUIZ -->

## D6. 上下游字段级接口

### D6.1 对外收敛

<!-- BEGIN_V12: P3-D6.1-HAL-BRIDGE -->
#### [V1.2-解释] 从领域目标到设备合同差了什么

`JointTargetArray` 只是规范关节目标；`HalCommand` 除 joints，还必须有 `boot_id/writer_id/seq/action_epoch/deadline_ns/payload_crc/mode_plan_id`，设备用它确认**由谁、在什么版本、什么期限内**接管。`HalStatus` 带 `ack_event_seq/seq_ack/accepted/reject_reason/hal_state/active_epoch/watchdog_state`；拒收不能续狗。

| 看起来相似的字段 | 唯一使用场合 | 不得混用 |
|---|---|---|
| `RequestHeader.timeout_ms` | 外部 RPC 相对超时，Gateway 收到后一次换算 | 不能冒充内部 `deadline_ns` |
| `ScheduledAction.deadline_ns` | Gateway/RT 相容单调时钟的绝对截止 | 不跨不同主机单调时钟直接相减 |
| `BodyVelocityRef.ttl_ms` | 速度来源有效窗 | 不等于 SafetyLease 30 ms |
| `ActionEpoch` | 当前普通 Action 接管版本 | 不是 ControlLease seq |

唯一协议事实源：`proto/collie_mc_v11.proto`；唯一 HAL 行为合同：附录 A。
<!-- END_V12: P3-D6.1-HAL-BRIDGE -->

**四个稳定 RPC**：`SetBehavior`（primary + overlay）、`SetVelocity`（低频/SDK 配置入口；高频速度仍走 Topic）、`GetState`、`SetSafety`（只有可信本地 Safety/Admin 可设更严格限制；普通用户只能 TriggerStop，不能解 ESTOP）。**两个流**：`MotionStatus` 50 Hz、`MotionEvent` 事件。内部仍保留 `ActionRequest/BodyVelocityRef/OverlayRequest` + 独立 `SafetyEvent`。

| 方向 | 接口 | 传输/频率 | 关键字段 | 失败 |
|---|---|---|---|---|
| 任务→MC | `SetBehavior → ActionRequest` | RPC，事件，受理≤20 ms | `request_id,session_id,source_id,action_id,params,timeout_ms,preempt_mode,idempotency_hash,control_lease_id` | REJECTED/QUEUED/ACCEPTED；完成看 Event/State |
| 任务→MC | `OverlayRequest` | RPC，事件 | `motion_id,slot,owns_mask,interrupt,timeout_ms` | 无主动作稳定/冲突→REJECTED |
| 导航/遥控→MC | `BodyVelocityRef` | DDS Topic（可经 SetVelocity） | `source_id,session_id,control_lease_id,seq,stamp_robot_ns,ttl_ms,frame_id,vx,vy,wz` | seq/权限/TTL 错拒收；过期制动归零 |
| 平台安全→MC | `SafetyEvent/SetSafety` | 可信 IPC/RPC/事件 | `kind,severity,latched,source,stamp,reason,nonce` | 立即撤销许可/升级；复位单独流程 |
| MC→HAL | `HalCommand` | 单写者 SHM，200 Hz | `boot_id,writer_id,seq,action_epoch,deadline_ns,payload_crc,joint_count,joints,mode_plan_id` | 过期/非法拒收；HAL watchdog |
| HAL→MC | `JointStateArray/IMU` + `HalStatus` | SHM，200–1000 Hz | 关节/IMU + ack/seq/epoch/watchdog/fault | 缺失/过期/倒退→Snapshot invalid |
| MC→Task/HMI | `MotionStatus` | DDS，50 Hz | 见 D4.6 | 上游 TTL 后标 UNKNOWN |
| MC→Task/HDS | `MotionEvent` | DDS+审计 | `execution_id,from_phase,to_phase,reason,trace_id` | 丢消息可用 GetState 重建 |

`RequestHeader.timeout_ms` 是外部相对时间；Gateway 接收时换算 `ScheduledAction.deadline_ns`；重试不延长 deadline；跨未同步计算单元不比较 monotonic。

### D6.2 领域 IDL 与 ROS 映射

`proto/collie_mc_v11.proto` 是消息字段唯一源；C++ 代码由 proto 生成，文档不再手写第二版结构。ROS2 侧建议包 `collie_mc_interfaces`：`SetBehavior.srv`、`BodyVelocityRef.msg`、`SafetyEvent.msg`、`MotionStatus.msg`、`MotionEvent.msg`；T1 `SetMcAction/McLocomotionVelocity` 只在兼容 Adapter 中映射。

明确边界：ROS2/DDS executor 只在 Gateway/桥接进程处理回调；不得直接触发 RT 模型计算或写 HAL；跨 RT 结构用 schema 生成固定布局或校验过的 IPC，禁止把 ROS msg 裸指针塞进 Runner。

### D6.3 错误码

`uint32` 分段：

| 段 | 范围 | 例子 | 客户端动作 |
|---|---|---|---|
| 参数/协议 | 1000–1999 | INVALID_ARGUMENT/SCHEMA_MISMATCH/IDEMPOTENCY_CONFLICT | 修参数/升级接口 |
| 运行状态 | 2000–2999 | INVALID_ACTION_STATE/EDGE_NOT_ALLOWED/GUARD_WAIT | 订阅阶段/选合法动作 |
| 安全/权限 | 3000–3999 | SAFETY_DENIED/E_STOP_LATCHED/SOURCE_UNAUTHORIZED/STALE_FEEDBACK | 不自动重试运动 |
| 资源/时效 | 4000–4999 | RESOURCE_BUSY/DEADLINE_EXCEEDED/ASSET_NOT_RELEASED/OUTPUT_STALE | 按 retry_after；危险动作不自动重试 |
| 内部/设备 | 5000–5999 | INFERENCE_FAILED/HAL_REJECTED/INTERNAL_ERROR | 记录 trace，转安全/维护 |

`ACCEPTED` 只表示受理，不代表站稳；`QUEUED` 未执行；`REJECTED` 没有活跃动作。

### D6.4 幂等、背压、断流

- 幂等键 `(source,session,request_id)`；同 payload 返回原 execution_id；不同 payload → `IDEMPOTENCY_CONFLICT`；
- source seq 严格递增，重启需新 session/boot；旧包不能覆盖新包；
- Action 每 source 最多 8，总 32；超限拒绝；速度只保留每 source 最新 seq；
- 导航/遥控 TTL：50 Hz 遥控 100 ms、10 Hz 导航 250 ms（初始建议）；过期按制动包络归零；
- 安全事件升级可重复、原因锁存；复位单独鉴权；HAL 断流由独立 watchdog 拒收旧命令。

### D6.5 来源权限

| 角色 | SetBehavior | Overlay | Velocity | SetSafety | Reset ESTOP |
|---|---|---|---|---|---|
| Task Engine | 是，受允许集 | 是，受组合矩阵 | 资源会话内 | 仅请求升级 | 否 |
| 物理遥控 | 停止/授权模式 | 白名单 | 是，独立 ControlLease | 仅请求保护 | 否 |
| 导航/跟随 | 否 | 否 | 是，任务资源租约 | 请求停止 | 否 |
| App/SDK | 经 Task | 经 Task | 经授权桥接 | 仅安全升级 | 否 |
| PlatformSafety | 保护性取消 | 撤销 | 限制/禁止 | 是，升级/限制 | 按系统流程，不能单方清硬件锁存 |
| 维护/调试 | 离线/举升授权 | 受限 | 受限 | 独立硬件确认 | 双因素/物理确认，仍需硬件复位 |

### D6.6 坐标系、单位、模式

`base_link` FLU：X 前、Y 左、Z 上；`vx/vy` m/s、`wz` rad/s 右手；非 base_link 速度必须经时间戳 TF，无可靠变换直接拒绝。IMU 四元数固定 `wxyz` 与变换方向；关节角按 RobotDescription 正方向。温度 ℃、电流 A、电压 V；轮速 rad/s。`kp` 转动关节 N·m/rad，`kd` N·m·s/rad。每个动作输出明确 `POSITION/VELOCITY/TORQUE/DAMPING/PASSIVE`；轮式连续关节不能假装有普通角度软限位；`enabled=false` 不等于已验证安全卸力。

### D6.7 Q6/Q8/Q10 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q6 接口 | 4 RPC + 2 stream；内部三类领域输入 + SafetyEvent | 全 Topic/每 Runner RPC | 非 ROS 客户端占主导时加 gRPC gateway，内部不变 |
| Q8 推理 | CPU ONNX Runtime 首版；命名多输入/多输出；Worker 隔离、预热、SHA、限时 | GPU/NPU/进程内同步 | CPU WCET 不达标且加速后端确定性通过 |
| Q10 规格 | 逐维 ObsSpec/ActionSpec + Golden；历史实例私有 | 只约定 N 维/ONNX | 自描述模型元数据仍需生成同等逐维合同 |

---

**Part 3 完成度：100%（D5–D6 合并稿）；待补：真实模型逐维规格、硬件时统、HAL 最终 schema、模式切换物理包络。**



---



<!-- BEGIN_V12: P3-D6-QUIZ -->
#### [V1.2-解释] D6 读完自测

1. timeout_ms、deadline_ns、ttl_ms 有何区别？
2. HalCommand 比 JointTargetArray 多哪类字段？
3. 失 ACK 后为什么不能重发相同 seq？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P3-D6-QUIZ -->

# Collie 运控服务软件架构 V1.3 — Part 4（D7–D8）

<!-- BEGIN_V12: P4-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：任何一步失败，谁还能保护

```mermaid
flowchart TB
 P["PlatformSafety：系统许可"] --> S["mc_safety：SafetyLease"] --> R["mc_rt：OutputGuard"] --> H["HAL watchdog/driver"] --> E["硬件急停/电气链"]
 W["Worker 可能故障"] -.->|"失效候选"| R
```

| 解释盒 | 为什么／是什么 | 不是什么 | Running Example | 误解 |
|---|---|---|---|---|
| INIT/UNKNOWN | 未确认支撑先禁正常保持 | 不是“自动姿态锁定” | 开机不执行 SAFE_HOLD | disabled 也可能跌倒，必须分析 |
| SafetyLease | 让安全核失活后正常输出失去许可 | 不是 30ms 的物理急停保证 | 跟随遇 IMU 故障撤租 | 软件和硬件截止不同 |
| OutputGuard | 拒绝非法目标和超期候选 | 不是防所有接触事故的算法 | NaN 拒绝，不继续正常转轮 | 有限值不代表动力学可行 |
| HAL watchdog | RT 死后设备自保的合同 | 不是 Supervisor 重启脚本 | kill RT 不保持最后命令 | 需要设备 HIL/示波器证据 |
| WCET | 控制线程最坏耗时的要求 | 不是 p99 延迟 | 5ms RT 预算 2.1ms【建议】 | 24h无超期≠数学证明 |

**小故事**：B2Q 中急停，硬件链不等 Worker/RT；Safety 锁存、RT 停常规候选、HAL 自保。复位返回 INIT/UNKNOWN 而不是继续旧 phase。

**怎么读 D7/D8**：D7 的“检测/反应/残余风险”三列必须连读；D8 的“周期/超时/核”都属于【目标建议】，不是已测。任何没有批准的保护姿态都不能称 SAFE_HOLD。
<!-- END_V12: P4-OVERVIEW-01 -->

> 合并说明：本 Part 以 V1.1 的 `INIT/UNKNOWN`、HAL 合同、Safety 独立核 S0/FIFO92、Epoch 两阶段与 watch dog 为准；V1.0 的危害/FMEA/八故障走查保留。  
> 安全边界：软件合同不等于硬件安全；`SAFE_HOLD`、`HAL_SAFE_OUTPUT`、独立 watchdog 的物理有效性必须由 HAL/电气/本体 HIL 证明。

---

## D7. 安全目标、失效模型及防线

### D7.1 安全目标与危害

目标：避免接触伤害、限制失控运动、保留故障可追踪性、在单一软件故障下避免无限继续输出旧命令。**不能承诺所有故障都可避免跌倒**：动态双足掉电、无姿态反馈、失去支撑时不存在通用安全保持姿态；DAMPING、零力矩、刹车、抱死的风险取决于物理位置、旁人距离、轮胎/关节构造。

| H# | 危害/后果 | 触发示例 | 保护目标 | 残余风险 |
|---|---|---|---|---|
| H01 | 跌倒/砸人 | 双足失稳、接触错误、地滑 | 及时撤销危险运动、限制恢复 | 双足跌落能量不能由软件消除 |
| H02 | 失控移动/撞人 | 速度源断流、源切换竞态 | 有界制动时间/距离 | 下坡/低摩擦可能停不住 |
| H03 | 超速/高速冲击 | 原始动作超限 | HAL/Guard 逐关节速度/加速度/变化率 | 物理惯量滞后 |
| H04 | 机械越界/关节损伤 | 错误关节顺序、绝对位置 | 软限位+驱动限制 | 错标定使软件限位也错 |
| H05 | 过流/过温/堵转 | 高增益、碰撞、长时间高扭矩 | 驱动保护+控制律力矩预算 | 温度估算偏差、过流瞬态 |
| H06 | 通信断流/实时停顿 | Worker/RT/HAL/总线挂死 | 各层独立截止/看门狗 | 总线最后一帧可能被固件保持 |
| H07 | 模型/观测异常 | NaN、张量错位、错误权重 | 加载校验+Golden+运行时有限性/范围 | 错误但数值有限的输出 |
| H08 | 非法/重放请求 | 越权 SDK、旧速度包、恶意模型 | 鉴权、序号/时间、签名 | 凭证泄露、内部威胁 |
| H09 | 形态切换夹伤 | Q2B/B2Q 有人靠近、支撑不稳 | 进入净空许可+阶段守卫 | 盲区/误报、无法停在任意相位 |
| H10 | 意外恢复运动 | 急停后旧 Action 自动恢复 | ESTOP 锁存、人工复位、新 Epoch | 操作者判断错误 |

### D7.2 FMEA（设计版）

不填虚构 RPN；真实严重度/概率/可检测性由产品/功能安全/本体签发。

| 失效 | 第一检测 | 反应（不等推理） | 更低层兜底 | 残余/验收 |
|---|---|---|---|---|
| Worker 卡 ONNX | RT 候选 deadline；Supervisor | 不采用旧输出，Guard 进入批准保护 | HAL 命令超时 | 保护姿态受限；无限阻塞注入 |
| RT 线程挂死 | HAL `seq/deadline` watchdog | HAL 拒收/设备保护 | 驱动器/硬件安全链 | HAL 缺陷；杀 RT/占核测试 |
| IMU/关节过期/倒退 | Snapshot + SafetyKernel | 关键观测 invalid，撤销许可 | HAL 反馈 watchdog | 假时间戳仍需传感器自检 |
| Runner NaN/Inf | Worker/RT 两次有限性 | 拒绝整个有影响候选 | Guard/驱动模式限制 | 有限数错误需 Golden 覆盖 |
| 电机过流/过温 | HAL/驱动 + Safety | 降额/停机，锁存 | 驱动器硬限 | 温升惯性，保护曲线需实测 |
| Q2B 接触滑失 | 接触/轮速/姿态 | phase fallback；无回退则保护 | HAL/硬件 | 仍可能倾倒；封闭环境试验 |
| 速度重放/持续旧非零 | Arbiter seq/TTL | 丢弃，按包络减速 | SafetyKernel 时间检查 | 坡面制动不足 |
| 所有权重叠 | Registry + JointMux | 禁止加载/提交 | Guard 只接受单一合成目标 | 需回放验证 |
| 资产签名不匹配 | Release validator | 拒绝激活，保留旧版 | 只读文件/安全启动 | 密钥失窃/供应链 |
| ESTOP 网络被阻断 | 硬件安全输入/本地 Safety | 物理急停直接作用硬件 | 驱动器/安全电路 | 电气共因需安全分析 |
| SafetyKernel 停机 | RT Lease 到期 | 终止正常输出 | HAL watchdog | 共同内核/电源故障 |
| 关节零点/方向错 | 交付映射 Golden/HAL 验收 | 加载拒绝/限能停止 | 硬限位/电流保护 | 软件验证不能排除机械错 |

### D7.3 分层防线

| 层 | 依赖 ONNX | 权限 | 自己失效时下一层 |
|---|---|---|---|
| 平台 Safety/SystemMode | 否 | 业务准入、系统 E_STOP、禁新任务 | MC 自治/硬件链 |
| Runner 自身守卫 | 可选 | 只报告能否进入/退出/候选有效 | JointMux/Guard 拒绝 |
| MotionSafetyKernel | **否** | 本地安全等级、Lease、故障锁存 | RT 发现失租；HAL watchdog |
| OutputGuard (`mc_rt`) | **否** | 唯一正常写 HAL 的命令检查 | HAL 超时独立保护 |
| HAL | **否** | 协议/超时/模式/驱动安全 | 电机驱动/硬件急停 |
| 硬件急停 | **否** | 物理断能/安全停止 | 机械/电气剩余风险分析 |

普通 Action 不能选择 `DAMPING/ESTOP` 作为“特技模式”；请求停止可由上游发起，但保护等级和解除权限受平台/本地安全协议约束。

### D7.4 安全状态机、锁存与恢复

<!-- BEGIN_V12: P4-D7.4-INIT-SAFETY -->
#### [V1.2-图] 起点为何必须是 INIT，而不是 SAFE_HOLD

```mermaid
stateDiagram-v2
 [*] --> INIT
 INIT --> DAMPING: 支撑未知/标定未就绪（设备保护）
 INIT --> SAFE_HOLD: 支撑+姿态+反馈可信
 INIT --> NORMAL: 显式启动许可+全部准入
 NORMAL --> ESTOP: 严重故障/硬件急停
 ESTOP --> INIT: 物理复位+维护授权+自检
 SAFE_HOLD --> DAMPING: 支撑丢失
```

**未知不能“保持”**：未知支撑下发送位置保持可能把错误的力矩压到地面。`INIT/UNKNOWN` 阻断 Q2B/B2Q/Balance/Recovery/Overlay/正常移动。`DAMPING` 也不是 universally safe：设备无已验证阻尼时需要其批准的 `HAL_SAFE_OUTPUT`，并明确倾倒风险。
<!-- END_V12: P4-D7.4-INIT-SAFETY -->

状态：`INIT / NORMAL / DEGRADED / SAFE_HOLD / DAMPING / ESTOP / RECOVERY`。

- 上电/重启/急停复位 → `INIT`，`Form=UNKNOWN`，默认 `enabled=false`/HAL_SAFE；
- 支撑/姿态/反馈确认后才允许 `INIT → SAFE_HOLD`；
- 只有显式 `boot_motion` 且全部准入才 `INIT → NORMAL`；
- `NORMAL → DAMPING` 用于失稳/不可保持；`SAFE_HOLD` 只在 `support_confirmed && form_confirmed && feedback_fresh && hold_controller_approved`；
- `ESTOP → INIT` 需物理复位+维护授权+自检；不得自动回 NORMAL/RECOVERY；
- `DAMPING` 若 HAL 未证明阻尼可用，物理输出为设备保护 disabled，不能假造阻尼控制律。

`SafetyLease` 绑定 `boot_id, safety_epoch, sequence, issued/expire_mono_ns, permitted_mode_mask`；只有本机 SafetyKernel 写，RT 每 5 ms 验证。建议 100 Hz 监护、30 ms Lease；严重故障用独立事件标志快速撤销。Lease 不承诺 30 ms 内检测所有故障；物理急停完全独立。

### D7.5 八种故障走查

| 故障 | 检测 | 反应 | 兜底 | 验收 |
|---|---|---|---|---|
| F01 推理挂死 | RT 候选 deadline | 不阻塞；旧候选只在短 hold 窗内整形；超期 Guard 保护 | HAL watchdog | 挂死 Worker 不拖停 RT；不无限复发旧命令 |
| F02 反馈过期/倒退 | Snapshot/Safety 独立检查 | 标 invalid，不补零；Guard 撤销正常输出；Form 可能转 UNKNOWN | HAL 反馈 watchdog | 单关节/IMU/全部断流有不同 fault_mask |
| F03 输出 NaN/Inf | Worker/RT 两次有限性 | 拒绝候选，锁存模型故障，资产不可自动再激活 | Guard/驱动 | 每个张量边界/最终命令无 NaN/Inf |
| F04 Q2B 中急停 | 硬件/安全事件 | 硬件链直接动作；Safety 锁存/撤 Lease；晚到候选拒收 | 驱动器/硬件 | 每个 phase 注入急停；不自动回 Q2B/B2Q |
| F05 双足失稳 | 姿态/角速度/接触/滑移 | 不等待 Balance 报错；撤许可；查 form/support/fault fallback | HAL/硬件 | 报告误触发/漏触发/跌落能量/响应 |
| F06 速度断流 | Arbiter TTL/seq/时钟 | 按制动包络归零；无法在停车窗稳定则升级 | Safety/HAL | 丢包/乱序/重放/短抖/长断全覆盖 |
| F07 越权/重放 | Gateway 身份/ACL/seq/nonce/时效 | 拒绝，不投递 RT，不改图/锁存；审计+限流 | 硬件特权路径 | 仿冒/ACL/payload/过期/未签名全拒绝 |
| F08 模型加载失败 | SHA/tensor/预热 | 标 BROKEN/NOT_RELEASED，不进入目标；旧 Action 仍有效则继续 | Guard/HAL | 损坏/错版本/缺 tensor/OOM/断电可拒绝 |

### D7.6 独立性论证与认证边界

独立性分三层：①**逻辑独立**：安全判断/保护函数不调用 InferenceBackend、不经 Task、日志仅旁路；②**调度独立**：Safety/RT/Worker 线程与核资源分开，RT 不持业务锁、无动态分配；③**硬件独立**：RT 被杀死、OS 故障、电源共因下仍有 HAL/驱动器/安全电路保护。前两项是软件目标，第三项必须本体/电气实测；未证明不能宣称功能安全完整。

功能安全：ISO 12100 风险分析、相关机器人标准、ISO 13849-1 PL / IEC 61508 SIL 适用性由产品合规判断。本文 Guard/Lease 是**工程安全措施**，未经第三方认证、诊断覆盖率/失效概率计算、硬件安全完整性证明，**不得直接标 PL d/SIL 2**。

---

<!-- BEGIN_V12: P4-D7-QUIZ -->
#### [V1.2-解释] D7 读完自测

1. 软 SafetyLease 可以替代物理急停吗？
2. 动态双足失稳时 SAFE_HOLD 一定安全吗？
3. Kill RT 时谁能独立保护？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P4-D7-QUIZ -->

## D8. 并发、实时性与内存

### D8.1 线程与 CPU

<!-- BEGIN_V12: P4-D8.1-THREAD-REALITY -->
#### [V1.2-解释] 优先级、专核、截止之间的区别

`HAL / RT / Safety` 分开实时资源，Worker 单独有计算预算，Gateway 不设为硬实时；这是**建议部署**。核 H0/R0/S0/W0/N0 是抽象角色而非已知 CPU 核号，FIFO95/90/92 是预案，并不证明 Safety 一定不会被 IRQ/热节流影响。

| 异常 | 理论上的软件行为 | 需要的实际证据 |
|---|---|---|
| Worker 推理超 8ms | 候选无效，RT 不等待 | 目标平台候选时间戳/丢弃统计 |
| Safety 被抢占 30ms | Lease 不续，RT 禁正常候选 | 满载+IRQ+热节流的续租抖动试验 |
| RT 被杀 | HAL 在签发的超时窗内保护 | 硬件时戳、驱动状态、电流/使能波形 |

“0 次可解释外 Deadline miss”是测试目标，不是把 p99 当 WCET。
<!-- END_V12: P4-D8.1-THREAD-REALITY -->

以抽象核 H0（HAL）、R0（RT）、S0（Safety）、W0（Worker）、N0（非实时）说明；平台冻结后映射物理核。核数不足时必须重新做共核预算/隔离并通过 HIL，不能直接删安全调度证明。

| 进程.线程 | 工作 | 周期 | 优先级建议 | 核/栈 | 队列 | 超时 |
|---|---|---|---|---|---|---|
| device_hal.bus_loop | 执行器命令/反馈 | 设备要求，目标 1 kHz | FIFO 95（同 OS 时） | H0/128 KiB | 固定 4 槽 | MC 命令 15 ms 超时→设备保护 |
| mc_rt.control_publish | Snapshot/Arbiter/Switch/Mux/Guard/publish | 5 ms/200 Hz | FIFO 90 | R0/256 KiB | 最新候选 4 槽 | 自监测 WCET；HAL 超时兜底 |
| mc_safety.monitor | 独立监控/Lease | 10 ms/100 Hz | **S0 独立核/FIFO92** | S0/128 KiB | 重要事件 16 槽 | 不续租→RT 禁正常输出 |
| mc_runner_worker.step | Obs/模型/Codec/Runner | 20 ms/50 Hz | SCHED_OTHER 或测试过的 DEADLINE | W0/512 KiB | snapshot/candidate 4 槽 | 超 15 ms 结果作废；超时计数 |
| mc_runner_worker.loader | 资源校验/预热 | 事件级 | OTHER | N0/512 KiB | 4 个加载请求 | 无法加载→拒新 Action |
| mc_gateway.rpc | ROS/DDS/RPC/权限/队列 | 事件 | OTHER | N0/512 KiB | 32 请求槽 | 拒绝/限流 |
| mc_gateway.status | 状态/事件/诊断 | 20 ms + 事件 | OTHER | N0/256 KiB | 状态 4/事件 256 | 丢非关键，保留故障序号 |
| mc_gateway.logger | 黑匣子/文件 I/O | 异步/降采样 | OTHER | N0/512 KiB | 预分配 ring | 磁盘满不阻塞 RT |

优先级数值只表示关系示例；部署要与 IRQ/HAL/其他实时进程一起审查。Safety 必须独立核 S0、FIFO92；核不足时只能 Safety≥RT 且同核 WCET/IRQ/热测通过，否则不准量产。**续租约束**：Lease 30 ms，目标续租 10 ms，`max_renewal_interval≤15 ms`；`wake_jitter` p99.99≤3 ms、绝对最大≤5 ms；`missed_renewals=0/1e6`、`unwanted_protective_stops=0/2h`（批准压力工况）。这些是初版验收目标，不是已验证 WCET。

### D8.2 RT 同步规则

| 位置 | 机制 | 禁止 |
|---|---|---|
| HAL→RT Snapshot | 有界单写多读 ring + 序列号/版本检查 | 等新包、信号量 |
| Worker→RT Candidate | SPSC ring/最新值邮箱 + 身份校验 | 互斥锁、无界队列、跨进程指针 |
| Gateway→RT 切换 | bounded MPSC 控制邮箱，RT 单点消费 | RPC 回调直接改活动 Epoch |
| Safety→RT Lease | 单写者只读共享页，序号+过期校验 | RT 等 Safety 回复 |
| RT→HAL 命令 | 单写者 SHM + seq/deadline | ROS callback 直接发同一关节 |
| RT→日志 | 固定环无阻塞写 | malloc/new、磁盘、格式化大字符串 |

RT 代码构建期禁止：`new/delete/malloc/free`、阻塞 mutex、文件 I/O、DNS、同步 RPC、模型加载、printf、可能分配的异常、不可界定时长 GPU 同步。预分配 `mlockall`/预触页、限制栈深、检查 page fault。

### D8.3 WCET 与超期

WCET 是上界，p99 不等于 WCET。RT 5 ms 预算 2.10 ms（Snapshot 0.20、校验 0.20、仲裁 0.15、候选 0.20、Mux 0.25、整形 0.35、Guard 0.30、发布 0.25、统计 0.20），保留 2.9 ms。Worker 15/20 ms，保留 5.0 ms。超期：Worker 晚于 deadline 一律无效；RT 任一 5 ms miss 记录 `RT_DEADLINE_MISS` 与真实最大时间，不补发过期 tick；Safety Lease 不续→RT 停正常输出；HAL 永久无更新→独立 watchdog 保护。不能依赖“超了三次才处理”。

### D8.4 内存与 OOM

| 对象 | 上界建议 | 溢出 |
|---|---|---|
| 关节数组 | MAX_JOINTS=64（实际 N 来自 RobotDescription） | N>64 拒绝启动 |
| Snapshot ring | 8 槽 | 丢帧计数；关键状态失效保护 |
| Candidate ring | 每 Worker 4 槽 | 只取最新有效 |
| 速度最新缓存 | 16 source | 超白名单拒绝 |
| Runner history | `max_history×tensor_elems`，manifest 上界 | OOM→Runner 不开放 |
| 黑匣子 | 128 MiB ring（建议），30+10 s | 满按策略覆盖；故障窗不静默丢 |
| Action 队列 | 每 source 8，总 32 | RESOURCE_BUSY |
| 事件持久化 | 256 条 | 锁存不依赖落盘；统计丢失 |

OOM killer 杀 Worker/Gateway 不能影响 RT；杀 RT 由 HAL 超时保护，不能只靠进程重启。禁止 RT 故障时额外分配诊断对象；GPU/NPU 显存独立配额，禁止推理抢占 HAL/RT 保底资源。

### D8.5 启动、关闭、过载

启动：HAL 安全态/自检 → 时统/估计 → Safety INIT → RT 建立单写者/看门狗握手 → Worker 资产/Schema/Golden/预热 → Gateway 注册 ActionGraph → Task/Nav 等 `mc_ready` → 首次授权 Lease → 正常。**HAL 就绪不等于允许运动。**

关闭：先禁业务/速度 → 受控停车 → 撤许可 → 停 Worker/Gateway → 最后 HAL 安全停机；不能先杀 RT 再等 Runner 优雅退出。

过载：Gateway 令牌桶限流；Worker 迟到候选丢弃/停低优先 Overlay；RT 高抖动记录并减少 trace，HAL 超时保护；日志盘满降采样/轮转；网络拥塞保留最新速度、拒旧 seq；温度节流限高负载 Action；GPU/NPU reset 标故障，切回 CPU 需安全状态重新准入。

### D8.6 ROS/DDS

ROS2/DDS executor 只在 Gateway 普通线程收包、鉴权、拷贝成固定布局；回调不调用 `IRunner::step`、不获取 RT 锁、不写 HAL。速度 `KEEP_LAST(1)` + 短寿命 + 明确可靠性；Action/Event 可靠交付 + 幂等；状态 `KEEP_LAST(1)` + 50 Hz 心跳。**可靠 DDS 不代替 TTL，liveliness 不代替 HAL watchdog。**

### D8.7 Q2/Q7 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q2 线程/实时 | HAL、RT、Safety 独立实时资源；Worker 另核有截止；Gateway 非 RT | 同进程独核多线程 | 独立实时 MCU 承担控制+安全后重设计，但保留同等证明 |
| Q7 安全 | PlatformSafety 策略、MC SafetyKernel 运动/Lease、OutputGuard 唯一出口、HAL/硬件独立 | 只有 Guard 或只有安全线程 | 硬件安全控制器承担某层时可合并软件层，但不得减少有效防线 |

---

**Part 4 完成度：100%（D7–D8 合并稿）；待补：经安全分析批准的保护动作、HAL 独立 watchdog/电气输出实测、核隔离/WCET、认证适用性。**



---



<!-- BEGIN_V12: P4-D8-QUIZ -->
#### [V1.2-解释] D8 读完自测

1. 2.1/5ms 与 15/20ms 能相加吗？
2. Safety 独核是测过的硬件事实吗？
3. 黑匣子能否在 RT 同步写盘？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P4-D8-QUIZ -->

# Collie 运控服务软件架构 V1.3 — Part 5（D9–D12）

<!-- BEGIN_V12: P5-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：怎样让新动作能可靠发布、回放、拒绝

```mermaid
flowchart LR
 RD["RobotDescription"] --> SYS["Graph/Safety/System"] --> MF["Bundle/Manifest"] --> AS["model+ObsSpec+ActionSpec+Golden"] --> CI["Schema/Golden/签名"] --> RT["Worker候选→RT准入"]
 BB["黑匣子/Replay"] -.-> CI
```

| 解释盒 | 为什么／是什么 | 不是什么 | Running Example | 误解 |
|---|---|---|---|---|
| 四级配置 | 让本体、系统、Action、策略各有唯一权威 | 不是四个 YAML | quad_stop 需本体/系统/规格/守卫/Golden/签名 | 只交 ONNX 不叫 Action |
| Release/asset_state | 区分“获准发布”和“运行时是否可用” | 不是一个枚举 | CANDIDATE 不能 ACTIVE | AVAILABLE 也不代表站稳 |
| Golden | 训练端到部署端的逐维期望向量 | 不是现场日志 | 16维演示数据可检查映射 | Golden PASS 不证明安全 |
| 黑匣子 | 故障前后带时钟的每拍记录 | 不是磁盘同步写日志 | Q2B 失败后重放时序 | 128MiB 非实测 |
| SIL/HIL/网安 | 区分软件合同、硬件证据、授权来源 | 不是 36 次真实系统测试 | 重放旧 seq 和资产篡改 | 有 CRC 不等于鉴权 |

**小故事**：准备部署 `quad_stop`，先验标定/系统图/Manifest/策略规格/Golden，然后发布签名；切换失败时黑匣子给出 Snapshot→候选→HAL 拒收的证据。示例 release=CANDIDATE，不允许把它当真实 Collie 资产运行。

**怎么读 D9–D12**：D9 按文件依赖先后读；D10 的 128 MiB/40s 先看记录速率预算；D11 按 Unit→SIL→HIL→实机签收读；D12 先看身份/信任边界再看攻击类型。
<!-- END_V12: P5-OVERVIEW-01 -->

> 合并说明：本 Part 以 V1.1 的 `SCHEMA_CANON`、`schemas/`、16 关节 examples、128 MiB 黑匣子、36 个 SIL/合同测试为准；V1.0 的配置/测试/网络安全结构保留。  
> 唯一权威：`proto`（消息）、`schemas/*.json`（配置）、`safety_limits.yaml`（物理界限）；示例均为不可部署夹具。

---

## D9. 配置、资产、签名与升级

### D9.1 四级配置

<!-- BEGIN_V12: P5-D9.1-FULL-ACTION-PACK -->
#### [V1.2-解释] 一份完整 `quad_stop` Action 包有哪些文件

```text
release/quad_stop-demo-CANDIDATE/
  robot/robot_description.yaml + calibration.yaml       [①本体：真实映射]
  system/action_graph.yaml + velocity_sources.yaml     [②系统：合法路径/来源]
  system/safety_limits.yaml + deployment.yaml           [②系统：限额/周期]
  bundles/quad_stop.yaml                                [③Action：Primary/owns]
  manifests/quad_stop.yaml                              [③Action：两维Runner/资产/guard]
  builtin/quad_stop.yaml                      [④策略：内置，无模型]
  specs/quad_stop_obs.csv + quad_stop_action.csv         [④策略：逐维映射]
  golden/quad_stop_fixture.json                          [④策略：期望向量]
  release_manifest.yaml                                 [签名/哈希/发布状态]
```

**引用顺序**：Release→RobotDescription/校准→System Graph/Safety→Bundle→RunnerManifest→模型+Obs/ActionSpec→Golden→验证→AVAILABLE。**本教学包 release=CANDIDATE、模型/哈希占位，不可部署**。四层不是四个文件，关节方向由 RobotDescription/HAL 适配一次，不能让策略重复定义。

| 字段 | 回答的问题 | 若错了怎样 |
|---|---|---|
| `runner.execution_kind/behavior_role/class_id` | 用哪类算候选？ | Registry 禁模糊回退 |
| `tensor_io+ObsSpec+ActionSpec` | 每一维读写什么？ | 模型错配禁运行 |
| `owns` + Bundle | 哪些关节归主/叠加？ | mask 冲突禁止激活 |
| `entry/exit/completion` | 何时进/何时可出/何时稳定？ | WAIT/REFUSE/超时保护 |
| `golden` + SHA + `release.status` | 是否能证明与发布资产一致？ | BROKEN/CANDIDATE 不运动 |

`[V1.2-审阅注记]` V1.1 评审指出 ModeTransitionPlan、Factory 矩阵、HAL capability 未全部机器化；本段没有虚构已经可校验的 schema。
<!-- END_V12: P5-D9.1-FULL-ACTION-PACK -->

| 层级 | 权威文件 | 内容 | 签发 |
|---|---|---|---|
| 本体层 | `robot_description.yaml` + calibration artifact | 关节名称/顺序、传动、零点方向、限位、驱动 ID、形态、外参 | 本体/HAL |
| 系统层 | `velocity_sources.yaml`、`action_graph.yaml`、`safety_limits.yaml`、`deployment.yaml` | 控制源权限/TTL、合法边、安全包络、实时配置 | 平台+MC+安全 |
| Action 层 | `bundles/<id>.yaml`、`manifests/<id>.yaml` | Action、Runner 类、所有权、周期、进入/退出、资产依赖 | 运控+软件 |
| 策略层 | `models/*.onnx` / `motions/*.mref`、`specs/*ObsSpec.csv`、`*ActionSpec.csv`、`golden/*` | 权重、张量、逐维配方、校验向量 | 训练/运控联合 |

静态事实只定义一次：关节方向/机械限位在 RobotDescription/标定文件，不允许每个 Runner 重复硬编码；ObsSpec 的训练默认位是模型域数据，不等于 HAL 机械零点。输出最终由 HAL 把 SI 转设备表示，方向转换只执行一次。

### D9.2 RobotDescription

关键字段：`schema_version, robot_id, hardware_revision, calibration_id, calibration_sha256, robot_time_source, frames, joint_order, joint_groups, joints, forms`。

- `joint_order` 无重复，每个 name 有唯一设备映射/类型/限位；无未知多余驱动；
- 有效数量 ≤ `MAX_JOINTS=64`；超过需新 IPC 版本；
- 传动比 >0、方向仅 ±1、限位有限且顺序正确；连续轮与机械受限关节区分；
- 所有 frame/外参/时间源在运行前 ready；不可信估计量不得作为必要控制观测；
- RobotDescription/HAL 标定/训练资产兼容矩阵不一致时拒绝正常运动。

示例 16 关节仅用于结构测试，**不是 Collie 拓扑**；示例故意不完整，真实发布必须有逐关节完整记录、外参/惯量版本、校准签名。

### D9.3 RunnerManifest

| 字段 | 说明 | 校验 |
|---|---|---|
| `schema_version` | 1.1 | major 匹配 |
| `manifest_id/version` | 不可变策略版本 | 组合唯一 |
| `action_id/behavior_id` | 动作/业务能力 | Registry 存在 |
| `runner.execution_kind` | ONNX/CLASSICAL/PLAYBACK/COMPOSITE | 与 role 组成唯一工厂 |
| `runner.behavior_role` | LOCOMOTION/TRANSITION/BALANCE/POSE/RECOVERY/OVERLAY | 同上 |
| `runner.class_id` | 工厂 class ID | 与二维表匹配 |
| `runner.backend_id` | onnxruntime_cpu/classical_builtin/trajectory_engine/... | 白名单 |
| `runner.abi_version/period_ms/worker_budget_ms` | ABI/周期/预算 | budget<period |
| `asset.kind/path/sha256` | MODEL/TRAJECTORY/BUILTIN | 模型/轨迹必须带路径+SHA |
| `tensor_io.inputs/outputs` | name/dtype/shape/semantic | 与模型图一致 |
| `obs_spec/action_spec` | path+SHA | 逐维闭合 |
| `owns` | 规范 joint 名 | 与 Bundle/RobotDescription 匹配 |
| `entry/exit/completion` | predicates/max_duration_ms/stable_ms | 有限时长 |
| `failure_target` | DAMPING/ESTOP/PHASE_FALLBACK/SAFE_HOLD_IF_VERIFIED | 经认证保护出口 |
| `golden` | path+SHA | 未通过 Golden 不开放 |
| `release.status` | DISABLED/CANDIDATE/APPROVED | 只有 APPROVED 可正常运动 |

**双层状态**：

- `release.status`：发布包签发时只读；`DISABLED/CANDIDATE/APPROVED`；
- `runtime.asset_state`：`UNLOADED/LOADING/AVAILABLE/ACTIVE/BROKEN`；`AVAILABLE` 前提是 release APPROVED、拓扑/校准匹配、规格/资源/Golden 通过；`ACTIVE` 只表示 RT 提交了当前 Epoch，不等于物理稳定。

### D9.4 JSON Schema 与示例

`schemas/runner_manifest.schema.json`、`action_graph.schema.json`、`obs_spec.row.schema.json`、`action_spec.row.schema.json`、`safety_limits.schema.json` 为机器校验源；`examples/` 提供 16 关节完整 Obs/Action CSV、Manifest、Graph、safety_limits。

示例规则：

- `release.status=CANDIDATE`、`robot_ids: demo16_nonphysical`，Asset 是 `.placeholder`，**不可部署**；
- ObsSpec 16 行、ActionSpec 16 行，索引 0..15 连续，joint_name 精确 16/16，`owns` 全等；
- `sign` 只出现一次方向变换，示例 `fr_hip=-1` 用于测试；
- `safety_limits.yaml` 的 `physical_limits_signed=false`、所有 `limit_profile.approved=false`；校验器必须拒绝正常运动。

### D9.5 一个 Action 的资产

一个 Action 的完整资产 = 模型/轨迹 + Manifest + RobotDescription 映射 + ObsSpec/ActionSpec + 进入/退出/完成守卫 + Golden + Release 签名。只交 ONNX 不算策略。

示例 `quad_stop` 可以演示无 ONNX 的 BUILTIN 契约；Hash 为占位，`release.status=CANDIDATE`，不能被标 APPROVED。完整 16 关节示例见 `examples/demo16_*`。

### D9.6 加载顺序、兼容矩阵、OTA

加载：验证 Release 签名/文件 SHA → RobotDescription/校准/HAL 映射 → SystemConfig（source/graph/safety） → Bundle/Manifest JSON Schema → 跨文件拓扑/mask/tensor/guard → 预分配/预热 → Golden smoke → `AVAILABLE`/受控激活。失败保留上一个已签名 Release。

兼容：RobotDescription topology SHA 精确命中；校准 SHA/机械版本按允许集；Runner ABI major 精确；Manifest Schema major 一致；Tensor/Obs/Action 名称/shape/dtype/顺序/公式/SHA 精确；provider/opset 在预热+Golden+平台列表；safety limits 同本体/Release 签名。

OTA：A/B 完整 Release；下载非活动槽 → 验签/哈希 → 禁新运动 → 受控停止进安全态 → 预加载/回放 → 原子切 active 指针 → 健康检查 → 允许运动。失败回滚上一签名包；回滚不是继续旧 Epoch；不在运动中热替换模型/安全参数。

### D9.7 Q9 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q9 配置资产 | 四层只读资产包+签名+SHA+JSON Schema+跨文件校验+双槽回滚 | 单 YAML/运行中热写 | 多机型资产平台成熟后合并源格式，但仍生成等价锁定包 |

---

<!-- BEGIN_V12: P5-D9-QUIZ -->
#### [V1.2-解释] D9 读完自测

1. 四级配置各自拥有哪类事实？
2. CANDIDATE 能否 ACTIVE？
3. Manifest 缺真实 Golden/ModePlan 还能上线吗？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P5-D9-QUIZ -->

## D10. 可观测性、黑匣子与回放

### D10.1 Trace 与每拍日志

每个 RPC/Event/Candidate/JointTarget/安全事件共享 `trace_id`，并传播 `request_id/execution_id/action_epoch/tick_id/boot_id/release_id`。日志线程不参与 RT；RT 写预分配二进制环，单独线程转储。

| 层 | 字段 | 采样 |
|---|---|---|
| SAMPLE | 实际使用的关节/IMU/接触、每源 timestamp/valid/seq、时基质量 | Worker 20 ms；HAL 高频故障窗按容量 |
| REFERENCE | source/seq/TTL/坐标变换前后速度、限制/失源原因 | 每 Worker tick + 源变更 |
| OBS | 逐维 tensor 名/shape/dtype/数组/历史顺序/摘要 | 每次推理（故障环完整） |
| MODEL | 模型 SHA/provider/IO/耗时/raw output | 每次推理（故障环完整） |
| CODEC | 解码目标/模式/增益/own_mask | 每次候选 |
| RT | Epoch/Mux/Guard clamp/原因/HAL 目标/seq/deadline | 每 5 ms |
| SWITCH | 阶段/物理守卫/fallback/原子接管 tick | 事件 |
| SAFETY | fault/latch/lease_seq/状态迁移/硬件确认 | 事件+周期摘要 |
| SYSTEM | CPU/内存/温度/时统/队列/磁盘 | 1 Hz |

### D10.2 黑匣子容量（唯一 128 MiB）

<!-- BEGIN_V12: P5-D10.2-MEASURE -->
#### [V1.2-解释] 为什么 128 MiB 不等于无条件能回放

按 V1.1 预算，全活跃 Worker 合计 409600 B/s，RT 51200 B/s，总 460800 B/s≈0.4395 MiB/s；40 秒需要约 17.58 MiB，128 MiB 总环预留 16 MiB 后还有 112 MiB 记录区。**2.8 MiB/s** 是完整 30+10s 窗的准入上限，不是实测写速率。Overlay 增大 tensor 或样本时，必须重算实际编码带宽并检查“故障前窗口仍完整”，不能仅凭内存尺寸宣称回放可用。RT 不同步落盘。
<!-- END_V12: P5-D10.2-MEASURE -->

`blackbox.ring_bytes = 134,217,728`（128 MiB，建议）。编码预算：所有活跃 Worker 合计 `8192 B×50 Hz=409600 B/s`，RT `256 B×200 Hz=51200 B/s`，总 `460800 B/s≈0.4395 MiB/s`；128 MiB 可容约 291 s，未含索引。预留 16 MiB，允许记录 112 MiB，约 255 s；故障前 30 s+后 10 s 最少约 17.58 MiB，仍低于 128 MiB。准入条件：含 Header/对齐/辅助模型的全部活跃 Runner，平均与最坏单窗 `recorded_max_bytes_per_s ≤ (128−16) MiB/40 s = 2.8 MiB/s`；超出则该 Action 的“完整故障窗”标 `UNAVAILABLE`，不得声称满足黑匣子验收。

RT 不写盘；故障触发 ring 保存事件锚点并继续记录 10 s，异步转储最近 30 s+后 10 s；超容量不得静默覆盖故障前窗口。`.mcbx` 文件头含 magic/version/robot_id/boot_id/release_hash/clock_map；SchemaTable 含 joint/tensor 名称/shape/dtype/unit/frame/spec SHA；Record 含 seq/tick/epoch/time/type/payload_len/CRC；Footer 含 file SHA/record_count/incomplete。CBOR/FlatBuffers 二选一，需最终冻结。

### D10.3 Replay 与 Golden

- 纯数据重算：复原 Snapshot/Reference，重新构造 Obs/推理/解码/Guard；
- 锁定 raw 输出重放：跳过不确定推理，验证 Codec/Mux/Guard 确定性；
- 端到端时序重放：各种 timestamp/deadline/丢帧/乱序/切换事件。

Golden 是训练与软件共同签收的固定期望向量；现场黑匣子是可复现输入证据，不能互相替代。回放必须比较逐维 tensor 值，不只比最终轨迹。

### D10.4 指标与告警

关键指标：`mc_rt_tick_exec_ns`/`rt_deadline_miss_total`、`mc_worker_exec_ns`/`inference_timeout_total`、`feedback_age_ns`/`invalid_sample_total`、`velocity_source_age_ms`/`source_switch_total`、`action_switch_duration_ms`/`switch_fail_total`、`guard_clamp_total`/`guard_fault_total`、`lease_expiry_total`/`hal_watchdog_total`、`cpu_pct/memory/page_fault/shm_depth`、`release_id/model_hash/topology_hash`。Dashboard 至少显示行为/形态/安全态、切换阶段、时延直方图、速度源/TTL、模型/配置版本、反馈新鲜度、HAL watchdog、安全事件、磁盘/黑匣子容量。线上不允许改未签发安全阈值。

### D10.5 Q11 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q11 回放 | RT 内存黑匣子完整每拍；普通日志限速；三种 Replay | 全同步日志/只留摘要 | 模型数据超容量时按资产扩容，不能隐式丢张量 |

---

<!-- BEGIN_V12: P5-D10-QUIZ -->
#### [V1.2-解释] D10 读完自测

1. Golden 与现场黑匣子为什么不能互相替代？
2. 为什么 128MiB 要按所有活跃模型重算？
3. 如何知道故障窗口没被覆盖？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P5-D10-QUIZ -->

## D11. 测试、故障注入与签收

### D11.1 测试金字塔与门槛

<!-- BEGIN_V12: P5-D11.1-SIL-HIL -->
#### [V1.2-审阅注记] “36/36 通过”究竟证明了什么

V1.1 的 `check_examples` 12 项、`hal_contract_sil` 9 项、`init_and_lease_sil` 11 项、`check_doc_contracts` 4 项，共 36 项属于**SIL模型/合同、配置样例、文档一致性**。其中 FakeHal 只证明拒收分支模拟逻辑，不能证明电机总线独立超时。发布流程必须区分：Unit/Schema→Golden/Replay→故障注入→真实 HAL HIL→限能/封闭真机→每条边签收。

当前阻断编码/评审的重点 P0：`can_exit` 已封 READY 后在 `step` 中出故障或挂死，不能允许 RT 提交；生产路径应新增相应竞态注入，`0 次错误提交` 才能关闭 P0。
<!-- END_V12: P5-D11.1-SIL-HIL -->

```text
实机封闭场地（已开放边）
  ↑ HIL（真实 HAL/驱动 + 故障注入）
  ↑ 故障注入 + 切换图全边
  ↑ Golden 回放 + 时序重放
  ↑ 单元/Schema/静态检查
```

| 层 | 门槛（建议） | 证据 | 签收 |
|---|---|---|---|
| Unit | 安全关键分支/异常守卫 100% 覆盖；CI；parser fuzz 不崩溃 | 报告/覆盖率/fuzz | 软件+安全 |
| Asset | 错位/缺文件/错 ABI 必须拒绝；0 silent fallback | validator JSON | 软件+运控 |
| Golden | 同 CPU+fp32 逐维 abs error ≤1e-5（初值）；量化/异后端按 tensor 签署 tolerance；Guard/状态精确 | 每 Action Golden diff | 训练/运控+软件 |
| ActionGraph | 100% 已开放边正负例/超时；非法边 0 成功 | 图覆盖清单 | 软件+运控 |
| Replay | 同 Release+同 captured raw，Codec/Mux/Guard bit-exact 或定义差异；阶段可重建 | `.mcbx`/diff | 软件+测试 |
| Fault | 8 类故障+每阶段急停；正常输出不越安全态；旧 Epoch 0 成功 | 注入日志/HAL seq/波形 | 安全+HAL+测试 |
| Timing | RT 2.1/5 ms；24 h 0 次无法解释发令超期；HAL 超时独立有效 | ftrace/perf/示波器/温升 | RT+HAL |
| HIL | 真实驱动/断流/急停/上下电；无未授权驱动命令；watchdog/ESTOP 100% 触发 | HIL 报告/总线抓包 | HAL+安全+测试 |
| 场景 | 批准地形/速度/载荷内完成；0 未解释失控；失败有安全结果 | 视频+黑匣子+版本 | 产品+运控+安全 |

`24h 0 超期` 是回归门槛，不等于理论 WCET；`1e-5` 是 CPU 浮点初值，不适用于量化后端。

### D11.2 测试矩阵与故障注入

模型/控制器（RL 单/多输入多输出、经典、轨迹、Transition、Balance、Overlay）× Action（QuadStand/Drive/Stop/Q2B/Balance/B2Q/Recovery/Overlay）× 切换（每条允许/禁止边、guard WAIT/REFUSE、phase fallback）× 故障（延迟/挂死、NaN、过期、越界、丢帧、急停、模型加载失败、通信断流、Worker/RT/Safety 进程死亡）× 平台（x86 影子/目标 ARM/HAL HIL/实机）。

注入点：Worker（sleep/死循环/异常/杀进程）；Snapshot（固定/倒退 seq、NaN、缺关节、IMU 断流）；Backend（改 tensor name/shape/dtype）；Codec/JointMux（overflow、mask 冲突、缺项）；Velocity（TTL/乱序/旧 session/失同步）；PolicyManager（WAIT_EXIT 永不 READY、目标首拍失败）；HAL（拒收/总线断/驱动 fault/温升）；Safety（撤 Lease/进程崩溃/硬件急停）；OTA（篡改/断电/磁盘满/版本冲突）。

### D11.3 真机开放边

每条 `from→to` 有开放记录：`edge_id, robot_hw_rev, calibration_sha, source/target_asset_sha, test_envelope, max_speed, payload, terrain, guard_values, fallback_coverage, HIL_evidence, real_evidence, safety_signoff`。顺序：离线/静态→SIL→HIL→支架/限能→封闭空场小扰动→既定场景。Q2B/B2Q 每个 phase 必须有急停/失败处理试验；不存在安全可逆轨迹的 phase 不能承诺自动回原形态。

阶段门：P0 影子（0 HAL 写）；P1 单 Action（Golden/50/200 Hz HIL/断流/封闭实机）；P2 切换/叠加（全开放边/非法边/超时/回放）；P3 安全联锁（杀 Worker/RT/Safety、硬件急停、HAL watchdog）；P4 形态（Q2B/B2Q/Balance 全 phase/接触/回退）。

### D11.4 CI 与证据

每次 PR：format/lint → compile → schema/static → unit/fuzz → Golden → graph-generated test → replay → deterministic IPC → report。每个候选 Release 补目标平台长稳时效/内存/线程泄漏/HIL fault matrix；涉及本体标定/Guard/模型张量/HAL 固件的改变必须触发相关真实设备回归。CI 产出带 `git SHA/compiler/OS image/robot_description_sha/model_sha/manifest_sha/golden_sha/test suite` 的不可变验收包，不能只留绿色勾号。

### D11.5 Q13 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q13 测试 | Unit+Golden+Graph 全边+Fault+HIL+真实场景分级开放 | 只仿真/现场手测 | 自动化成熟后减少人工重复，但保留安全/回归门 |

---

<!-- BEGIN_V12: P5-D11-QUIZ -->
#### [V1.2-解释] D11 读完自测

1. 36/36 是什么类型的测试？
2. HIL 的 HAL watchdog 测什么波形？
3. ActionGraph 每条边凭什么开放？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P5-D11-QUIZ -->

## D12. 网络安全与供应链

### D12.1 信任边界

```text
云/App/不可信客户端
  │ TLS/mTLS / Device API Gateway
  ▼
Task Engine 授权域
  │ 经签发的 Action 请求
  ▼
MC Gateway 可信域
  │ schema+ACL 后固定 IPC
  ▼
mc_rt 受限域 ── 独占写权限 ── HAL 最小权限域
  ▲
Worker 模型隔离域（只回候选+epoch+hash）
  ▲
MotionSafetyKernel（安全许可）
  ▲
独立物理急停
```

默认不把任意外部网络、ROS Topic、模型上传直接暴露给 HAL。外部网络失效不能绕过硬件急停和 HAL 本地保护。

### D12.2 STRIDE

| 类别 | 示例 | 措施 | 注入/证据 |
|---|---|---|---|
| S 伪装 | 伪造 `source=local_rc` 抢速度 | 身份证明/mTLS/source 绑定/ControlLease | 冒名 source 拒绝 |
| T 篡改 | 改 ONNX/安全配置/速度 | 签名 Release/SHA/消息完整性/权限隔离 | 单字节修改触发失败 |
| R 抵赖 | 否认启动高风险动作 | 签名/关联审计 `request_id,source,actor,reason` | 记录防篡改 |
| I 泄露 | 日志含用户/地图/令牌 | 匿名 source/脱敏/加密/保留期限 | 日志扫描/访问审计 |
| D 拒绝服务 | 高频 RPC/DDS 洪泛 | 网关限速/配额/隔离/固定队列/RT 独核 | 压测期间 RT 不越门 |
| E 权限提升 | SDK 调 SetSafety(NORMAL)/绕 Gateway 写 HAL | 细粒度 ACL/OS 权限/硬件隔离 | 非授权/直写 SHM 必须失败 |
| 供应链 | 替换动态库/provider | SBOM/构建可追溯/只读签名资产/版本固定 | 篡改/不匹配阻止激活 |
| 重放/乱序 | 重放旧 Action/速度/Lease | session/boot_id/seq/nonce/期限/epoch | 旧包/跨重启 0 接受 |

### D12.3 身份、消息、OTA

- MC Gateway 接受平台签发的身份与动作白名单；source 名称不是凭证；本地维护身份→允许 Action/速度源/Overlay/最高运动等级。
- 不可信链路 mTLS 或同等安全信道；请求含 session/单调 seq/nonce/有效期/payload digest；高风险请求可要求设备内签名或网关重签。合法网络请求仍须过物理 guard。
- Release 包含 manifest 全文件 SHA/签名/签发者/允许 robot_hw_rev/ABI；A/B 完整包；运行用户无修改活动资产权限；动态 `.so`/ONNX provider 入 SBOM；回滚不能越过安全补丁最低版本。
- 量产关闭 JTAG/开发调试/原始关节写入口；维修模式需物理授权、限速/限力、隔离、超时退出；不得用隐藏 ROS topic 开第二关节出口。
- 审计：连续鉴权失败、重复过期 seq、异常峰值、签名失败、非预期版本变更；安全关键异常可提升保护，但网络断流用已验证受控停止，不依赖云端检测。

### D12.4 网络安全与功能安全接口

安全模块接收 `SECURITY_INTEGRITY_LOSS/UNAUTHORIZED_MOTION/REPLAY_DETECTED/ASSET_TAMPERED`，按严重度禁正常 Action/新资产/远程控制，必要时撤销 SafetyLease。HAL/硬件的限位/超时/急停在 Gateway/网络全部受攻击时仍独立生效。恢复需身份/密钥检查、审计、本体物理状态确认；禁止在线自动解 ESTOP。

### D12.5 Q12 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q12 网络安全 | API/Motion/HAL 三道信任边界，ACL+mTLS+seq/nonce+完整包签名，调试物理授权 | 仅 ROS 域隔离/内网可信 | 专用安全总线可替代部分软件鉴权，但要证明同等威胁控制 |

---

**Part 5 完成度：100%（D9–D12 合并稿）；待补：Collie 全量 RobotDescription/模型资产、真实 SHA/签名、Golden、HIL 报告、密钥管理。**



---



<!-- BEGIN_V12: P5-D12-QUIZ -->
#### [V1.2-解释] D12 读完自测

1. writer_id 为何不是身份凭据？
2. CRC 为什么不是签名？
3. OTA 激活中如何防旧 Epoch 自动恢复？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P5-D12-QUIZ -->

# Collie 运控服务软件架构 V1.3 — Part 6（D13–D16）

<!-- BEGIN_V12: P6-OVERVIEW-01 -->
#### [V1.2-解释] 本 Part 在全局的位置：架构变成任务、证据、拍板

```mermaid
flowchart LR
 A["D13：做了什么决策"] --> B["D14：还有哪些风险"] --> C["D15：按哪些阶段交付"] --> D["D16：谁凭什么签收"]
```

| 解释盒 | 为什么／是什么 | 不是什么 | Running Example | 误解 |
|---|---|---|---|---|
| ADR | 记录做某选择的原因和代价 | 不是已完成验收 | 为什么只允许 RT 写 HAL | 决策通过≠实现通过 |
| 风险表 | 追踪未冻结事实和阻断级别 | 不是能删的备注 | 双足支撑未知→禁 Q2B | 不能以 T1 代 Collie |
| P0–P5 | 先影子/单动作，后切换/安全/形态/量产 | 不是任意团队都能12周完成 | 先验证 quad_stand 再开放 Q2B | 路线图不是安全批准 |
| 开放边 | 某个 from→to 的机型/版本/工况签收 | 不是一次跑通所有边 | QuadStop→Q2B 需逐phase试验 | 一条边开放不代表所有方向开放 |
| Checklist | 把“设计里写了”变成可复核证据 | 不是勾全绿的展示页 | HAL watchdog 要硬件测试证据 | 36 SIL 不能冒充 HIL |

**小故事**：项目经理想公开演示双足，先查 D13 的设计、D14 的资产和 HAL 风险、D15 的阶段门，再用 D16 第 11/17/20 条查 Q2B phase、时序、批准边。任何一项缺 HIL/本体签收，保持 DISABLED。

**怎么读 D13–D16**：ADR 负责说明为什么；风险表给责任/关闭办法；路线图给前置条件；Checklist 的“是”必须绑定可复核证据，不是基于主观信心。
<!-- END_V12: P6-OVERVIEW-01 -->

> 合并说明：本 Part 以 V1.1 的 24 条 ADR、14 项裁决、16 条风险、P0–P5 路线图、20 项 checklist 与 V1.1 自评 86 分为准；V1.0 的原始 ADR/风险保留为历史对照。  
> 结论：**可启动软件编码；不可据此开放真实运动上机。**

---

## D13. 架构决策记录（ADR）

| 编号 | 决策 | 理由 | 替代/代价 | 状态 |
|---|---|---|---|---|
| ADR-01 | Behavior→Action→Bundle→Runner | 对外稳定、内部可替换 | 仅 Runner/仅 Behavior；多映射层 | 【建议】 |
| ADR-02 | ActionBundle = Primary + Overlay slots | 五类行为共用组合 | 一 Action 一类一线程；组合校验 | 【建议】 |
| ADR-03 | Gateway/Worker/RT/Safety 混合多进程 | 推理挂死不阻塞发布 | 单进程；IPC/部署成本 | 【建议，待平台验证】 |
| ADR-04 | 只有 `mc_rt` 有正常 HAL 写权限 | 消除双写 | 每 Runner 写 HAL；统一仲裁 | 【建议】 |
| ADR-05 | 50 Hz 策略 + 200 Hz 发布（ZOH） | 与训练 dt=0.02 对齐；分离推理与发令 | 100 Hz 空转；50→100 插值 | 【V1.3 决策】 |
| ADR-25 | 50 Hz 策略 / 50 Hz Worker / 200 Hz RT；15/20 ms；25 ms TTL | 频率与训练一致；P0 窗口翻倍 | 100 Hz 空转；默认插值 | 【V1.3 决策】 |
| ADR-06 | 双足先按动态平衡接口 | 不隐含静态锁止 | 全 Pose；需平衡资产 | 【待定】 |
| ADR-07 | Q2B/B2Q 独立 TransitionRunner | 相位/支撑/退路 | 线性插值；独立资产 | 【建议】 |
| ADR-08 | 逐关节 bitmask，默认不同关节混合 | 禁叠加抢写 | Scope 粗分；需训练协商 | 【建议】 |
| ADR-09 | 4 RPC + 2 stream + 内部三类输入 | 小外部面、细语义 | 全 Topic/每 Runner RPC | 【建议】 |
| ADR-10 | SafetyKernel + Guard + HAL + 硬件链 | 不依赖模型 | 单看门狗/单安全进程 | 【建议】 |
| ADR-11 | Manifest + 逐维 Spec + Golden | 检出训练/部署错位 | 仅 ONNX+参数数 | 【建议】 |
| ADR-12 | 独立 MC 仓、阶段迁移 | 可独立编译/回滚 | 旧节点 switch(model) | 【建议】 |
| ADR-13 | 冷启动 INIT + UNKNOWN，未知支撑不发保持 | 未知姿态位置保持危险 | 直接 SAFE_HOLD；启动变慢 | 【建议】 |
| ADR-14 | ControlLease 独立于 Session/SafetyLease | 运动资源独占 | 只靠优先级；租约成本 | 【建议】 |
| ADR-15 | HAL token + 设备 watchdog + Epoch 预备 | 单写者需设备侧可验证 | 只靠 RT 单进程约定 | 【建议，待硬件】 |
| ADR-16 | proto+JSON Schema 生成；黑匣子 128 MiB | 消除字段漂移 | 手填多份；版本冲突 | 【建议】 |
| ADR-17 | `can_exit` Worker 预计算 sealed + RT 只读 | RT 不依赖 Worker | RT 纯函数；需镜像状态 | 【建议，含竞态待修】 |
| ADR-18 | Safety S0 独立核/FIFO92 | Safety 失调度会失租/误停 | 同核省资源；竞争风险 | 【建议，待平台】 |
| ADR-19 | ModeTransition 统一 ramp + HAL ack | 未受控模式突变会力矩跳变 | 直接切换；风险高 | 【建议，待 HIL】 |
| ADR-20 | Runner `(ExecutionKind,BehaviorRole)` 唯一工厂 | 消除类名歧义 | 字符串猜实现 | 【建议】 |
| ADR-21 | 双层资产状态 | release 审批/运行状态不同 | 单枚举；语义混淆 | 【建议】 |
| ADR-22 | 危险动作按 phase/边逐项开放 | 不能靠“全系统通过”放开 | 一次性全开；不可接受 | 【建议】 |
| ADR-23 | SIL/合同测试与 HIL/实机分级 | 软件合同不等于物理安全 | 只做仿真/只做实测 | 【建议】 |
| ADR-24 | 增量变更单 + 合并阅读版 | 避免重写、保留追溯 | 直接重写全文；易漏 | 【建议】 |

**重审规则**：计算平台/模型 WCET 变化→ADR-03/05/18；HAL/安全硬件变化→ADR-10/15；双足/上肢结构变化→ADR-06/07/08/19；硬件安全能力变化→ADR-13/15/18。

---

<!-- BEGIN_V12: P6-D13-QUIZ -->
#### [V1.2-解释] D13 读完自测

1. ADR 是设计决策还是验收证据？
2. 哪条 ADR 保证 RT 是唯一正常写者？
3. 改变硬件平台时哪个 ADR 需要重审？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P6-D13-QUIZ -->

## D14. 风险与未决

| ID | 风险/未决 | 概率 | 影响 | 缓解/阻断 | 责任方 | 验证 |
|---|---|---|---|---|---|---|
| R01 | 关节数量/顺序/零点未冻结 | 高 | 极高 | 先冻结 RobotDescription；实机出口关闭 | 本体+HAL | 关节映射/标定/方向/限位 |
| R02 | 双足动态/静态不明确 | 高 | 极高 | 按动态接口设计，不开放双足 | 本体+运控 | 动力学/支撑/扰动/断流 |
| R03 | Q2B/B2Q 资产不足 | 高 | 高 | 只交接口；边禁用 | 运控训练 | 模型/轨迹+Golden+每 phase HIL |
| R04 | 计算平台撑不住进程/周期 | 中 | 极高 | 压测/核/IRQ 规划；不达标禁开放 | 平台+RT | WCET/满载/热/HAL 超时 |
| R05 | HAL 缺独立 watchdog/Writer ACL | 中 | 极高 | HAL P0 改造/硬件联测 | HAL+安全 | 杀 RT/跨用户直写/断总线 |
| R06 | 硬件急停不独立 | 中 | 极高 | 电气审查；未过量产阻断 | 电气+安全 | 断网/杀全 MC/实际 E-stop |
| R07 | 训练/部署观测规格不一致 | 高 | 高 | 强制 Obs/ActionSpec+逐维 Golden | 运控+软件 | 任意 N 维/历史 diff |
| R08 | Overlay 与承重关节争用 | 中 | 高 | mask 严格不重叠；争用改模型参考 | 运控+本体 | 组合矩阵/WBC 扰动 HIL |
| R09 | 多进程候选/提交竞争/旧 Epoch 混入 | 中 | 极高 | RT 单写、不可变 prepare、单调 Epoch | 软件+RT | 乱序/重启/延迟推理注入 |
| R10 | 安全保持/阻尼仍可能伤害 | 高 | 极高 | 按 form/support/fault 分别制定保护动作 | 安全+运控+HAL | 动态/静态/倾倒/碰撞试验 |
| R11 | `roboparty_deploy` 不适配多输入/真实模式 | 高 | 中 | Adapter 重写；旧工程只参考 | 软件+运控 | 审码/Golden/shadow diff |
| R12 | 现场日志过大/不可回放 | 中 | 中 | 预分配环/Schema/30+10 s | 平台+测试 | 磁盘满/截断/故障提取 |
| R13 | 模型/配置升级途中不一致 | 中 | 高 | 签名 A/B 包/原子激活/断电测试 | 平台+安全 | 篡改/回滚/断电/旧版拒绝 |
| R14 | 上游越权/重放/误注入 | 中 | 高 | ACL/身份/seq/nonce/TTL/网关 | 平台安全+软件 | STRIDE/网络压测 |
| R15 | 产品地形/载荷超策略域 | 高 | 极高 | 首版仅无载平地；其他独立门 | 产品+运控+测试 | 需求冻结/场景/超域拒绝 |
| R16 | SIL 成功但无真实接触模型 | 高 | 高 | HIL+低能量实体；保留未知 | 运控+测试 | 仿真差异/现场日志 |

**上机阻断**：R01/R02/R04/R05/R06/R10/R15 未关闭前，相关真实运动不能开放；不得因项目进度强制放行。

---

<!-- BEGIN_V12: P6-D14-QUIZ -->
#### [V1.2-解释] D14 读完自测

1. 双足支撑方式未冻结阻断什么？
2. 哪个风险必须由电气/HAL 签发？
3. 为什么不能用 T1 数据填写 Collie 限额？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P6-D14-QUIZ -->

## D15. 实施路线、人力、迁移与回滚

<!-- BEGIN_V12: P6-D15-GATES -->
#### [V1.2-解释] 为什么路线图不能按“功能越多越好”排序

| 门 | 代表 Running Example 哪一段 | 退出证据 | 不过就怎样 |
|---|---|---|---|
| P0 影子 | 不接电机、仅算候选 | Schema/Golden/回放/0正常HAL写 | 不能切 writer |
| P1 单 Action | 有条件站立/行走 | 真实 HAL watchdog + HIL + 限能场景 | 不开放下一动作 |
| P2 切换/Overlay | 站立↔行走、普通切换 | 所有开放边正反例 + 旧 Epoch 0 接受 | 禁切换 |
| P3 安全联锁 | 急停、杀进程、失租 | 逐故障 HIL/硬件证据 | 停止真实运动 |
| P4 变形 | QuadStop→Q2B→Balance→B2Q | 每 phase 资产、净空、支撑、Fallback 签收 | 保持 DISABLED |
| P5 量产 | 现场 OTA/安全/追踪 | 发布签名和长期回归 | 仅内部试验 |

**关键风险**：V1.1 `can_exit` 的 pre-step READY 竞态必须先在编码/测试中解决，不能因已完成“路线图设计”而跳过。P0–P5 的估期是组织规划，不是实机开放许可。
<!-- END_V12: P6-D15-GATES -->

### D15.1 目标仓库

```text
collie_motion_control/
  include/collie_mc/       # 领域/IDL/错误码/版本
  proto/                   # IPC/ROS2 生成源
  gateway/                 # API/PolicyManager/Registry/Graph
  worker/                  # Runner/Obs/Inference/Codec
  rt/                      # Snapshot/Arbiter/Epoch/Mux/Guard/Publisher
  safety/                  # SafetyKernel/Lease/状态
  hal_contract/            # HAL 客户端/SHM/watchdog
  config/schema/           # JSON Schema/校验器
  assets/                  # 签名 release 构建输入（无私钥）
  tools/mcctl/ replay/ mrefc/
  test/unit/ golden/ fault/ hil/
  docs/adr/ interfaces/ safety/
```

构建产物：`mc_gateway`、`mc_runner_worker`、`mc_rt`、`mc_safety`、`libcollie_mc_api`、`mcctl`、`mcreplay`、版本化 schema/IDL、signed release manifest、Golden 报告、HIL 验收包。

### D15.2 从 `roboparty_deploy` 迁移

| 旧能力 | 策略 | 新位置 | 必须改造 |
|---|---|---|---|
| PolicyRuntime/模型加载 | 参考/抽取 | worker/inference | 多输入输出、tensor 校验、超时、预热、签名 |
| 配置化观测/历史 | 复用算法思想 | worker/observation | 逐维 ObsSpec、实例历史、首帧、Golden |
| RobotInterface::apply_action | 不直接继承写权限 | hal_contract | 模式/增益完整性、唯一 writer、deadline/seq |
| `/cmd_vel` | 只复用协议适配 | gateway→rt/VelocityArbiter | 授权/seq/TTL/frame/整形 |
| 旧同步推理+控制循环 | 不复用为 RT 主循环 | Worker+RT 拆开 | 阻塞推理不能留在唯一出口线程 |
| 状态机/单模型 switch | 不复用为 Action 切换 | gateway+rt/SwitchCoordinator | 图、原子 Epoch、进入/退出守卫 |
| 旧设备 writer | 迁移期只能单活 | 旧进程或 mc_rt 二选一 | 禁止双写；只在安全停机态交接 |

### D15.3 P0–P5 路线图

| 阶段 | 目标/交付 | 退出条件 | 风险门 |
|---|---|---|---|
| P0 骨架/影子 W1–W3 | IRunner/IPC、Schema/Registry、空动作、Dummy HAL、Golden/replay、黑匣子、CI | 0 HAL 正常写；全链虚拟 tick；关键错误可复现 | 无 HAL writer ACL 不上机 |
| P1 单 Action W4–W6 | QuadStand/QuadWheelDrive 二选一；Obs/Codec/Guard、真实 HAL | 单动作 Golden、50/200 Hz HIL、断流保护、封闭实机签收 | HAL watchdog/硬件急停失败即阻断 |
| P2 切换/叠加 W7–W9 | ActionGraph、PolicyManager、Session/Epoch、QuadStop、组合矩阵 | 已开放边/非法边/超时/切换回放通过 | 双写/旧 Epoch 接受即阻断 |
| P3 安全联锁 W10–W12 | SafetyKernel/Lease、平台安全接口、故障注入、黑匣子、A/B OTA | 8 场景、RT/Worker/Safety kill、恢复流程 | 未批准安全替代不得实机 |
| P4 多形态 W13+ | Q2B/B2Q/Balance/Recovery/可选 Overlay | 逐资产/边 SIL→HIL→封闭真机开放记录 | 无资产/无回退/无净空保持 DISABLED |
| P5 量产治理 | 现场 OTA、追溯、指标、合规、灰度/回滚 | Release 矩阵、运维手册、逐版本签发 | 不作未证实 PL/SIL 宣称 |

W 为有效开发周；P4/P5 不因 P0–P3 估算直接承诺。

### D15.4 人力粗估

| 角色 | 峰值 FTE | P0–P3 人周 |
|---|---:|---:|
| 架构/接口 | 1.0 | 8–12 |
| 实时/HAL | 2.0 | 16–24 |
| Runner/推理/模型集成 | 2.0 | 16–24 |
| 平台/API/OTA | 1.0 | 8–12 |
| 安全工程 | 1.0 | 8–12 |
| 测试/HIL | 2.0 | 16–24 |
| 运控算法/资产 | 1–2.0 | 8–20 |
| **合计** | **10–11 FTE** | **80–128 人周** |

12 周是“资源充足且硬件/标定及时”的规划尺度；4–5 人会显著延长；双足/变形训练与安全认证不含在稳定软件骨架工期。

### D15.5 影子双跑与切写

影子只比较计算，不双写 HAL：旧 deploy 是唯一 writer；新 MC Worker 只读同一反馈，输出候选/Guard 结果到 diff；对齐 Snapshot/Obs/raw/decoded/Guard/时延/故障结果。切写流程：停业务/速度→安全形态→确认设备安全/驱动使能→停旧 writer 并撤旧 HAL 权限→启新 writer 握手→新 Release 自检→SAFE_HOLD 重新准入→低能量/单 Action 验收。禁止运行中双 publisher 抢关节。

### D15.6 回滚

| 触发 | 动作 |
|---|---|
| 新 Release 签名/Schema/Golden 失败 | 不激活；旧签名包保持 |
| 新 Action 输出/时延异常 | Guard/HAL 保护；安全停机后恢复旧 writer/旧包 |
| Q2B/Balance HIL/实机未过 | 禁用对应图边/资产；四足能力不受影响 |
| 实机未知危险/急停失效 | 停止全部运动试验，隔离设备；根因关闭+安全联签后继续 |
| OTA 激活后崩溃 | HAL watchdog 安全态；启动器检测新槽失败→原子回滚，复位 Epoch |
| 网络安全/密钥泄漏 | 撤销远程控制/资产激活；轮换凭证/审计；必要时安全态回滚 |

回滚不是两个进程直接抢关节；必须 HAL 安全握手、唯一 writer 切换、新 `boot_id/action_epoch`，不得复用旧控制会话/速度/历史。

### D15.7 Q14 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q14 迁移 | 新独立 `motion_runtime`；旧部署只参考/影子；安全态切唯一 writer | 旧代码加 switch(model)/全部重写 | 所有关键旧功能迁移且新系统通过独立安全/回放/HIL 后退旧 |

---

<!-- BEGIN_V12: P6-D15-QUIZ -->
#### [V1.2-解释] D15 读完自测

1. 影子双跑可以两个 writer 吗？
2. 哪些阶段需要真实 HIL？
3. 回滚为什么不能沿用旧 Epoch？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P6-D15-QUIZ -->

## D16. 给非软件背景决策者的 20 项 Checklist

填写规则：只在有具体可复核的测试报告/签名资产/接口检查证据时选“是”；没有证据按“否/待证实”。**“设计里写了”不等于“验收完成”。**

| # | 是/否问题 | 证据要求 | 不过的风险 |
|---|---|---|---|
| 1 | 是否只有一个 MC 模块有正常 HAL 写关节权限？ | 进程 ACL/HAL 订阅者清单/双写注入 | 两套策略争电机 |
| 2 | 急停是否不依赖 ONNX/任务/日志？ | 逐进程 kill + 硬件急停测试 | 关键时刻停不住 |
| 3 | MC 全部异常时 HAL/驱动器能否独立保护？ | 杀 RT/断总线/驱动超时波形 | 无限沿用旧命令 |
| 4 | 每个 Action 是否有唯一 Manifest 和签名版本？ | Release 清单/SHA/签名 | 模型/参数不可查 |
| 5 | 关节名称/顺序/方向/零点是否三方确认？ | RobotDescription+标定 Golden | 电机反向/姿态错 |
| 6 | 模型所有输入/输出名/shape/dtype 是否加载前检查？ | 错配模型拒绝测试 | 隐性张量错位 |
| 7 | 每个 Action 是否有逐维 ObsSpec/ActionSpec？ | 训练/软件双签文件 | 同模型实机异常 |
| 8 | 每个 Action 是否至少一份 Golden？ | CI diff/版本记录 | 无法证明训练部署一致 |
| 9 | 旧 Epoch/过期推理是否永不下发？ | 故意延迟推理/切换竞态 | 切换后旧策略抢电机 |
| 10 | ActionGraph 所有开放边/非法边是否测试？ | 图覆盖报告 | 未受控危险切换 |
| 11 | Q2B/B2Q 是否有逐阶段守卫/超时/退路？ | Phase 表+每阶段故障试验 | 变形中断/倒地 |
| 12 | Overlay 是否有明确互斥 mask/退出规则？ | 组合 mask 检查/HIL | 承重关节双写 |
| 13 | 反馈过期/NaN/缺关节是否必阻断正常目标？ | 逐源故障注入 | 用错观测继续控制 |
| 14 | 速度 TTL 到期是否受控归零且有停车期限？ | 断流制动轨迹/距离 | 断网后继续走 |
| 15 | `switch_ready` 是否只在稳定且可退出时为真？ | 阶段事件/稳定窗试验 | 任务误判变形完成 |
| 16 | 是否有完整每拍黑匣子并可回放 30+10 s？ | `.mcbx` 导出/回放 diff | 故障无法定位 |
| 17 | RT/Worker 是否有 WCET 预算及超期动作？ | 24h 压力/ftrace/watchdog | 高负载控制中断 |
| 18 | 越权/重放/伪造速度是否被拒绝？ | STRIDE 注入/ACL 记录 | 外部攻击控制机器人 |
| 19 | OTA 是否整包签名并支持安全回滚？ | 篡改/断电/双槽演练 | 错版资产危险输出 |
| 20 | 每条实机 Action 边是否有本体/运控/软件/安全/测试签收？ | 开放边证据包/责任人签字 | 未验证能力被当量产 |

建议把第 1–3、5、9、11、13、17、20 项设为**高风险硬门槛**；任一否，暂停对应实机动作。

---

<!-- BEGIN_V12: P6-D16-QUIZ -->
#### [V1.2-解释] D16 读完自测

1. Checklist 中“是”凭什么证据？
2. 软件 36 PASS 能给第3项填“是”吗？
3. 哪个未闭环 P0 必须带进编码？

> 本节检查的是是否真正理解“输入→责任人→输出→失败兜底”，不是要求机械记忆字段。
<!-- END_V12: P6-D16-QUIZ -->

## V1.1 自评与残留

| 维度 | 满分 | 自评 | 说明 |
|---|---:|---:|---|
| 完整性 | 15 | 14 | D0–D16 保留，9 处修正 |
| 决策明确 | 15 | 14 | 九项有默认选择；硬件项待定 |
| 接口可实施 | 15 | 13 | proto/schema/时效明确；HAL 模式能力未交付 |
| 安全 | 15 | 12 | INIT/HAL 合同闭环到软件；电气/失稳未验证 |
| 实时/并发 | 10 | 7 | 5/10/30/15 ms 合同清楚；WCET 未测 |
| 可测试 | 10 | 8 | 36 个 SIL；HIL/实机缺失 |
| 可运维 | 5 | 4 | 黑匣子/指标/HAL 观测明确；规模待测 |
| 一致性 | 5 | 4 | 唯一 schema 已定义；生成代码/旧存档同步待实施 |
| 证据使用 | 5 | 5 | T1 仅参考；16 关节明示非 Collie |
| 可读性 | 5 | 5 | 变更/责任/阻断/测试可直接拆分 |
| **合计** | **100** | **86** | **可编码，不可上机** |

**残留 P0/P1（必须带进编码）**：

1. **P0**：`can_exit` 在 `step` 前发布 `READY` 的竞态（Part 2 §D3.5）；修法见 `REVIEW_V1.1.md` §2.1。
2. **P1**：`ExitKind` 的 proto 值（1/2/3）与 V1.1 C++ 伪代码（0/1/2）不一致；本合并版已改为 1/2/3，编码时必须由 proto 生成。
3. **P1**：`ModeTransitionPlan`、Q2B/B2Q phase 表尚未进入 Manifest/Schema。
4. **P1**：Factory 矩阵、HAL 能力表仍是文档/测试硬编码，需 `factory_matrix.yaml`/`hal_capabilities.yaml`。
5. **P2**：部分 Schema 语义（UNKNOWN 下 SAFE_HOLD、BUILTIN 路径、空 tensor/predicates、asset hash）需 `mcctl` 跨字段校验。
6. **P2**：V1.1 是变更单；本文件是合并阅读版，正式基线仍需生成完整 `V1.1_Full` 并跑全文章节/字段一致性。

---

**Part 6 完成度：100%（D13–D16 合并稿）；结论：可启动软件编码；真实运动/Q2B/B2Q/动态双足/Recovery 仍未获 HAL HIL、物理支撑、真实 Golden、RT 截止与安全签收，不能上机。**

---

<!-- BEGIN_V12: APPENDIX-CONCEPT -->
# 附录 D：概念讲透（用同一个动作串起来）

> `[V1.2-解释]` 所有例子沿用“上电 UNKNOWN→四足站立→四轮跟随→Q2B→双足手势→B2Q→急停→复位”。示例时间仅使用 V1.1 的目标值；Q2B/B2Q/Balance/Recovery 的 Collie 资产及实机验证均【待定】，**不允许运动使能**。
>
> **每项统一读法**：①是什么、②为什么、③不是什么、④例子、⑤链路位置、⑥所有权边界、⑦失败兜底、⑧章节、⑨三道自测。

## 01. HAL：为什么它不是“直接把数字发到电机”

1. **是什么**：硬件抽象层（HAL）在规范关节命令和具体驱动协议之间提供转换、权限校验、设备模式约束、ACK 与独立保护合同。
2. **为什么**：RT 只理解 `q_rad/dq_radps/tau_nm/kp/kd`，不同电机的 ID、方向、传动、编码器单位都不同。若每个 Runner 自己适配设备，既会双写，也没有统一超时保护。
3. **不是什么**：HAL 不会推理 ONNX，不负责选 Action，也不等于电机固件；固件/驱动器还必须拥有更低层的物理保护能力。【待定】目标设备是否已满足完整合同。
4. **具体例子**：RT 在 5 ms 边界发 `{writer_id,seq=101,epoch=7,deadline_ns,crc,16 joints...}`。HAL 先验独占 writer/seq/Epoch/截止/CRC/模式与范围，再把规范正方向转换为电机正方向；`seq=100` 重放被 `STALE_SEQ` 拒收，不能替系统续看门狗。`15 ms` watchdog 是【建议】，真实响应必须有电气/设备证据。
5. **位置**：`OutputGuard → HalCommand → HAL/driver → motor`；反向 `driver/IMU → HAL 规范反馈 → RT Snapshot`。
6. **拥有/禁止**：仅 mc_rt 持正常 writer 权限；HAL 自行发设备保护/拒收；mc_safety 只能撤销许可，不作为第二个正常 writer。
7. **失败兜底**：杀 RT → HAL 独立超时保护；断 HAL→电机总线 → 驱动侧独立失联动作【待验证】；若设备会无限保持最后指令，则硬件门禁失败、不可上机。
8. **位置**：D1.2、D5.6、D6.1、D7.3、D8.5；附录 A §1–§6。
9. **自测 3 问**：HAL 可以被 Runner 直接调用吗？旧 Epoch 命令为什么不能续看门狗？HAL 拒收了命令后，哪一层还能独立停止电机？

```mermaid
flowchart LR
 W["Worker 候选"] --> RT["mc_rt：Mux/Guard\n唯一正常 writer"] -->|"HalCommand：seq/epoch/CRC/deadline"| H["HAL：验权+适配+拒收"] --> DR["驱动/电机"]
 DR -->|"原始反馈"| H -->|"规范 q/dq/IMU"| RT
 ES["硬件急停"] -.->|"直接独立保护"| DR
 S["mc_safety"] -.->|"撤安全许可"| RT
```

**四个容易混淆的对象**：`mc_rt` 是决定这一拍发不发；HAL 是设备准不准收；设备驱动负责电流/总线/物理模式；电机是实际受控对象。HAL 的“唯一 writer”是设备侧权限合同，不是软件团队约定“大家别写”。

## 02. D1.3 逻辑模块 ≠ 进程/线程

1. **是什么**：模块是“某项职责的代码边界”；进程是 OS 隔离空间；线程是实际调度的执行流。一个进程可以放多个模块，一个模块可被几个线程以只读/写方式使用。
2. **为什么**：D1.3 画 13 个模块不意味着要部署 13 个服务，也不意味着每个模块跑 50 Hz。
3. **不是什么**：`ActionGraph` 是 Gateway 内的数据结构，不是一个独立实时节点；`ObservationBuilder` 是 Worker 里的函数/对象，而不是“观测进程”。
4. **例子**：`BodyVelocityRef` 被 Gateway 普通回调验来源并写固定邮箱，RT 在 5 ms 拍取最新速度，Worker 在 20 ms 拍构造观测；三个动作分别位于不同线程。
5. **位置**：用户请求→Gateway 的 Adapter/PolicyManager→Worker 的 Obs/Runner/Codec→RT 的 Mux/Guard→HAL。
6. **拥有/不能**：Gateway 只能提交切换请求；Worker 只能提候选；RT 只能读合规数据后发普通命令；HAL 管电机适配。
7. **失败**：Gateway 挂死使新任务受阻但不应拖住 RT；Worker 推理卡顿只会产生过期候选；RT 死亡交给 HAL watchdog。
8. **章节**：D1.2–D1.4、D5、D8.1–D8.2。
9. **自测**：一个模块必须独占一个线程吗？速度从 DDS 回调能直接写 HAL 吗？哪个模块在 RT 里处理 `ActionEpoch`？

| 逻辑模块 | 进程/线程 | 输入→输出 | 它不负责 |
|---|---|---|---|
| MotionApiAdapter | Gateway / rpc | RPC→已认证领域请求 | 关节输出 |
| PolicyManager / ActionGraph | Gateway / 控制调度 | 请求+图→合法路径+准备事务 | 直接提交 Epoch |
| Registry / ManifestValidator | Gateway + Worker loader | 配置/签名→可用 Runner 定义 | 每拍发令 |
| ObservationBuilder | Worker / step 50 Hz | Snapshot/Reference→tensor | 源权限仲裁 |
| InferenceBackend / Runner | Worker / step | tensor/反馈→raw output | HAL 写权限 |
| ActionCodec | Worker / step | raw→规范关节候选 | 物理安全限额的最终判定 |
| Snapshot / VelocityArbiter | RT / 5 ms | HAL 反馈+速度源→有效快照/参考 | 网络鉴权 |
| SwitchCoordinator | RT / 5 ms | 准备状态+Decision+HAL pending→Epoch | 同步等待 Worker |
| JointMux / ModeTransition / Guard | RT / 5 ms | 候选+mask+安全→合法设备目标 | 任意神经网络调用 |
| MotionStatusPublisher | Gateway / 20 ms | RT 状态镜像→50 Hz 状态 | 改 RT 控制 |
| MotionSafetyKernel | Safety / 10 ms | 设备/姿态健康→SafetyLease | 普通 writer |
| HAL validator + driver adapter | device_hal / 设备线程 | HalCommand→驱动协议+ACK | ActionGraph |

**单次调用链**：`SetBehavior(quad_stand)` → Adapter → PolicyManager → Registry → Worker.enter/step → RT.SwitchCoordinator → JointMux → OutputGuard → HAL；反馈由 HAL 经 Snapshot 回 Worker，形成下一次计算。不要把这条链理解成一个函数同步调用到底。

## 03. 五个限界上下文：五个责任区，而不是五个进程

1. **是什么**：限界上下文是五块各自定义并负责核心概念的业务/软件责任区，类似五个有明确交接单的部门。
2. **为什么**：没有边界时，Task 直接改 Runner 状态、模型代码直接改 HAL、Safety 与业务抢“谁停机”，一个动作改动就影响所有模块。
3. **不是什么**：不是必须产生五个微服务；V1.1 实际是四个 MC 进程 + 设备 HAL，且一个上下文可跨进程。
4. **例子**：任务说“站立”首先进 Motion API 检 Session；Orchestration 找合法 Action；Runner Runtime 生成候选；Joint Control 把候选变唯一目标；Motion Safety 可以在任一点撤销正常运动许可。
5. **位置**：下表按职责流排列，跨区只传明确的请求/状态/候选/许可。
6. **拥有**：每区负责自己对象的真实性，不允许上一区直接改下一区内部状态。
7. **失败**：例如 API 失败只应阻止新请求，不该阻塞设备级保护；Safety 进程故障由 SafetyLease 超期触发 RT 保护。
8. **章节**：D2.1，交叉 D1、D3、D4、D7。
9. **自测**：为什么五个区不是五个线程？哪一区定义 ActionGraph？哪一区保证每关节只有一个目标？

| 责任区 | 它回答的问题 | 管什么／不管什么 | 交接凭据 |
|---|---|---|---|
| ① Motion API | 谁请求的？是否有权？ | Session、请求/响应；不改电机 | `ActionRequest` |
| ② Motion Orchestration | 何时换哪个动作？ | PolicyManager、ActionGraph、Bundle；不直接写 Epoch | `PreparedSwitch` |
| ③ Runner Runtime | 怎样算候选？ | Manifest、ObsSpec、Runner、Backend；不碰 HAL | `RunnerOutput` |
| ④ Joint Control | 本拍准许输出什么？ | Snapshot、Epoch、Mux、Guard；不处理产品业务 | `HalCommand` |
| ⑤ Motion Safety | 是否还允许正常运动？ | SafetyLease、Fault、状态；不做常规行为规划 | Lease/撤销事件 |

```mermaid
flowchart LR
 A["API\n身份/请求"] --> B["Orchestration\n动作/切换"] --> C["Runner Runtime\n候选"] --> D["Joint Control\n唯一目标"] --> H["HAL"]
 E["Motion Safety\n独立许可"] -.->|"撤销/约束"| D
```

## 04. ControlLease：权限在链路的哪一站发挥作用

1. **是什么**：ControlLease 是“谁在一段 TTL 内独占某个运动 scope”的租约，其状态 `IDLE→REQUESTED→GRANTED→RENEWING→REVOKING→REVOKED/EXPIRED`。
2. **为什么**：即使 Task 与遥控都已登录，不能允许它们同时改四轮速度；普通“优先级高就覆盖”可能在一拍内交错发出非零命令。
3. **不是什么**：Session 不等于独占运动权；SafetyLease 不等于资源竞争裁决；HAL writer lease 不等于导航/遥控“谁能占方向盘”。
4. **例子**：导航 lease `L1` 在 500 ms TTL 内每≤150 ms 续租【建议】；遥控申请更高优先级时，PolicyManager 将 L1→REVOKING，RT 执行已批准停车/稳定验证，再授予 L2；不能让两个 lease 在同一个 scope 同时 GRANTED。
5. **位置**：Gateway 申请/仲裁，RT 验引用中的 lease_id/source/seq/到期，Safety 独立发 SafetyLease，HAL 独立认 writer。
6. **拥有/禁止**：PolicyManager 是控制资源租约签发者；导航只能使用被签发的 lease，不能自己创建、延长或继承旧 lease。
7. **失败**：失联后 TTL 不续 → 速度来源失效→制动/按相位 fallback；Balance 不能简单关电，要用已批准的安全动作，否则交给设备保护并记录跌倒风险。
8. **章节**：D2.5、D4.4、D6.5、D7.4、附录 A §1。
9. **自测**：控制者已登录但没 lease 会怎样？高优先级抢占是否可以跳过停车？SafetyLease 过期了，有 ControlLease 还能动吗？

```mermaid
sequenceDiagram
 participant N as Nav L1
 participant G as Gateway/PolicyManager
 participant R as mc_rt
 participant C as RC L2
 N->>G: 续租 L1（有效）
 C->>G: 请求接管 scope=base
 G->>G: L1→REVOKING
 G-->>R: 撤旧源、请求获批制动
 R-->>G: 停车/安全条件确认
 G-->>N: L1=REVOKED
 G-->>C: L2=GRANTED（独占）
 C->>R: 新 lease_id+seq+TTL 的速度
```

**四钥匙同时成立**：身份 `Session` → 资源 `ControlLease` → 运动安全 `SafetyLease` → 设备 `HAL writer`。它们发放周期不同、失效场景不同，不能合成一个 boolean。

## 05. RunnerManifest：身份证 + 菜谱 + 守卫 + 验收单

1. **是什么**：RunnerManifest 是 Runner 的静态加载合同，说明“我是哪个 Action、用什么机制/后端、读什么输入、输出哪些关节、进入退出条件和失败去向”。
2. **为什么**：只给 ONNX，软件不知道训练输入第 34 维是轮速还是 IMU、输出哪个关节、哪个形态能进入、需要什么版本。
3. **不是什么**：不是 ActionGraph（图决定可达路径）；不是 Bundle（组合多个 Runner）；不是 RobotDescription（本体事实）；也不等于权重本身。
4. **例子**：`quad_stop` 的 Manifest 写 `execution_kind=CLASSICAL,behavior_role=POSE,class_id=ClassicalPoseRunner`，`owns` 是腿/轮关节、`asset.kind=BUILTIN`、ObsSpec/ActionSpec/Golden 有 SHA；`release.status=CANDIDATE` 因没有真实签发不能动。
5. **位置**：Gateway Registry 在计划动作时读取；Worker loader 校验后实例化；RT 只接受与该 Manifest 哈希一致的候选。
6. **拥有/不能**：配置由运控与软件共同签收；Runner 不可运行中改写 Manifest；安全限额与本体零点从其他唯一权威取。
7. **失败**：路径/hash/接口缺失→`runtime.asset_state=BROKEN`，不加载；发布状态未 APPROVED→不执行；Golden 错位→在发布前阻断。
8. **章节**：D3.1–D3.4、D4.1、D9.1–D9.6、附录 B §4–5。
9. **自测**：Manifest 和 Model 谁定义维度含义？`release.status=APPROVED` 就保证当前可运行吗？为什么 owns_mask 不应写成“自动抢全部关节”？

| 字段组 | 它像什么 | 示例说明 | 缺少/不一致 |
|---|---|---|---|
| `manifest_id/version/action_id/behavior_id` | 身份证 | 这是 `quad_stop` 哪个版本 | 重复/未知拒收 |
| `robot_compatibility` | 适用机器列表 | topology/calibration SHA | 型号不匹配拒收 |
| `runner.execution_kind/behavior_role/class_id/backend_id` | 执行菜谱 | CLASSICAL×POSE→ClassicalPoseRunner | 无唯一工厂拒收 |
| `runner.abi_version/period_ms/worker_budget_ms` | 运算约束 | 20 ms/≤15 ms【建议】 | 算不完候选作废 |
| `asset.kind/path/sha256`, `tensor_io` | 食材+输入输出接口 | `MODEL` 与模型张量 | 模型空端口/错哈希拒收 |
| `obs_spec`, `action_spec`, `owns` | 处理步骤+归属 | 16 维演示观测/16 关节输出 | 映射/方向错误拒收 |
| `entry/exit/completion`, `failure_target` | 安全守卫 | 支撑有效/可退出/超时保护 | 不可无条件过渡 |
| `golden`, `release.status` | 验收单 | 固定向量通过/审批状态 | 无签发不可运动 |

```mermaid
flowchart LR
 R["RobotDescription\n本体事实"] --> M["RunnerManifest\n执行合同"]
 S["ObsSpec/ActionSpec\n逐维配方"] --> M
 A["asset: ONNX/轨迹\n可校验内容"] --> M
 G["Golden\n模型输出回归"] --> M
 M --> REG["Registry/Worker 加载"]
 B["ActionBundle\n主+叠加"] --> REG
```

**注意**：V1.1 评审指出 ModeTransitionPlan/phase、Factory 矩阵、HAL 能力表尚未全部机器化；这些不是已完成的配置合同。建议在编码前新增对应 schema/validator，不能仅看上表就宣布可物理切换。

## 06. “八类 Runner”不是 24 个算法

1. **是什么**：`ExecutionKind` 表示计算机制（ONNX/CLASSICAL/PLAYBACK/COMPOSITE）；`BehaviorRole` 表示用途（LOCOMOTION/TRANSITION/BALANCE/POSE/RECOVERY/OVERLAY）；二者组成 RunnerFactoryRegistry 的精确键。
2. **为什么**：`WheelDriveRunner` 是轮式移动角色/经典路径的历史类名，`RlLocomotionRunner` 是 ONNX 移动机制名，不能凭名字猜同一个四轮动作该用哪个。
3. **不是什么**：4×6=24 个坐标格不是 24 个已实现 Runner。`—` 表示默认不支持；部分格子映射到**同一** `TransitionRunner` 类，通过不同 backend 实现。
4. **例子**：四轮 ONNX 移动 `(ONNX,LOCOMOTION)→RlLocomotionRunner`；经典轮速控制 `(CLASSICAL,LOCOMOTION)→WheelDriveRunner`，它们的 `Behavior` 都可以叫“跟随”。
5. **位置**：Manifest 指定两个维度，FactoryRegistry 唯一选 class 与 backend，Worker 实例化；Bundle 再决定是否和 Overlay 共存。
6. **拥有/禁止**：Registry 必须检查唯一映射；开发者不能因为某两个类“看起来都合理”就手工双注册。
7. **失败**：tuple 未注册/不匹配 backend 或 class→`MANIFEST_CLASS_MISMATCH`，禁止回退到另一种算法“凑合运行”。
8. **章节**：D3.3–D3.4、D4.1、附录 B §4。
9. **自测**：一个 ONNX 四轮 Action 为什么不是 WheelDriveRunner？一个格子里复用 TransitionRunner 会创建两个类吗？Overlay 为什么还必须检查 owns_mask？

| ExecutionKind \ BehaviorRole | LOCOMOTION | TRANSITION | BALANCE | POSE | RECOVERY | OVERLAY |
|---|---|---|---|---|---|---|
| ONNX | RlLocomotionRunner | TransitionRunner | BalanceRunner | — | RecoveryRunner | OverlayRunner |
| CLASSICAL | WheelDriveRunner | TransitionRunner | BalanceRunner | ClassicalPoseRunner | RecoveryRunner | OverlayRunner |
| PLAYBACK | — | TransitionRunner | — | PlaybackRunner | — | OverlayRunner |
| COMPOSITE | — | TransitionRunner | — | — | — | OverlayRunner |

| Running Example 场景 | 行为角色 | 执行机制 | 唯一 class | backend 举例 | 为什么 |
|---|---|---|---|---|---|
| 四轮经典速度行驶 | LOCOMOTION | CLASSICAL | WheelDriveRunner | classical_builtin | 速度到轮/腿经典控制 |
| 四轮 RL 跟随 | LOCOMOTION | ONNX | RlLocomotionRunner | onnxruntime_cpu | 由网络给候选 |
| Q2B/B2Q 变形 | TRANSITION | ONNX/CLASSICAL/PLAYBACK（资产选一种） | TransitionRunner | 对应确定 backend | 具有 phase 与支撑守卫 |
| 双足持续平衡 | BALANCE | ONNX | BalanceRunner | onnxruntime_cpu | 需连续响应姿态/接触 |
| 四足站姿/静态姿态 | POSE | CLASSICAL | ClassicalPoseRunner | classical_builtin | 已批准姿态保持/整形 |
| 倒地后的受限恢复 | RECOVERY | ONNX/CLASSICAL（待验证） | RecoveryRunner | 对应 backend | 安全授权/净空/次数限制 |
| 预录动作/轨迹片段 | POSE | PLAYBACK | PlaybackRunner | trajectory_engine | 需要带时标的参考轨迹 |
| 双足讲解手势 | OVERLAY | CLASSICAL/PLAYBACK | OverlayRunner | 对应 backend | 只拥有明确不冲突的上肢 mask |

**类名归类**：`RlLocomotionRunner` 含机制词 `Rl`；`WheelDriveRunner` 含具体行为词；`TransitionRunner/BalanceRunner/ClassicalPoseRunner/RecoveryRunner/PlaybackRunner/OverlayRunner` 混合了角色与机制描述。名字不作为工厂决策依据，**唯一事实源是两维 tuple + 注册矩阵**。表中八类是八个“已规划的类名”，不表示八类已发布、已训练或已真实部署。

## 07. D3.7 三条时序图：把一条箭头翻译成一句人话

1. **是什么**：时序图横向是参与者，纵向从上到下是时间，`→` 表示发请求/送数据，`-->>` 表示异步返回/状态镜像；中间没有箭头不意味着线程停着等。
2. **为什么**：如果不看时序，容易把 Worker 的 50 Hz、RT 的 200 Hz 和 HAL 的高频控制当作一次同步调用，以为每拍都必须等模型出答案。
3. **不是什么**：图是协议中的因果顺序，不是实测毫秒曲线；所有时限必须用 timestamp/ftrace/硬件示波器确认。
4. **例子**：一个 Worker 20 ms tick 在 t=0 得到 Snapshot，t≈15 ms 以内生成候选；RT 在 t=0、5、10、15、20 ms 各运行一次，不等 t=15 才执行；HAL 按合同接受有效新 seq。时间仅为预算示意。
5. **位置**：D3.7 三图贯穿 HAL、RT、Worker、Task、Safety。
6. **拥有/不能**：Worker 的候选没有授权直接成为设备目标；RT 的 `PREPARE_EPOCH` 不意味着 HAL 已接管；急停硬件不等待 Safety 响应。
7. **失败**：候选错过 `deadline` → RT 丢弃；旧 Decision 不可信 → WAIT；新 epoch HAL 拒收 → 保护；硬件急停直接停机链。
8. **章节**：D3.7、D3.5、D4.5、D5.7、附录 A §2/§5，评审 §2.1。
9. **自测**：三条图最重要的独立时钟是什么？`PREPARE_EPOCH` ACK 能代替 `READY` 吗？哪个箭头完全绕过 ONNX？

**六步读图法**：①先数参与者；②找第一个触发；③按时间从上向下读箭头；④每条箭头问“这是什么字段”；⑤在空白处标“谁仍在按自己的周期运行”；⑥补上失败分支和过期检查。

### 07-A. 正常四轮单拍：参与者与逐箭头读法

参与者：HAL（反馈/设备）、RT（5 ms 唯一出口）、Worker（20 ms 候选）、Inference（Worker 内后端）。

| 次序 | 图中的箭头 | 人话、数据与时间 | 失败分支 |
|---:|---|---|---|
| 1 | HAL → RT `joint/IMU` | 设备把带时间戳的真实反馈交给 RT | 老帧/NaN→Snapshot invalid |
| 2 | RT → RT `snapshot/ref/epoch/deadline` | 在自己 5 ms 拍冻结这一次输入 | Velocity TTL 过期→制动引用 |
| 3 | RT → Worker `snapshot+ref` | 把只读输入交非 RT 计算，最多最新有效槽 | Worker 慢不拖住 RT |
| 4 | Worker → Worker `Obs+history` | ObsSpec 决定维度顺序/历史 | 缺必要观测→候选无效 |
| 5 | Worker → Inference `named tensors` | ONNX 按名称/dtype/shape 运算 | Backend 超时/错 shape→无候选 |
| 6 | Inference → Worker `outputs` | 得到网络原始数值 | NaN/Inf→Fault |
| 7 | Worker → RT `candidate+decision` | ActionCodec 转规范关节目标，附 epoch/deadline/manifest | 迟到/旧 epoch/旧 Decision→拒绝/WAIT |
| 8 | RT → RT `Guard/Lease` | 再检查所有权、模式、限幅、安全许可 | 一项失败→不发正常命令 |
| 9 | RT → HAL `HalCommand 200Hz` | 经 HAL 检验后才可能到电机 | HAL 拒收→保护，不续设备狗 |

```mermaid
sequenceDiagram
 participant H as HAL
 participant R as RT 5ms
 participant W as Worker 20ms
 participant I as ONNX backend
 H-->>R: 反馈含时间戳
 R-->>W: Snapshot + VelocityRef + epoch
 W->>W: ObsSpec + history
 W->>I: named tensors
 I-->>W: raw output
 W-->>R: Codec 候选（deadline）
 R->>R: Age/Epoch/Mux/Guard/SafetyLease
 R-->>H: 只有合规 HalCommand
 Note over R: RT下一拍自行运行，不等Worker
```

### 07-B. Q2B 切换：参与者与逐箭头读法

参与者：Task（想转双足）、PolicyManager（找路径/准备）、Worker（Runner 进入与候选）、RT（Epoch 单点提交）、HAL（Epoch 准备与硬件接受）。

| 次序 | 消息/阶段 | 为什么 | 失败分支 |
|---:|---|---|---|
| 1 | Task → Policy `SetBehavior(biped)` | 表达意图，不表示准许改变关节 | Session/Lease/Release 不合格→REJECTED |
| 2 | Policy → Graph | 选 Drive→Stop→Q2B→Balance | Graph 禁边或资产 DISABLED→拒绝 |
| 3 | Policy → Worker `preload/enter` | 先准备目标首拍，不夺旧 Epoch | model/phase/Golden 不匹配→旧动作不变 |
| 4 | Worker → RT `candidate/ExitDecision` | Worker 的 Decision 表示旧 Runner 是否可退出 | **pre-step READY 竞态 P0**：不可当已修 |
| 5 | RT → HAL `PREPARE_EPOCH` | 先让设备准备新版本，仍允许旧版本出令 | HAL 未准备/超时→不提交 |
| 6 | RT 本地 `read/commit` | 每 5 ms 查 Decision+支撑+SafetyLease+首候选，然后原子换 Epoch | 任何条件缺失→WAIT/保护，RT 不阻塞 |
| 7 | RT → HAL `new_epoch first command` | HAL 原子将 pending→active；旧 epoch 永久失效 | 第一命令拒收→保护、不能普通回旧 |
| 8 | RT/Worker → Task `phase/status` | Q2B 到稳定双足需真实支撑判据 | phase 超时/失接触→已批准 fallback/保护 |

```mermaid
sequenceDiagram
 participant T as Task
 participant P as PolicyManager
 participant W as Worker
 participant R as RT
 participant H as HAL
 T->>P: SetBehavior(biped_balance)
 P->>P: Graph: Stop→Q2B→Balance
 P-->>W: preload/enter target
 W-->>R: candidate + sealed decision
 R-->>H: PREPARE_EPOCH（非阻塞）
 H-->>R: pending ready（状态镜像）
 Note over W,R: P0: pre-step READY 可能先于step故障/相位变更
 R->>R: 只读并验新鲜/支撑/Lease/Guard
 alt 满足全部条件
 R-->>H: new_epoch command
 H-->>R: ACK active_epoch=new
 else 条件不足
 R->>R: WAIT/保护，不等Worker
 end
```

**需要标在图旁的 P0**：V1.1 `can_exit → publish READY → step()` 这条顺序允许 READY 先出现，随后 `step` 挂死、输出 NaN，或进入 Q2B 不可中断 phase。RT 在过期前仍可能接纳 READY。**推荐的改法是 READY 只在成功 step 后封存并绑定完成序号/phase/fault，写成生产测试前不得开放新动作边**；本解释文档不悄悄替换 V1.1。

### 07-C. 急停/反馈过期：参与者与逐箭头读法

参与者：物理急停/传感器、SafetyKernel、RT、HAL/驱动。

| 次序 | 箭头 | 含义 | 失败分支 |
|---:|---|---|---|
| 1 | 急停→HAL/驱动 | 电气路径直接动作，不经计算 | 独立电气链失效→硬件门禁失败 |
| 2 | 急停/反馈异常→Safety | 故障锁存、停止签发 SafetyLease | Safety 线程死亡→RT 等租约到期 |
| 3 | Safety→RT `REVOKE` | 使正常动作失去许可 | IPC 丢包仍由租约过期保护 |
| 4 | RT→RT `drop candidates` | 不再使用普通模型输出，不能沿用无限旧目标 | RT 本身死掉→HAL watchdog |
| 5 | RT→HAL `approved protection` | 若物理条件允许则发送已批准保护目标 | 未验证的保持/阻尼不可假装安全 |
| 6 | HAL→驱动 `local protection` | 设备自主保护，不依赖上游运行 | 需真实驱动/HIL 签收 |

```mermaid
sequenceDiagram
 participant E as EStop/Sensor
 participant S as mc_safety
 participant R as mc_rt
 participant H as HAL/Driver
 E-->>H: 物理急停直接输入
 E-->>S: fault/invalid feedback
 S-->>R: fault latch / revoke SafetyLease
 R->>R: 不采纳普通候选
 R-->>H: 仅获批保护（如果可用）
 H->>H: 独立 watchdog/驱动保护
 Note over H: 即使RT/Worker已死，物理链仍须有效【待验证】
```

### 07-D. 20 ms/5 ms/约 1 ms 一条时间轴

```text
时间(ms)     0    5   10   15   20   25   30   35   40
HAL目标      |----|----|----|----|----|----|----|----| ...【待定】
RT拍         R0   R1  R2   R3   R4   R5   R6   R7   R8
Worker       W0================>候选0(预算≤15ms)       W1================>候选1
             |-------- 20ms tick --------|---------- 20ms ------|
安全核       S0                    S1                    S2     ...
```

这里 `R1` 绝不会“等候选 0 到达”；它要么在时效范围内使用上一条合格候选并整形，要么采取批准的降级路径。**15 ms/20 ms** 是 Worker 预算，**2.1 ms/5 ms** 是 RT 目标预算；两者不是模型计算时间与电机接令延迟的实测数据。

## 08. 五个运行主体：前台、后厨、出菜口、安全员、司机

1. **是什么**：Gateway=前台接单和排队；Worker=后厨按菜谱做候选；RT=唯一出菜口，按规则核对；Safety=安全员，有权撤许可；HAL=设备司机，知道设备能否执行。
2. **为什么**：把模型耗时、网关拥塞、设备响应与安全判断分开，才能解释不同故障不会按同样方式扩散。
3. **不是什么**：五个比喻不对应五个等价优先级；四个是 MC 进程，HAL 是独立设备侧角色。
4. **例子**：Worker 卡 50 ms，RT 仍每 5 ms 做时效检查；超出 hold 窗后不继续正常指令；HAL 不能因“最新收到旧 cmd”无限续狗。
5. **位置**：Gateway→Worker→RT→HAL 是主链，Safety→RT/HAL 是横向保护。
6. **拥有/不能**：见映射表，普通 RPC 不进 RT 回调；只有 RT 有正常设备 writer。
7. **失败**：Gateway 死新请求失败；Worker 死无新候选；RT 死 HAL 自主超时；Safety 死 Lease 过期；HAL/驱动无法保护则不可上机。
8. **章节**：D1.2、D8.1–D8.5、附录 A。
9. **自测**：为什么 Worker 是非 RT？为什么 Gateway 不能直接调用 HAL？Safety 进程死了之后的最后保护在哪？

| 主体 | 周期/线程性质【建议】 | 主数据 | 失败后接力者 |
|---|---|---|---|
| `mc_gateway` | RPC 非实时 + 20 ms status | ActionRequest/Graph/ControlLease | RT/Safety/HAL |
| `mc_runner_worker` | 50 Hz step；loader 非实时 | Snapshot→RunnerOutput | RT 超期丢弃 |
| `mc_rt` | 200 Hz RT；FIFO90 仅示意 | Snapshot/Candidate→HalCommand | HAL watchdog |
| `mc_safety` | 100 Hz 专用核目标；FIFO92 仅示意 | Sensor health→SafetyLease | RT 失租+HAL |
| `device_hal` | 约 1 kHz 目标设备循环【待定】 | HalCommand/Status/反馈 | 设备侧超时/急停 |

## 09. D9.1 四级配置：一份完整 Action 不止一个 YAML

1. **是什么**：配置按本体层、系统层、Action 层、策略层四级组织，每一级对齐不同事实/签发者。
2. **为什么**：模型不应自己定义电机方向，Action 不应私藏新的安全限位；所有资产必须可溯源、可校验、可复现。
3. **不是什么**：四级不是“严格四个文件”；每一级都有多份文件，之间以 ID/SHA/规范 joint name 引用。
4. **例子**：`quad_stop` 需要有效本体标定、系统 Graph 和安全包络、Bundle/Manifest、经典/内置控制资产、Obs/ActionSpec、Golden、Release 签发。
5. **位置**：Registry/Worker 加载时按依赖顺序验证；RT 不在控制拍读 YAML；HAL 按签发的本体映射验证。
6. **拥有/禁止**：本体/HAL 签发 RobotDescription；平台/安全签发安全配置；运控/软件签 Manifest；训练/运控签模型与逐维规格；发布平台整包验签。
7. **失败**：任何 SHA/拓扑/模式/Golden/审批不一致标不可用；不能“跳过这个字段继续跑”。
8. **章节**：D9.1–D9.6、D4.1、附录 B §3–§7、附录 C。
9. **自测**：关节 `direction` 应写在哪一级？一个 `CANDIDATE` 的 model 会进入 ACTIVE 吗？哪一级决定能否从 quad_drive 切到 quad_stop？

| 层 | 回答什么 | 文件举例 | 签发/加载者 | 失败结果 |
|---|---|---|---|---|
| ① 本体 | 我控制的是哪台机器？关节真实方向/限位？ | `robot_description.yaml` + `calibration` | 本体/HAL → Registry/HAL | topology/calibration 错拒绝 |
| ② 系统 | 允许谁控制、可走哪些边、安全边界？ | `velocity_sources.yaml`、`action_graph.yaml`、`safety_limits.yaml`、`deployment.yaml` | 平台/MC/安全 → Gateway/RT | graph/限额错误禁止启动/动作 |
| ③ Action | 哪个 Runner、哪些关节、何时进出？ | `bundles/quad_stop.yaml`、`manifests/quad_stop.yaml` | 运控/软件 → Registry/Worker | Manifest/Factory/Ownership 错拒绝 |
| ④ 策略 | 模型的每一维读写什么、期望输出多少？ | `builtin/quad_stop.yaml`、`specs/*.csv`、`golden/*` | 训练/运控 → Worker/CI | tensor/Golden 错拒绝 |

### 09-A. `quad_stop` 完整文件树（教学包，不能部署）

```text
release/demo16-quad-stop-CANDIDATE/
├── robot/robot_description.yaml
├── robot/calibration.yaml                         # 占位；未签发
├── system/velocity_sources.yaml
├── system/action_graph.yaml                       # 仅 nodes/edges
├── system/safety_limits.yaml                      # approved=false
├── system/deployment.yaml
├── bundles/quad_stop.yaml                         # primary + owns_mask
├── manifests/quad_stop.yaml                       # 2维Runner选择+asset/spec/Golden引用
├── builtin/quad_stop.yaml               # 内置经典停止策略；不加载模型
├── specs/quad_stop_obs.csv                         # 21列×16行示例
├── specs/quad_stop_action.csv                      # 16列×16行示例
├── golden/quad_stop_fixture.json                   # 观测→raw→codec参考（虚构）
└── release_manifest.yaml                          # release.status=CANDIDATE，无有效签名
```

**注意**：这是用“`quad_stop` 采用 CLASSICAL+POSE、BUILTIN”建立的**可理解文件引用闭环**，不是已有可运行策略。`models/*.placeholder` 不是合法 ONNX，不可通过模型加载；不能把虚构 SHA 写成真实签名。V1.1 的 `demo16` 16 关节仅用于接口测试，**不是 Collie 事实**。

### 09-B. 全套引用与加载顺序（用一条链看清楚）

```mermaid
flowchart LR
 RL["release_manifest\n签名+文件SHA"] --> RD["RobotDescription\n关节表/标定"] --> SY["system config\nGraph+Safety+source"]
 SY --> BD["Bundle\nprimary=quad_stop"] --> MF["RunnerManifest\nCLASSICAL×POSE"]
 MF --> MD["model\nIO/sha"]
 MF --> OB["ObsSpec\n21列"]
 MF --> AC["ActionSpec\n16列"]
 MF --> GO["Golden\n已签收向量"]
 GO --> RG["可准入？\n当前示例：否"]
```

```yaml
# system/action_graph.yaml：与 Appendix B 的 nodes 根一致；演示边，不可部署
schema_version: '1.1'
nodes: [quad_stand, quad_drive, quad_stop, q2b, biped_balance, b2q]
edges:
  - {from: quad_drive, to: quad_stop, cost: 1, guard: [feedback_fresh],
     max_duration_ms: 1500, on_timeout: DAMPING}
```

```yaml
# bundles/quad_stop.yaml：解释性结构，不声称通过现存 JSON Schema
bundle_id: quad_stop_bundle
primary: quad_stop
owns: [fl_hip, fl_thigh, fl_calf, fr_hip, fr_thigh, fr_calf,
       rl_hip, rl_thigh, rl_calf, rr_hip, rr_thigh, rr_calf,
       fl_wheel, fr_wheel, rl_wheel, rr_wheel]
overlay_slots: []
combination_rules: {allow_overlap: false}
```

```yaml
# manifests/quad_stop.yaml：完整字段组的教学映射；具体嵌套格式仍以 schema 为准
schema_version: '1.1'
manifest_id: demo16_quad_stop
version: '0.0.0-demo'
action_id: quad_stop
behavior_id: stop_follow
robot_compatibility: {robot_ids: [demo16_nonphysical], topology_sha256: PLACEHOLDER,
                      calibration_sha256: PLACEHOLDER}
runner: {execution_kind: CLASSICAL, behavior_role: POSE,
         class_id: ClassicalPoseRunner, backend_id: classical_builtin,
         abi_version: '1', period_ms: 20, worker_budget_ms: 15}
asset: {kind: BUILTIN}
tensor_io: {inputs: [{name: demo_obs, dtype: FLOAT32, shape: [1,16], semantic: observation}],
            outputs: [{name: demo_act, dtype: FLOAT32, shape: [1,16], semantic: joint_action}]}
obs_spec: {path: specs/quad_stop_obs.csv, sha256: PLACEHOLDER}
action_spec: {path: specs/quad_stop_action.csv, sha256: PLACEHOLDER}
owns: [fl_hip, fl_thigh, fl_calf, fr_hip, fr_thigh, fr_calf,
       rl_hip, rl_thigh, rl_calf, rr_hip, rr_thigh, rr_calf,
       fl_wheel, fr_wheel, rl_wheel, rr_wheel]
entry: {predicates: [support_valid, feedback_fresh], max_duration_ms: 1000}
exit: {predicates: [velocity_zero, stable], max_duration_ms: 1500}
completion: {predicates: [velocity_zero, stable], stable_ms: 200, max_duration_ms: 1500}
failure_target: DAMPING
golden: {path: golden/quad_stop_fixture.json, sha256: PLACEHOLDER}
release: {release_id: demo16_quad_stop, status: CANDIDATE}
```

**为什么不能靠这些 YAML 上机**：`PLACEHOLDER` 不是真 SHA；模型不存在；标定/拓扑不是真实 Collie；`ModeTransitionPlan`、HAL capabilities、Factory 矩阵的机器化仍是 V1.1 P1；`release.status=CANDIDATE` 禁止正式运动。发布前必须换成已校验、签发、通过 SIL/HIL 的资产，且 P0 竞态先关闭。

### 09-C. 读 CSV 时只看哪几列

| 文件 | 示例行（摘要，不是完整 CSV） | 意义 | 若搞错 |
|---|---|---|---|
| ObsSpec | `demo_obs,0,joint_pos,...,fl_hip,rad,...,history_lag=0` | 第 0 维是规范 FL hip 角 | 训练/部署观测错位 |
| ActionSpec | `demo_act,0,fl_hip,POSITION,rad,...,sign=1` | 原始第 0 维解码到 FL hip | 方向/增益错误 |
| Tensor IO | `demo_obs [1,16]→demo_act [1,16]` | 张量端口和 CSV 每维闭合 | 任意缺维应拒绝加载 |
| RobotDescription | `joint_order[0]=fl_hip; direction=±1` | 唯一本体方向映射 | 硬件关节反向 |

完整 16 行 CSV 采用 V1.1 Appendix B 指向的 `examples/demo16_obsspec.csv`、`examples/demo16_actionspec.csv`，不能在教学片段里用“其余类推”代替正式交付。


## 10. Behavior / Action / ActionExecution

1. **一句话定义**：Behavior 是面向业务的能力，Action 是可注册定义，ActionExecution 是一次运行实例。
2. **为什么需要**：同一个“跟我走”能力可以从经典轮驱实现替换成 ONNX，而任务接口不改。
3. **它不是什么**：不是每收到一个 ActionRequest 就生成一种新 Runner 类。
4. **具体例子**：Task 发跟随请求产生 execution_id=E1，下一次重复启动是 E2；当前 Epoch 在 E1/E2 之间切换。
5. **链路中的位置**：Task→Gateway/PolicyManager→Registry/Worker。
6. **谁拥有、谁不能做**：PolicyManager 拥有执行实例与状态；Runner 不能定义产品能力。
7. **失败与兜底**：未发布的 Action REJECTED；已接收不等于物理稳定。
8. **对应文档**：D0/D2/D4。
9. **自测 3 问**：Task 应绑定 Behavior 还是模型文件？ Action 与 execution_id 能否复用同一个含义？ RPC ACCEPTED 就表示站稳吗？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | SetBehavior/ActionRequest |
| 输出 | ActionExecution + action_id |
| 必须通过的门 | Graph/Release/ControlLease |

## 11. ActionGraph

1. **一句话定义**：ActionGraph 是 Action 间合法有向边的表；根字段统一为 nodes。
2. **为什么需要**：从行走到变形必须先减速停稳，不能跨过 quad_stop。
3. **它不是什么**：不是存放安全状态 ESTOP/INIT 的图。
4. **具体例子**：quad_drive→quad_stop→q2b；Q2B 禁用时路径不可执行。
5. **链路中的位置**：Gateway PolicyManager 的路径/准入阶段。
6. **谁拥有、谁不能做**：Gateway 拥有 Graph；RT 只执行已准备的切换，不现场搜索图。
7. **失败与兜底**：缺边/守卫失败拒绝或 WAIT，安全抢占绕过图。
8. **对应文档**：D4.2、D9、附录 B §3。
9. **自测 3 问**：为什么安全态不放 nodes？ 边 guard 和真实接触检查是一回事吗？ 删除 quad_stop 边会怎样？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 当前 Action/目标 Action |
| 输出 | 合法 Path + guards |
| 必须通过的门 | 节点 release + guard + deadline |

## 12. ActionBundle 与 Ownership

1. **一句话定义**：Bundle 只有一个 Primary，Overlay 占各自声明的关节位图。
2. **为什么需要**：同一关节多个动作会相互覆盖，引发不可预测力矩。
3. **它不是什么**：不是多个 Runner 输出按最后写者覆盖。
4. **具体例子**：BipedBalance 占腿和手臂时，不得叠加直接抢这些臂的 Overlay。
5. **链路中的位置**：Registry/Worker 提供候选→RT JointMux 合成。
6. **谁拥有、谁不能做**：Bundle 定义 owns；RT 每拍复核；Worker 不改 mask。
7. **失败与兜底**：mask 交叉在预加载拒绝，运行期交叉导致保护。
8. **对应文档**：D4.3/D5.6。
9. **自测 3 问**：一个关节能同时被两个 Runner 占用吗？ 没有 owner 的关节可以保持上一拍吗？ 平衡需要挥手时应如何做？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | Primary+Overlay候选 |
| 输出 | 唯一规范关节目标 |
| 必须通过的门 | bitmask互斥/完成窗口 |

## 13. RobotDescription

1. **一句话定义**：RobotDescription 是机器人真实拓扑、方向、零点与限位的唯一规范记录。
2. **为什么需要**：训练输出是抽象关节名，设备读写按真实 ID 和方向映射。
3. **它不是什么**：不是策略模型的关节顺序，也不是一个能自动校准的算法。
4. **具体例子**：16 关节 demo 是假本体；真实 Collie 需要本体/HAL 签发 topology/calibration。
5. **链路中的位置**：HAL/Registry→Obs/Codec/Guard。
6. **谁拥有、谁不能做**：本体/HAL 签发，运控软件只验证和引用。
7. **失败与兜底**：SHA/关节顺序/方向对不上→动作不可用。
8. **对应文档**：D9.2、附录 B §1。
9. **自测 3 问**：关节方向在 Codec 改还是 HAL 改？ demo16 能否证明 Collie 是 16 自由度？ 拓扑 SHA 错时还能让站立 Runner 动吗？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 标定+拓扑 |
| 输出 | joint_name→device_id |
| 必须通过的门 | N≤64及校准签名 |

## 14. ObsSpec

1. **一句话定义**：ObsSpec 是把 SensorSnapshot 按逐维转换写入模型 tensor 的确定配方。
2. **为什么需要**：同样 16 个 float，如果顺序、滤波、历史不同，策略行为完全不同。
3. **它不是什么**：不是模型的输入维数说明一句话。
4. **具体例子**：传感器 q=0.3rad 经 CENTER_SCALE_CLIP 形成 input[0]，历史按 OLDEST_TO_NEWEST 排。
5. **链路中的位置**：Worker ObservationBuilder→InferenceBackend。
6. **谁拥有、谁不能做**：训练/运控签发逐行；Worker 运行；RT 不构造模型张量。
7. **失败与兜底**：缺必要关节/历史/timestamp/字段→候选无效。
8. **对应文档**：D5.3/D9.5、附录 B §5。
9. **自测 3 问**：history_lag=0 是哪一拍？ 全零数据为什么不等于 valid=false？ 为什么要用 Golden 检查每一维？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | Snapshot+Reference |
| 输出 | 命名tensor与history |
| 必须通过的门 | shape/unit/frame/missing_policy |

## 15. ActionSpec

1. **一句话定义**：ActionSpec 决定原始模型每一维怎样解码到规范关节模式、数值、增益。
2. **为什么需要**：模型 0.2 不是电机 q=0.2 rad；需要 sign、scale、default、mode。
3. **它不是什么**：不是安全限额表；不能用 raw_clip 代替 OutputGuard。
4. **具体例子**：a=0.2、sign=-1、scale=0.5、default=1.0 → q=0.9 rad。
5. **链路中的位置**：Worker ActionCodec→RT Guard/HAL。
6. **谁拥有、谁不能做**：训练/运控签发；Codec 执行 sign；HAL 仅执行 RobotDescription.direction。
7. **失败与兜底**：维度/模式错拒加载；非有限值候选整体失效。
8. **对应文档**：D5.5/附录 B §5。
9. **自测 3 问**：sign 与硬件 direction 能省一个吗？ 默认值在哪个坐标系？ TORQUE 模式还需要检查哪类包络？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | raw output |
| 输出 | JointTarget候选 |
| 必须通过的门 | raw_clip+sign+scale+default |

## 16. ActionEpoch / sealed ExitDecision

1. **一句话定义**：ActionEpoch 是 RT 提交动作时递增的版本，sealed decision 是旧 Runner 可退出的限时声明。
2. **为什么需要**：防旧候选在新动作接管后重新控制电机。
3. **它不是什么**：不是 Session、不是每个 5ms tick 都加一。
4. **具体例子**：q2b 首命令新 epoch=8，所有 epoch=7 的输出被 HAL/RT 拒绝。
5. **链路中的位置**：Worker 只读 epoch/产 decision→RT 提交→HAL pending/active。
6. **谁拥有、谁不能做**：RT 唯一更新 active epoch；Worker 不能主动切；HAL 校验设备接受。
7. **失败与兜底**：旧/过期决策统一 WAIT；**pre-step READY 竞态 P0 未解决**。
8. **对应文档**：D3.2/D3.5/D4.5、Review §2.1。
9. **自测 3 问**：RT 可以等待 Worker 返回 can_exit 吗？ READY 已发布后 step 挂死安全吗？ 新 epoch HAL ACK 失败能直接回旧 epoch 吗？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | snapshot_seq/Runner phase |
| 输出 | Epoch原子提交 |
| 必须通过的门 | lease/decision/fault/epoch_ready |

## 17. RobotStateSnapshot

1. **一句话定义**：Snapshot 是 RT 用多个带时间戳反馈构成的同拍不可变状态。
2. **为什么需要**：避免 IMU 更新时又读到上一拍电机状态导致观测不同步。
3. **它不是什么**：不是裸 joint_pos 数组。
4. **具体例子**：seq=200 的关节反馈和当前新 IMU 含各自 age；超过上限则该字段 invalid。
5. **链路中的位置**：HAL feedback→RT Snapshot→Worker ObsBuilder。
6. **谁拥有、谁不能做**：RT 构建，Worker 只读；上游不能伪造 valid 位。
7. **失败与兜底**：关键反馈过期/倒退/NaN→Guard/安全降级。
8. **对应文档**：D5.1/D5.2。
9. **自测 3 问**：snapshot_seq 为何必须单调？ 为什么时钟不对齐会阻断动态参考？ 反馈数值是0能直接判无效吗？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | HAL反馈和时间戳 |
| 输出 | 冻结RobotStateSnapshot |
| 必须通过的门 | age/valid/clock_quality |

## 18. JointMux

1. **一句话定义**：JointMux 是按所有权把 Primary/Overlay 合成唯一目标的模块。
2. **为什么需要**：任何同关节叠写都会使输出无明确控制者。
3. **它不是什么**：不是数值加权平均器。
4. **具体例子**：四足移动 owns 轮/腿；头部点头仅 owns 头部（且测试批准）。
5. **链路中的位置**：RT Candidate校验→JointMux→Guard。
6. **谁拥有、谁不能做**：RT 唯一合成，Registry 预校验组合表。
7. **失败与兜底**：重叠 mask/未定义关节→拒绝合成并保护。
8. **对应文档**：D4.3/D5.6。
9. **自测 3 问**：谁保证 mask 不重叠？ 主动作离开时 Overlay 先做什么？ 平衡用手臂时为何不能直接加 Overlay？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 候选+owns_mask |
| 输出 | 完整JointTargetArray |
| 必须通过的门 | 无重叠/相同epoch |

## 19. OutputGuard / ModeTransition

1. **一句话定义**：OutputGuard 检查发布包络，ModeTransition 限制控制模式及增益的变化。
2. **为什么需要**：即使模型输出 finite，也可能速度过大或 POSITION→TORQUE 突变。
3. **它不是什么**：不是训练奖励，也不是 HAL 的设备保护替代。
4. **具体例子**：变形 phase 要换 TORQUE：先 PREPARE_MODE，再按获批 ramp、ACK 后才 RAMP_UP。
5. **链路中的位置**：RT JointMux→ModeTransition→OutputGuard→HAL。
6. **谁拥有、谁不能做**：RT 负责软件限幅；HAL 确认设备模式；安全配置另签发。
7. **失败与兜底**：无 mode plan 或 ACK/实际反馈失败→保留当前已验证模式或保护。
8. **对应文档**：D5.6、附录 A §2.2。
9. **自测 3 问**：为什么控制模式不能只改 enum？ model raw clip 就足够安全吗？ HAL 不支持 TORQUE 应如何处理？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 唯一关节候选 |
| 输出 | 被Guard接受的HalCommand |
| 必须通过的门 | q/dq/tau/kp/kd rate/prepare ack |

## 20. SafetyLease / Form=UNKNOWN

1. **一句话定义**：SafetyLease 是安全核短时准许正常运动的证明；UNKNOWN 是无法证明当前支撑姿态的状态。
2. **为什么需要**：确保无安全监控就不继续发令，并防冷启动错误保持。
3. **它不是什么**：不是获签即代表硬件失控不会跌倒。
4. **具体例子**：上电 INIT+UNKNOWN：不能 Q2B/B2Q/Balance/Recovery，默认设备安全输出。
5. **链路中的位置**：SafetyKernel→RT，每 5ms验证；HAL/硬件继续独立。
6. **谁拥有、谁不能做**：SafetyKernel 签发许可，RT 检查；业务不能续租。
7. **失败与兜底**：Safety 失活 Lease 超期；硬件急停直接走设备。
8. **对应文档**：D2.4–D2.5/D7.4/D8、附录 A。
9. **自测 3 问**：上电 UNKNOWN 可直接 SAFE_HOLD 吗？ 30ms Lease 代表 30ms 急停响应吗？ 安全进程挂死后谁保护？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | health+physical state |
| 输出 | SafetyLease/INIT gate |
| 必须通过的门 | 许可时效+形态确证 |

## 21. Golden / 黑匣子 / Replay

1. **一句话定义**：Golden 是固定验收输入输出；黑匣子是故障现场逐拍事实；Replay 在软件中重算现场。
2. **为什么需要**：既证明训练部署一致，又能追查临时故障。
3. **它不是什么**：Golden 不是现场观测，黑匣子不是签发审批。
4. **具体例子**：quad_stop 同一 Obs tensor 逐维 diff；运行中急停后取前30s+后10s回放。
5. **链路中的位置**：Worker/RT 写预分配环→异步转储→测试回放。
6. **谁拥有、谁不能做**：训练和软件共同签 Golden；RT 不直接落盘。
7. **失败与兜底**：日志满不可拖 RT；容量不足需阻断完整故障窗宣称。
8. **对应文档**：D9/D10/D11、附录 B §6。
9. **自测 3 问**：Golden PASS 能证明不跌倒吗？ 128MiB 是已测可用内存吗？ 原始输出重放和重新推理回放差别是什么？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | Golden fixture/Snapshot记录 |
| 输出 | diff/trace/安全审查 |
| 必须通过的门 | hash/时钟/完整性 |

## 22. SIL / HIL / 开放边

1. **一句话定义**：SIL 测软件模型和协议分支，HIL 连接真实 HAL/驱动做故障注入，开放边是被批准的 Action 切换证据。
2. **为什么需要**：合同正确≠真实硬件保护有证据；每条危险动作边需逐一验收。
3. **它不是什么**：不是有36/36软件 PASS 就能上机。
4. **具体例子**：用 FakeHal 测 STALE_SEQ 再用真 HAL 注入同样旧包并抓 ACK/驱动动作。
5. **链路中的位置**：D11 CI→HIL→封闭真机。
6. **谁拥有、谁不能做**：测试执行、HAL/安全/本体分责签收；软件不能代替电气批准。
7. **失败与兜底**：某一 phase 无安全退路则该边保持 DISABLED。
8. **对应文档**：D11.1–D11.4、附录 C。
9. **自测 3 问**：SIL 测试证实独立硬件狗了吗？ 哪个环节需要示波器/抓包？ 只开放 quad_stand 是否意味着开放 Q2B？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 模拟输入/真实设备注入 |
| 输出 | 证明与开放记录 |
| 必须通过的门 | 条件/测试包/签名 |

## 23. switch_ready / Status

1. **一句话定义**：switch_ready 是稳定且允许新普通切换的运行状态标记。
2. **为什么需要**：上游不能用 ACTION_ACCEPTED 猜机器人已准备好下一个任务。
3. **它不是什么**：不是 action_done，也不是无故障的唯一依据。
4. **具体例子**：双足平衡 RUNNING 但姿态尚未稳定，switch_ready=false。
5. **链路中的位置**：RT/PolicyManager状态→Gateway 50Hz MotionStatus→Task。
6. **谁拥有、谁不能做**：RT 提供事实状态，Gateway 转发；Task 不能自设 ready。
7. **失败与兜底**：上游状态流逾 TTL 标 UNKNOWN，不自动启动下一步。
8. **对应文档**：D4.6、D6.1。
9. **自测 3 问**：ACTION_ACCEPTED 等于 switch_ready 吗？ Action 做完但不稳定能切吗？ 状态流断掉 Task 该怎么做？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | 稳定窗+阶段+退出判据 |
| 输出 | MotionStatus/Events |
| 必须通过的门 | 反馈/Lease/无切换 |

## 24. 黑匣子容量与时间预算

1. **一句话定义**：黑匣子记录全链现场，128 MiB 是软件初始容量建议，不是保证任何动作都能保存40s。
2. **为什么需要**：多Runner大tensor可能超出容量，必须在发布时计算带宽上限。
3. **它不是什么**：不是“128MiB无论如何够用”。
4. **具体例子**：按V1.1基准0.4395 MiB/s，40s≈17.6MiB；总112MiB可记录区，阈值2.8MiB/s。
5. **链路中的位置**：RT二进制ring→异步logger→Replay。
6. **谁拥有、谁不能做**：RT只写预分配内存；logger落盘；Release准入审核容量。
7. **失败与兜底**：超过预算不得假称故障完整可回放。
8. **对应文档**：D8.4/D10.2、附录 B §6。
9. **自测 3 问**：40s容量计算包含所有Overlay吗？ 磁盘慢可以让RT等吗？ 录入速度大于2.8MiB/s怎么标注？

| 看这条小链 | 具体内容 |
|---|---|
| 输入 | Snapshot/candidate/event |
| 输出 | mcbx按时间封存 |
| 必须通过的门 | max_bytes_per_s/CRC/索引 |

## 25. 读完后的最终检查

读者应能从 `SetBehavior` 一路指到 `HAL` 的 `accepted/reject_reason`，并说明任何一个进程死亡时下层如何处理；能用 `(ExecutionKind, BehaviorRole)` 唯一查 Runner；能指出完整 Action 包内至少四级资产；能说明 V1.1 **尚未修复** `can_exit` READY 竞态、现有 36 个测试不是 HIL；能说出“可拆模块编码，但不可直接上机”的原因。

完成度：100%（9 个核心专题 + 15 个关联概念，全部使用九项模板、表/图、Running Example）。未完成/假设：样例 SHA、模型、标定、HIL 均未签发；V1.1 P0 仅标注不静默更改。
<!-- END_V12: APPENDIX-CONCEPT -->


---

<!-- BEGIN_V12: APPENDIX-SELF-CHECK -->
# 附录 E：V1.3 频率修订自检

> 只记录 V1.3 的频率/文档一致性，不是 V1.1 架构或实机安全评分。

## 1. 已改

- 策略推理：100→50 Hz，`period_ms=20`；
- Worker：10→20 ms，预算 7.6/10→15/20 ms；
- `can_exit`：10→25 ms，`snapshot_seq` 差 2→4；
- 候选 deadline：tick+8→tick+15 ms；`max_hold` 10→25 ms；
- 黑匣子：Worker 100→50 Hz，819200→409600 B/s；
- Deck：19 页版按 50 Hz/20 ms 重画第 2/3/4/9/10 页；
- 全文 6 个 Part + 附录 D 的 100/10/7.6 已同步。

## 2. 未改

- T1 的 100 Hz、196 Hz 发布、WBC 10.5 ms 是 T1 实证，保留对照；
- `mc_safety` 100 Hz、SafetyLease 30 ms、HAL 15 ms、PD 1 kHz 不变；
- `can_exit` pre-step READY 的 P0 没有因为改频率而修复；
- 36/36 仍是 SIL/合同/Schema/文本检查，不是 HIL。

## 3. 残留与阻断

| 事项 | 状态 | 下一步 |
|---|---|---|
| `can_exit` P0 | 50 Hz 把窗口从 10 ms 放大到 20 ms | 先修 READY 发布顺序/完成序号，再开放切换 |
| 50 Hz 模型 WCET | 预算 15/20 ms 是目标 | 在目标平台测 obs+model+codec |
| ZOH 保持 | 默认保持，不插值 | HIL 验证 4:1 保持的跟踪/舒适性 |
| HAL watchdog/双足/Q2B | 未签收 | 不能上机 |

## 4. 结论

**V1.3 的频率基线可评审、可拆编码任务；P0/HIL 未闭环，不能上机。**
<!-- END_V12: APPENDIX-SELF-CHECK -->
