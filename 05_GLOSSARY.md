# 05 Glossary（术语表）

> 目的：避免同一词在不同文档里指不同东西。设计文档第一次出现术语时，应与本表一致；如需新增，先在这里定义。

| 术语 | 英文/缩写 | 定义 | 不要混淆 |
|---|---|---|---|
| 运控 | MC, Motion Control | 把“运动意图”变成“关节/轮目标”的实时服务；含策略执行、切换、观测/动作适配、安全出口 | 不等于导航（规划路径）、不等于感知 |
| Runner | Runner / Policy Runner | 可独立加载、按固定节拍输出关节目标的执行单元；RL/ONNX、经典控制、播放器、过渡、恢复、叠加都是 Runner | 不等于“一个 ONNX 文件”；一个 Runner 可能含模型 + 前后处理 + 守卫 |
| Runner 框架 | Runner Framework | Runner 的契约、生命周期、管理器、切换、数据链路、配置、安全的整体 | 不等于训练框架 |
| `IRunner` | Runner Interface | Collie 建议的策略接口：`load/enter/can_exit/step/exit/status` | 不是 T1 的 C++ ABI |
| `RunnerBase` | T1 Runner Base | T1 二进制中确认存在的基类，含 12 个生命周期钩子 | 不能假定其完整字段/语义 |
| `RunnerManifest` | Manifest | 一个 Runner 的静态资产描述：模型/轨迹、tensor IO、obs/action 规格、增益、所有权、周期、守卫 | 不等于 `policy.onnx` |
| `RobotDescription` | Robot Profile | 本体静态事实：关节名/顺序/零点/方向/限位/传动/外参/设备版本 | 不在策略配置里重复定义 |
| `ActionBundle` | Bundle | 一个 Action 的执行组合：`primary` + `overlays` + `owns_mask` | 不等于“一个 Action = 一个类/线程” |
| `StepInput` | — | 每拍输入：`RobotStateSnapshot` + `MotionReference` + `TransitionContext` | 不是静态配置 |
| `RunnerOutput` | — | 每拍输出：`JointTargetArray` + `owns` + `phase` + `done/exit_ready` + `fault` | 不是最终电机命令（还要过 JointMux/Guard） |
| PolicyManager | — | 软件侧管理器：注册/预加载、动作图校验、请求仲裁、切换、阶段状态 | 不是策略本身 |
| ActionGraph / TransitionGraph | — | 合法 Action 与切换边的图；含守卫、超时、回退 | 不是 ROS 计算图 |
| `ActionRequest` | — | 离散请求：`request_id/source/action_id/issued_at/deadline/params/preempt_mode` | 不与连续速度混合 |
| `BodyVelocityRef` | VelocityRef | 连续机身速度参考：`source/seq/stamp/ttl/frame/vx/vy/wz`（可选姿态/高度） | 不是目标位置/路径 |
| `OverlayRequest` | — | 局部动作请求：头/臂/手势，受关节所有权约束 | 不是主 Runner |
| `SafetyEvent` | — | 异步安全事件：急停/跌倒/低电/故障，带 `kind/severity/stamp/latched` | 不走普通动作队列 |
| `JointTargetArray` | — | 逐关节目标：`name/mode/q/dq/tau/kp/kd/enabled` | 不是 `JointState`（反馈） |
| `RobotStateSnapshot` | — | 同一拍不可变反馈：关节/IMU/接触/有效性/时间戳 | 不是原始消息队列 |
| `MotionReference` | — | 已完成来源仲裁、坐标变换、时效检查的参考 | 不是所有速度源的集合 |
| `ObsSpec` | Observation Spec | 逐维观测配方：索引/块/源/单位/坐标/偏移/尺度/裁剪/滤波/历史/缺失策略 | 不是 `obs_nums` 一个数字 |
| `ActionSpec` | — | 逐关节动作配方：模式/scale/default/gain/limit/activation | 不是模型原始输出 |
| `ObservationBuilder` | — | 把 snapshot + reference + spec 组装为 tensor | 不做推理 |
| `InferenceBackend` | — | 模型加载/校验/执行后端（ONNX Runtime 等） | 不做前后处理 |
| `ActionCodec` | — | 把模型原始输出解码为关节目标（裁剪/scale/default/gain） | 不做安全限幅 |
| `JointOwnershipMux` / `JointMux` | — | 按 `owns_mask` 合成主 Runner 与 overlay | 不允许“最后写者赢” |
| `OutputGuard` | — | 每拍最终硬限幅/失效替代/唯一关节出口 | 不是安全策略本身，但必须独立于推理 |
| `Lease` | Safety Lease | 安全内核发给控制环的短时“可输出”凭证（如 50 ms） | 不替代硬件急停 |
| `switch_ready` | — | 当前策略稳定且可接受下一动作 | 不等于“动作完成” |
| `epoch` | Action Epoch | 一次接管/动作实例的代数，用于拒绝过期命令 | 不是时间戳 |
| `Q2B` / `B2Q` | Quad-to-Biped / Biped-to-Quad | 四足↔双足过渡动作，独立过渡 Runner | 不是两份行走权重插值 |
| `WBC` | Whole-Body Control | 全身控制；T1 双足用 WBC 策略 | 不是通用“平衡”同义词 |
| `HAL` | Hardware Abstraction Layer | 设备抽象层；关节命令→电机，反馈→MC | 不是 MC 内部模块 |
| `HDS` | Health/Diagnosis System | 健康诊断系统；MC 向其报诊断 | 不是安全内核 |
| `SM` | System Mode | 系统模式机；整机生命周期/功能组 | 不是任务状态机 |
| `TTL` | Time To Live | 速度/请求有效期；过期归零/拒绝 | 不是超时重试 |
| `WCET` | Worst-Case Execution Time | 最坏执行时间；实时预算的核心指标 | 不是平均耗时 |
| `Golden Fixture` | — | 一组固定输入/期望输出，用于逐维回放验证 | 不是“看起来差不多”的对比 |
| `HIL` | Hardware-in-the-Loop | 硬件在环测试 | 不是纯仿真 |
| `SIL` | Software-in-the-Loop | 软件在环测试 | 不是真机 |
