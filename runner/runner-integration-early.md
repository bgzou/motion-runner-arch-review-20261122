# Collie 运控策略 / Runner 架构对接说明（评审稿）

**版本**：2026-11-18　**交付对象**：运控算法、软件平台、导航/感知、本体与测试团队。

**接口主文档**：[运控 Runner 接口与数据链路设计](./runner-interface-and-dataflow.md)逐项列出 T1 上下游、Collie 领域接口、每拍前后处理、配置 schema、Runner 类与软件模块分工。本文保留场景映射、策略优先级和切换图谱。

## 0. 一页结论

1. 运控团队交付的是**策略契约、策略资产、观测/动作适配、切换约束和安全判据**；软件团队实现 Runner/Policy Manager、任务编排、进程/线程、RPC/话题、持久化与监控。策略的物理接管、输出限幅和异常降级必须由运控与软件共同签收，不能只在上层任务里实现。
2. 对上层明确三条运动接口：**离散 Action/模式请求**（站、趴、四足/双足、恢复等）、**连续机身速度/姿态参考**（领路、跟随、运镜、遥控）和**受关节所有权约束的局部动作请求**（头/臂手势）。相机快门、VIP 识别、NLU、导航路径、云台变焦不是腿轮策略。
3. P0 基座建议先有 `SafeHold/Damping`、`QuadStand`、`QuadWheelDrive`、`QuadStop`、`Q2B`、`BipedBalance/WBC`、`B2Q` 和 `Recovery`。四足→双足、双足→四足是**独立闭环过渡策略**，不是在两份行走权重之间插值。表演与头/臂手势须声明关节所有权及与平衡策略的组合限制。
4. T1 的真机配置可参考运行概念，但**不要复制其 Action 数字、关节映射或模型尺度**。本目录 T1 `qd1_t2d0` 是 14 关节；`roboto_origin-main` 默认 RPO 配置是 23 关节。T1 样例 ONNX 为当前观测和 10 帧历史的**双输入**；现有 roboparty 推理节点源码明确只接受单输入模型。
5. 本文中的 **[实证]** 指本地原始配置/接口/源码或 ONNX 图直接可读；**[建议]** 指 Collie 的待实现契约；**[待定]** 指需要本体、训练或产品验收确认。附带《需求场景.txt》是需求证据，不将其中的实现分工、阈值草案视为已批准的软件接口。

配套图：[策略链路图](../evidence/diagrams/strategy-chain.drawio)、[策略切换图](../evidence/diagrams/strategy-switching.drawio)。

## 1. 证据与适用范围

| 证据 | 本文使用方式 | 限制 |
|---|---|---|
| [T1 Action 配置](../evidence/configs/action_setting.yaml)、[切换规则](../evidence/configs/action_ruler.yaml)、[模型清单](../evidence/model-list/action-execution-runner.md) | 核对 Action→执行组→runner、周期和合法边 | 真机部署态，不是源代码；清单属于二次整理，以 YAML 为准 |
| [T1 四足行走配置](../evidence/configs/rl_quad_walk.yaml)、[Q2B 配置](../evidence/configs/rl_quad_to_bi_run.yaml)、[双足 WBC 配置](../evidence/configs/rl_bi_wbc_run.yaml) | 观测索引、关节顺序、默认位、尺度、增益、模型路径 | 只适用于对应 T1 资产，不能作为 Collie 标定值 |
| [T1 IDL](../evidence/interfaces/MC_INTERFACE_CATALOG.md)、[真机资料说明](../reference/real-machine-evidence-notes.md) | 对外消息语义、任务/状态字段 | 不等于 `libmc_common_runner.so` 的 C++ ABI |
| [roboparty 推理源码](../reference/NOT_INCLUDED.md)、[类定义](../reference/NOT_INCLUDED.md)、[观测实现](../reference/NOT_INCLUDED.md)、[默认配置](../reference/NOT_INCLUDED.md) | 评估代码复用点与缺口 | RPO 本体/训练契约与 T1 不同 |
| [17 UC 与展馆 3 IR](../requirements/requirements-scenarios.txt) | 场景覆盖、P0/P1/P2、未决验收 | 从用户所附桌面文件复制的参考副本；场景内含待澄清项，参数须冻结后入配置 |

**二进制核查更新**：Z 盘现可访问，已直接检查 `Z:\primebot-t1\robot_rk\software\mc\lib\libmc_common_runner.so` 与相邻 Manager/具体 Runner 库。导出符号证实 T1 的 `mc::runner::RunnerBase`、`Configure/PreInit/Init/Run/ExitCheck/EnterCheck/PreRunOnce/AfterExit` 等钩子，以及具体 Runner 的 `CreateRunner/DestroyRunner` 工厂入口。完整证据和限制见[接口主文档 §1.2](./runner-interface-and-dataflow.md#12-libmc_common_runnerso-能说明到哪一步)。本文 `IRunner` 仍是**Collie 建议的新接口**，并非与 T1 ABI 兼容的头文件定义。

## 2. 边界：谁把什么交给谁

| 方向 | 接口/数据 | 运控团队负责 | 软件/其他团队负责 |
|---|---|---|---|
| 任务/导航 → Manager | `ActionRequest`、`BodyVelocityRef`、`PostureRef`、可选上肢/头部参考 | 支持矩阵、速度包络、可接管条件、输入时效 | 请求来源仲裁、任务生命周期、导航/跟随/运镜产生速度、业务超时 |
| 设备/状态估计 → Runner | `RobotState`：14 关节反馈、IMU、接触/支撑、时间戳、故障标志 | 关节及坐标定义、滤波与有效性要求、观测配方 | 驱动采集、时间同步、状态估计、缓存和发布 |
| Runner → 输出适配 → 设备 | `JointTarget[14]`（逐关节控制模式、位置/速度/力矩前馈、kp/kd） | 模型推理、后处理、关节所有权、限位/切换包络 | 唯一电机命令出口、设备协议/CAN 映射、低层限流与急停 |
| Manager → 上层 | `MotionStatus`：当前/目标 Action、phase、form、`switch_ready`、完成/故障原因 | 各策略结束/失败/接管判据 | 状态机/RPC/话题、可观测性、任务回调 |
| 安全旁路 | E-stop、姿态异常、失联、过温/电压、电机故障 | 安全动作与恢复条件、模型失效的安全姿态 | 硬件急停和软件执行链、事件汇聚、故障锁存/复位授权 |

T1 可参考的接口语义：[`SetMcAction.srv`](../evidence/interfaces/MC_INTERFACE_CATALOG.md) 的请求含 `source` 与 `McActionCommand`；[`McLocomotionVelocity.msg`](../evidence/interfaces/MC_INTERFACE_CATALOG.md) 含速度源、前/侧/偏航/俯仰速度和 level；[`McCommonState.msg`](../evidence/interfaces/MC_INTERFACE_CATALOG.md) 发布输入源、Action、运行模型、形态、姿态、跌倒等；[`McActionInfo.msg`](../evidence/interfaces/MC_INTERFACE_CATALOG.md) 将当前 Action、状态、`switch_ready` 分开。**请求被接收 ≠ 切换完成 ≠ 机体已稳定**，三者要有独立事件。

## 3. 策略内部数据链路与契约

### 3.1 每拍链路

`源数据采样 → 时间戳/新鲜度检查 → 单位/坐标/关节重排 → 滤波/状态估计 → 命令仲裁与速度限幅 → 按策略 ObsSpec 组装当前帧 → 缩放/裁剪 → 历史帧堆叠 → 模型或经典控制 → 输出裁剪/缩放/默认位 → 关节控制模式/增益装配 → 所有权合成 → 切换整形 → 位置/速度/力矩及变化率限制 → 安全复核 → 设备出口`。

**前处理是策略契约的一部分**：T1 `quad_walk.yaml` 定义 `obs_nums=57`、`action_nums=14`、`frame_stack=10`、`obs_index`、`seq`、`action_seq`、`obs_scales`、`command_scales`；`quad_to_bi_run.yaml` 同样是 14 关节但 `obs_nums=51`。这些不同尺寸说明不能用一个固定观测向量假装所有策略通用。实际读取本地 ONNX 图：`t2_quad_walk_0902.onnx` 输入 `observations[1,57]`、`observation_history[1,570]`，输出 `action[1,14]` 及另一 4 维辅助输出；`wbcterrain2026092602.onnx` 为 49/490→14；`t2.2_quad2bi_norm_0708.onnx` 为 51/510→14。辅助输出的语义未在配置中证实，不能当作控制命令。

**后处理是执行契约的一部分**：T1 配置中 `action_scale`、`default_dof_pos`、`kps/kds`、`activation`、轮减速比与关节次序均按策略定义。输出的 14 个浮点数不是可以直接下发的 14 个电机位置；轮维可能采用速度语义，应逐关节声明 `POSITION/VELOCITY/TORQUE`，再由唯一设备适配层编码。限位、限速、限加速度、力矩包络和失效降级应在策略之后再做独立复核。

### 3.2 建议的数据结构（逻辑 IDL，不规定 ROS 还是进程内 C++）

```cpp
struct MotionRequest {
  string request_id, source, action_id; uint64_t stamp_ns, ttl_ns;
  int priority; map<string, float> parameters;
};
struct BodyVelocityRef {
  string source; uint64_t stamp_ns, ttl_ns, sequence;
  float vx_mps, vy_mps, yaw_radps, pitch_radps; // 机身坐标系
};
struct RobotState {
  uint64_t stamp_ns; JointFeedback joints[14]; ImuState imu;
  ContactState contact; Form form; FaultBits faults; bool valid;
};
struct JointTarget {
  ControlMode mode; float q_rad, dq_radps, tau_nm, kp, kd;
  bool enabled;
};
struct RunnerOutput {
  JointTarget joints[14]; uint32_t owns_mask;
  Phase phase; bool done, exit_ready; FaultCode fault;
};
struct MotionStatus {
  string current_action, target_action, request_id, velocity_source;
  Form form; Phase phase; bool switch_ready, stable, moving;
  FaultCode fault; uint64_t stamp_ns;
};
```

所有消息需冻结**坐标系、单位、关节顺序、时间基准、有效期和序号**；不允许把无时间戳的旧 `/cmd_vel` 长期保持成非零速度。`source` 表示仲裁身份，不表示业务场景；导航、跟随、拍摄轨迹可以共用四足行走 runner。

### 3.3 建议的 Runner 类层次

```cpp
class IRunner {
 public:
  virtual bool load(const RunnerManifest&, const RobotDescription&) = 0;
  virtual bool enter(const RobotState&, const EnterContext&) = 0;
  virtual ExitDecision can_exit(const RobotState&, ExitContext&) = 0; // READY/WAIT/REFUSE
  virtual RunnerOutput step(const RobotState&, const MotionReference&) = 0;
  virtual void exit(ExitReason) = 0;
  virtual RunnerStatus status() const = 0;
  virtual ~IRunner() = default;
};
```

建议实现为少数**执行机制类**加不同 manifest，而非每个 ONNX 文件写一个 C++ 派生类：`WheelDriveRunner`（四轮滑行）、`OnnxPolicyRunner`（持续运动/平衡）、`TransitionPolicyRunner`（Q2B/B2Q 等一次性）、`RecoveryRunner`、`ClassicalPoseRunner`（站、趴、坐、阻尼）、`MotionPlaybackRunner`（经验证的轨迹/表演）、`OverlayRunner`（头/臂手势，需所有权约束）。每个 Runner 是一个配置实例；一个 Action 可由主 Runner 和局部 Overlay 组成 `ActionBundle`。不同模型可共用类，但观测配方、输出语义和退出判据不可共用默认值。`SafetySupervisor` 常驻并独立于当前 runner，它可以强制抢占。

`RunnerManifest` 至少包含：`action_id`、`kind`、`asset/hash`、机型/关节拓扑版本、`obs_schema`（顺序/尺度/历史/缺失策略）、`action_schema`、控制周期与推理时限、`owns_mask`、控制模式/增益、进入/退出守卫、完成判据、允许来源/目的边、故障去向。加载时核对 ONNX 输入输出**名称、个数、shape、dtype**及 hash；所有动态分配和权重加载在接管前完成，实时 `step()` 不做文件 I/O。

### 3.4 管理器最小职责与接管协议

软件团队的 `PolicyManager/RunnerManager` 名字不限，但至少：注册和加载策略实例、校验 manifest、仲裁离散请求/速度源、执行显式转换边、保存当前与目标/请求 ID、锁定单一电机输出、发布阶段状态、超时回退、追踪每拍耗时。常驻安全旁路在 Manager 内可直接转入阻尼/安全驻留；上层任务状态机不能阻断此路径。

正常切换建议 `REQUESTED → PREPARING → WAIT_EXIT → ENTERING → TRANSITIONING → STABILIZING → RUNNING`；任一步失败进入 `FAULT/SAFE`。旧策略 `can_exit()` 仅表示物理上可交出（速度近零、支撑可靠、最短执行步数等），新策略 `enter()` 验证初态与资产；正式接管是原子步骤。**形态转换本身是一个 runner**，其完成要用姿态/接触/关节误差和稳定保持时间判定；不可只按播放时间或 `form` 字段判定。策略输出混合仅用于经验证的同控制模式/同关节语义边；`Q2B/B2Q` 不做通用 `q_des` 线性混合。对外 `switch_ready` 只在稳定且可接受下一动作时为真。

## 4. 首批策略清单与 Action 映射

| 优先级 | Collie 能力 / 建议 Runner | T1 对照 Action（仅参考） | 触发与出口 | 备注 |
|---|---|---|---|---|
| P0 | 安全驻留/阻尼 `SafeHold`、被动 `Passive` | `DAMPING_DEFAULT`、`PASSIVE_DEFAULT` | 任意态异常直达；人工复位+重新验证 | 不是 RL；急停硬件链另行保证 |
| P0 | 四足站立/起立/趴下 `ClassicalPoseRunner` | `QUADRUPED_READY_STAND_DEFAULT`、`QUADRUPED_STAND_DEFAULT`、`QUADRUPED_GET_DOWN_DEFAULT` | 待机、迎宾、退出任务 | 四足低姿态不是“零速行走” |
| P0 | 四轮滑行 `QuadWheelDrive` | 参考 T1 `QUADRUPED_LOCOMOTION_DEFAULT` 的 Runner 组织方式 | 领路、跟随、巡游、运镜机位 | Collie 轮式四足策略/控制律由运控提供；业务差异主要在速度参考 |
| P0 | 减速/支撑稳定 `QuadStop` | 参考 T1 `QUADRUPED_LOCOMOTION_STEP` 的切换门控 | 四轮滑行→变形/表演前 | 可用受验证的停止过渡实现，但不能省略稳定门控 |
| P0 | 四足→双足 `Q2B` | `QUADRUPED_TO_BIPED` | 站立讲解/合影/平视交互 | 独立过渡 runner；初态、目标高度待定 |
| P0 | 双足直立平衡 `BipedBalance` | `BIPED_LOCOMOTION_WBC` | 讲解、合影保持、手势叠加 | 静止也需闭环平衡；后轮接触/滑移判据待标定 |
| P0 | 双足→四足 `B2Q` | `BIPED_TO_QUADRUPED` | 讲解/合影结束、恢复四轮移动 | 独立过渡 runner |
| P0 | 四足/双足恢复 `RecoveryRunner` | `QUADRUPED_RECOVERY`、`BIPED_RECOVERY` | 跌倒后仅在场地清空且人工/安全授权 | 展馆拥挤时默认阻尼等待，不自主弹起 |
| P0 条件项 | 低幅迎宾/讲解手势 `OverlayRunner` | `BIPED_CUSTOM_UPPER`、`animation_player` 等 | 站稳后与平衡策略组合 | 若 Collie 无独立头/臂自由度，则改为语音/灯效；关节所有权先定 |
| P1 | 低速复杂地形 `QuadTerrain`、窄道 | 参考 T1 `QUADRUPED_LOCOMOTION_TERRAIN` 的策略切换组织 | 门槛、坡道、院子、户外 | 场景自动识别/切换证据不足；先显式请求和保护 |
| P1 | 载物配置 `LoadedQuadWheelDrive` 或参数化 `QuadWheelDrive` | T1 无可直接映射的 5 kg 保证 | UC-10 平层/门槛；IR-B 取物 | 载荷、质心、制动距离须重新训练/实测 |
| P1 | 室外/人群限速配置 | 复用四足走路 Action | UC-03/06/12/15 等 | 人群检测/限速判定来自感知/规划；运控执行硬上限 |
| P2 | 楼梯、载物爬楼、拖拽 | T1 `TERRAIN` 不能推出安全载物爬楼 | UC-01、UC-10 变体 | 独立样机验证与地形/负载策略；不写入首发承诺 |
| P2 | 特技/复杂表演 | T1 `FRONTFLIP`、`DANCE` 等 | UC-14 可选 | 展馆/老人儿童附近禁用高风险特技 |

**策略数 ≠ 场景数**：17 个 UC 和展馆 3 IR 中多数平层移动行为复用 `QuadWheelDrive`；导航、跟随、避障、轨迹跟踪负责输出不同速度和停止条件。`BipedBalance` 可支持站立对话与静态合影；若需要双足移动、牵手移动，应另立 `BipedLoco/HandHeld` 需求和验收，不把静态平衡暗称可行走。

## 5. 场景覆盖：业务调用到运控动作

| 场景 | 运动序列与归属 | 首发边界 |
|---|---|---|
| UC-13 唤醒认主、UC-11 居家信息交互 | 待机 `QuadStand`；必要时 `Q2B→BipedBalance→B2Q`；人脸/声纹/权签由感知/大脑完成 | P0；VIP 识别不要求运控增加新 RL |
| UC-04 访客接待、UC-14 变形/手牵/表演 | `QuadStand→QuadWheelDrive→QuadStop→Q2B→BipedBalance`；返回 `B2Q→QuadWheelDrive`；手牵/表演走独立受限能力 | P0；手牵**移动**与动态表演需单列能力确认 |
| UC-07 合影、UC-08 跟拍、UC-09 运镜 | 移动机位/跟拍 `QuadWheelDrive`，静态平视合影 `Q2B→BipedBalance`；云台/相机并行任务 | P0；跟拍优先 Q；直立态不默认移动，变焦归相机 |
| UC-15 跟随、UC-16 领路、UC-17 信标跟随 | `QuadWheelDrive` 消费导航/跟随速度；遮挡、信标丢失时零速并驻停 | P0；重识别/路径规划不是 Runner |
| UC-10 门口收发、UC-03 陪同外出、UC-06 夜巡、UC-12 看家 | `QuadWheelDrive`；门槛/坡道需 `QuadTerrain`；夜间/雨天/人群限速由工况包约束 | P1；载物与地形均需验证 |
| UC-01 载物爬楼、UC-02/05 看护 | 前者 `LoadedTerrain/Stair` 待研发；后者主要复用 `QuadWheelDrive/Stand` 并由感知发危险区/跌倒事件 | P2；不把看护识别当运控策略 |
| 展馆 IR-A 迎宾→领路→直立讲解 | `QuadStand→QuadWheelDrive(约 1m 停驻/转向)→QuadWheelDrive(导航速度)→QuadStop→Q2B→BipedBalance(+手势)` | 单机；VIP/语音/NLU/路线/30 cm 避障由上游提供，运控做速度包络、接管与稳定 |
| 展馆 IR-B 问询→取物→寻人→送达 | `B2Q→QuadWheelDrive` 往返，载物用已验证参数/策略；到人前停止 | 双通道定位/寻人和人装人取归上游；载荷/质心验收未定 |
| 展馆 IR-C 命令触发合影或跟拍 | 合影 `QuadWheelDrive` 到位→`Q2B→BipedBalance`→`B2Q`；跟拍保持四足 `QuadWheelDrive` | 云台/手机/快门/成片不占腿轮 Runner；构图速度来自上游 |

## 6. 策略切换图谱（建议冻结为配置）

| 从 → 到 | 进入守卫 | 完成/失败 |
|---|---|---|
| `SafeHold → QuadReady → QuadStand` | 急停已复位、反馈新鲜、关节/IMU 有效、支撑可确认 | 位姿误差和稳定保持达标；否则保持安全态 |
| `QuadStand ↔ QuadWheelDrive` | 支撑可靠、速度命令有效；反向需速度衰减到阈值 | 轮速/机身速度稳定后 `switch_ready=true` |
| `QuadWheelDrive → QuadStop → Q2B` | 零速、支撑稳定、周围安全距离、地面平整、载荷许可 | `Q2B` 监测姿态/接触/滑移/超时；失败按已验证回退或阻尼 |
| `Q2B → BipedBalance` | 转换完成且后轮支撑有效 | 保持稳定窗口完成后才通知业务“可讲解/拍照” |
| `BipedBalance → B2Q → QuadStand/QuadWheelDrive` | 手势叠加已退出、速度零、前方空间清空 | 回到四轮支撑后才放行移动 |
| `QuadWheelDrive → QuadTerrain → QuadWheelDrive` | 地形请求明确，训练域/传感器/载荷满足 | 地形结束且稳定后回平地；不能仅凭速度大小自动推断 |
| `任意 → SafeHold/Damping` | 安全事件抢占 | 锁存原因；禁止自动回原动作 |
| `SafeHold → Recovery → QuadStand/BipedBalance` | 倒地类型已判定、场地无人与障碍、人工/产品授权 | 恢复失败回阻尼，次数受限 |

T1 的 [切换规则](../evidence/configs/action_ruler.yaml) 中存在 `QUADRUPED_LOCOMOTION_DEFAULT→QUADRUPED_TO_BIPED→BIPED_LOCOMOTION_WBC` 和 `BIPED_LOCOMOTION_WBC→BIPED_TO_QUADRUPED→QUADRUPED_STAND_DEFAULT/QUADRUPED_LOCOMOTION_DEFAULT`；`QUADRUPED_LOCOMOTION_STEP` 是多个特殊动作前的稳定节点。Collie 只采用这类**物理交接逻辑**，边是否开放以新本体验证为准。常规切换不可越过未配置边；紧急动作独立直达。

## 7. 以 roboto_origin-main 承接的具体改动点

| 现有位置/事实 | 建议改造 | 交付归属 |
|---|---|---|
| [`InferenceNode` 模型加载](../reference/NOT_INCLUDED.md)：`setup_model` 抛出 `Only single-input ONNX models are supported` | 支持按 manifest 验证**多输入、多输出**模型；分别分配当前帧/历史帧 tensor；忽略未声明的辅助输出 | 软件实现；运控提供模型 schema/测试向量 |
| [`PolicyRuntime`](../reference/NOT_INCLUDED.md)：已有模型、obs layout、history、motion loader | 抽出 `IRunner`/manifest 实例；将观测、推理、后处理与场景切换解耦；经典/过渡 runner 可共存 | 软件实现；运控定义接口/配方 |
| [`obs_manager.cpp`](../reference/NOT_INCLUDED.md)：已有 IMU、重力、速度、关节、上一动作、感知、latent 观测源 | 加入数据新鲜度、单位/坐标/14 关节映射、当前帧与历史输入分别装配；逐策略 obs schema 校验 | 联合 |
| [`inference_node.cpp`](../reference/NOT_INCLUDED.md)：推理后 `output × action_scale + default_angle`，控制线程平滑下发 | 扩成逐关节控制模式、kp/kd/力矩、关节所有权、限幅、切换整形和安全复核；仅一个执行出口 | 联合 |
| [`default.yaml`](../reference/NOT_INCLUDED.md)：`joint_num: 23`、单模型 `policy.onnx`、`dt:0.004`、`decimation:5` | 新建 **Collie 本体配置与模型清单**；不要覆盖 RPO 默认配置；先用无电机仿真回放验证 | 运控提供标定；软件接入 |
| [`ros_interface.cpp`](../reference/NOT_INCLUDED.md)：`/cmd_vel`、手柄、模式切换已有入口 | 换成带 `source/ttl/seq` 的速度仲裁及 Action 请求接口；手柄抢占、失联归零、状态反馈 | 软件实现；运控确认优先级/限速 |

**注意**：当前 roboparty `control()` 线程按 `dt` 周期下发，`inference()` 线程按 `dt×decimation` 推理；T1 runner 配置常见 10 ms，仅是参考。最终频率须根据 Collie 电机/总线、推理耗时、训练采样率联合冻结。`rsl_rl/runners` 是训练 runner，不是机器人实时 Runner。

## 8. 可直接给软件团队的验收契约

1. **加载期**：关节拓扑、模型 hash、输入输出名称/shape/dtype、观测配方、输出模式不匹配时拒绝启动；旧策略继续安全运行或进入安全态。
2. **回放期**：同一段时间戳反馈/速度/参考，经新旧离线实现对比，验证观测向量逐维一致、历史帧顺序、首次进入清零规则、14 维输出反标定一致。每种模型至少提供一组 golden input/output。
3. **切换期**：非法边明确拒绝；正常边记录每阶段时间和守卫；任务收到“已接收、转换中、已稳定、失败”四种不同结果；变形期间不接受行走速度接管。
4. **异常期**：速度 TTL 到期、IMU/关节反馈过期、ONNX 异常、推理超时、输出 NaN/Inf、关节越界、跌倒、急停，都必须触发可追溯的安全输出；急停不能依赖 ONNX 或任务引擎存活。
5. **场景期**：展馆 IR-A 至少跑通迎宾/领路/直立讲解/回四足；IR-C 验证静态合影与四足跟拍两条路径；UC-15/16/17 验证同一四足 runner 承接三种速度来源。载物、楼梯、拥挤与手牵移动各设独立验证门槛。

验收记录字段：`request_id`、来源、当前/目标 Action、转换阶段、`switch_ready`、形态、输入新鲜度、速度源/TTL、模型版本/hash、推理耗时、输出限幅原因、安全事件及最终结果。可用离线回放+仿真完成接口验收；真机开放边必须再做本体安全试验。

## 9. 评审时必须拍板的最少问题

| 问题 | 当前依据/影响 | 建议决策责任人 |
|---|---|---|
| Collie 关节拓扑、轮/腿/头臂数，双足直立究竟是静态锁止还是动态后轮平衡 | 需求同时使用“四足轮式”“静态稳定”“后双轮自平衡”，表述冲突；决定控制模式和安全守卫 | 本体+运控 |
| Q2B/B2Q、双足保持、5 kg 载物、门槛/楼梯分别有哪些**Collie 自研权重/训练域/实测** | T1 资产不能直接迁移到不同机构 | 运控+训练 |
| 头/前肢手势与平衡策略是否争用关节 | 决定 `owns_mask`、叠加接口或重训练 | 本体+运控 |
| 展馆拥挤限速、30 cm 避障、被撞 5 s 恢复是否作为安全要求 | 需求里有草案但检测与自动恢复条件不完整；不能直接编码成常量 | 产品+安全+导航 |
| 断网、目标丢失、普通观众并发、VIP 识别失败、跟丢 15 s 后回哪里 | 属任务/感知策略；运控需要收到明确 `STOP/HOLD/RETURN` 意图 | 产品+平台+导航 |
| 直立高度、稳定时间、允许负载、目标速度、切换时限、跌倒后自动恢复许可 | 决定 Q2B/B2Q/Balance 的验收门槛 | 产品+本体+运控 |

上述未决项不妨碍软件团队先按契约实现 Manager、回放测试和安全出口；对应实体 Action 的开放必须等本体与策略验证完成。
