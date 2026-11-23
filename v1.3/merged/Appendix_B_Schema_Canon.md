# SCHEMA_CANON.md — Collie MC V1.1 唯一协议和配置事实源

> 状态：【设计冻结用于编码，非 Collie 物理参数验证】；版本：`mc-schema/1.1.0`。适用于 V1.0 的 D2/D3/D4/D5/D6/D8/D9/D10/D11 的 V1.1 定点替换。与本文件冲突的 V1.0 字段、表格和示例一律失效。
>
> 数据源顺序：**`proto/collie_mc_v11.proto`**（RPC、事件、状态、HAL IPC 的领域字段）→ **`schemas/*.schema.json`**（YAML/CSV 配置）→ **`safety_limits.yaml`**（每机型签发的物理界限）→ 生成的 C++/ROS2 适配代码与文档字段表。**不得以文档表格反向定义新字段。**本包 `examples` 均为不可部署的接口示例，不含签发安全参数。

## 1. 时钟、单位与错误的统一规则

- `*_ns` 使用同一设备内单调纳秒时钟；RPC 的 `issued_utc_ns` 仅用于审计，不参与控制截止判定。跨计算单元时必须经已验证的时钟映射；同步质量不足则不允许跨板时效比较。
- 只有外部 `RequestHeader.timeout_ms` 是**RPC 相对时间**，Gateway 于验签/接收时将其换为 `ScheduledAction.deadline_ns = receive_mono_ns + timeout_ms × 1,000,000`，并做溢出和允许范围校验；**`deadline_ns` 是内部绝对截止时刻**。对过渡相位使用配置字段 `max_duration_ms`（进入该相位时转为绝对截止），不得与请求超时混淆。
- `ttl_ms` 用于来自控制源的输入有效时间或外部 ControlLease 的续租区间，入本地 RT 缓冲后统一转为 `expires_mono_ns`。
- 姿态 `Form=UNKNOWN`、字段 `valid=false`、年龄未知（`UINT32_MAX`）、不支持的控制模式均按**不准许正常运动**处理。没有隐式默认零、默认支撑或默认握持。
- 正常消息出错返回精确 `reject_reason` 或标准 `Errc`；安全事件始终异步单调锁存，任何 RPC 不能绕过硬件急停。`CRC32C` 只检查传输损坏，**不是身份认证**。
- 单位：`q_rad` (rad)、`dq_radps` (rad/s)、`tau_nm` (N·m)、`vx_mps`/`vy_mps` (m/s)、`wz_radps` (rad/s)；若存在直线关节，使用 `q_m`/`dq_mps`/`force_n` 的**明确类型 variant**，绝不在同一字段混入不同单位。`kp` 旋转关节 N·m/rad；`kd` N·m·s/rad。示例 16 关节全部为转动关节，**不代表 Collie 的结构**。

## 2. Canonical 消息表（与 proto 同步）

| 对象 | Canonical 字段（类型；单位/时效） | 非法/过期的确定处理 |
|---|---|---|
| `RequestHeader` | `request_id` UUID、`session_id` UUID、`source_id` uint32、`issued_utc_ns` uint64（审计）、`timeout_ms` uint32（相对 ms）、`payload_digest` bytes32 | 0/溢出/超过网关上限拒绝 `INVALID_ARGUMENT`；Gateway 接收一次计算 `deadline_ns`，重复请求不延时 |
| `ActionRequest` | `header`、`action_id` string、`validated_params` 经过固定 schema 校验的字节载荷、`preempt_mode` enum、`control_lease_id` UUID | 授权/lease/幂等/边校验失败 `REJECTED`；超时 `DEADLINE_EXCEEDED`；受理不代表动作完成 |
| `BodyVelocityRef` | `session_id` UUID、`control_lease_id` UUID、`source_id` uint32、`seq` uint64、`stamp_robot_ns` uint64（robot monotonic）、`ttl_ms` uint32、`frame_id` string、`vx_mps`/`vy_mps` float、`wz_radps` float | source/lease/seq/TTL/frame 错误丢弃并记录原因；有效源过期按获批制动包络归零，不能永久续发上次速度 |
| `MotionStatus` | `boot_id,request_id,execution_id,session_id` UUID；`seq,action_epoch,stamp_robot_ns` uint64；`source_id` uint32；`current_action,target_action` string；`phase,transition_phase,form` enum；`stable,switch_ready,action_done` bool；`active_primary` string、`active_overlays` string[]；`effective_velocity{vx_mps,vy_mps,wz_radps}`；`effective_velocity_source_id` uint32；`effective_velocity_age_ms` uint32；`safety_state` enum；`latched_fault_code` uint32；`feedback_age_max_ms,inference_age_ms` uint32；`release_id` string；`manifest_sha256` bytes32；`control_lease_id` UUID；`control_lease_state` enum；`hal_state` enum；`hal_last_ack_seq` uint64；`hal_last_reject_reason` enum | 50 Hz 快照；每变更发事件；上游逾消息 TTL 标 UNKNOWN，不猜 `switch_ready`；年龄无效=UINT32_MAX；HAL 状态失联=HAL_UNKNOWN |
| `RobotStateSnapshot`（内部 RT 固定布局） | **保留 V1.0 D5.2** 的 `boot_id_hi,boot_id_lo,tick_id,snapshot_robot_time_ns,joint_count,joints,imu` 等字段；仅增加 `snapshot_seq` uint64；在同一 boot 内 `snapshot_seq==tick_id` 且单调；`snapshot_robot_time_ns` 是 monotonic ns。**不新增** `stamp_robot_ns` 别名 | 一次 RT snapshot 构造时赋值；Worker 冻结读取；boot/序号/时间无法共同校验则 ExitDecision 视为 WAIT，关键观测失效保护；固定 IPC 结构升级 ABI，不得在 RT 用动态 protobuf 反序列化 |
| `JointTargetArray` | `boot_id` UUID、`action_epoch` uint64、`tick_id` uint64、`snapshot_seq` uint64、`deadline_ns` uint64、`joint_count` uint32、`joints[] {name,index,mode,q_rad,dq_radps,tau_nm,kp,kd,enabled}` | 全关节 `joint_count` 和 RobotDescription 一致、索引唯一、有序；跨进程候选过期/数值无效/掩码冲突拒收；它是 RT 输出的**逻辑目标**，尚不是完整 HAL 命令 |
| `ExitDecision` | `kind` enum (`READY/WAIT/REFUSE`)、`reason_code` uint32、`snapshot_seq` uint64、`valid_until_ns` uint64、`retry_not_before_ns` uint64；在 `SealedExitDecision` 中另附 `boot_id,action_epoch,runner_instance_id,seal_seq,snapshot_stamp_ns` | 必须与活动 Runner 身份匹配，快照序差≤4（按 200/50 Hz）、年龄≤25 ms、`now<=valid_until_ns`；不满足统一当 `WAIT`；`REFUSE` 锁存至下一次 `enter`，安全抢占例外 |
| `HalCommand` | `boot_id,writer_id,seq,action_epoch,deadline_ns,payload_crc,joint_count,joints[],mode_plan_id` + 内部经过许可的 token/session | HAL 验证 owner/seq/epoch/时效/CRC/capability；拒收有 ack 和原因；控制模式变化另需异步 PREPARE_MODE、`mode_plan_id` 一次性绑定，失写由硬件侧 watchdog 兜底，详见 `HAL_CONTRACT.md` |
| `HalStatus` | `ack_event_seq,seq_ack,accepted,reject_reason,watchdog_state,active_writer,hal_state,fault_bits,active_epoch,last_accepted_seq,last_accept_mono_ns,prepared_mode_plan_id,mode_plan_ready,boot_id,status_stamp_mono_ns,last_ack_mono_ns,pending_epoch,epoch_prepared,epoch_prepare_tx_id` | 必须为只读独立状态镜像；ACTIVE 期间≥200Hz ACK/状态，建议 10 ms 状态/ACK 新鲜度门槛；RT 发现拒收或超期进入保护；非阻塞读取 |

**对应 C++ 语义**：`MotionStatus` 的生成 C++ 结构必须具有以上所有字段；不得沿用 V1.0 D6.2 的删减手写结构。`RequestHeader` 不出现另一种毫秒截止字段；只有 `ScheduledAction` 持绝对 `deadline_ns`。

```cpp
// 结构性伪代码：生产代码由 proto 生成，字段和单位以该协议为准。
struct RequestHeader { Uuid request_id, session_id; uint32_t source_id;
  uint64_t issued_utc_ns; uint32_t timeout_ms; Digest32 payload_digest; };
struct ScheduledAction { ActionRequest request; uint64_t deadline_ns; };
struct ExitDecision { ExitKind kind; uint32_t reason_code; uint64_t snapshot_seq;
  uint64_t valid_until_ns; uint64_t retry_not_before_ns; };
struct SealedExitDecision { Uuid boot_id; uint64_t action_epoch;
  Uuid runner_instance_id; uint64_t seal_seq; uint64_t snapshot_stamp_ns;
  ExitDecision data; };
struct EffectiveVelocity { float vx_mps, vy_mps, wz_radps; };
struct MotionStatus { Uuid boot_id, request_id, execution_id, session_id;
  uint64_t seq, action_epoch, stamp_robot_ns; uint32_t source_id;
  StringId current_action, target_action; SwitchPhase phase; TransitionPhase transition_phase;
  Form form; bool stable, switch_ready, action_done;
  StringId active_primary; FixedArray<StringId, MAX_OVERLAYS> active_overlays;
  EffectiveVelocity effective_velocity; uint32_t effective_velocity_source_id, effective_velocity_age_ms;
  SafetyState safety_state; uint32_t latched_fault_code;
  uint32_t feedback_age_max_ms, inference_age_ms; StringId release_id;
  Digest32 manifest_sha256; Uuid control_lease_id; ControlLeaseState control_lease_state;
  HalState hal_state; uint64_t hal_last_ack_seq; HalRejectReason hal_last_reject_reason; };
```

## 3. ActionGraph：唯一根 `nodes`

**Canonical**：根 `schema_version, nodes, edges`；`nodes` 为动作 ID 数组，**只包含 Action，不包含 `SAFE_HOLD`、`DAMPING`、`ESTOP`、`INIT` 等安全状态**。安全抢占无条件旁路图。边字段 `from,to,cost,guard,max_duration_ms,on_timeout`；`on_timeout` 为 `DAMPING` 等安全路由标识而不是图节点。`max_duration_ms` 是边执行的配置时长，启动边时计算 `edge_deadline_ns`。图不能选择未批准的保护动作；`SAFE_HOLD` 需要运行时支撑许可，缺许可退到 HAL 已验证低能量路径。

```yaml
# Canonical 完整示例。实际文件：examples/action_graph.yaml
schema_version: '1.1'
nodes: [quad_stand, quad_drive, quad_stop, q2b, biped_balance, b2q]
edges:
  - from: quad_drive
    to: quad_stop
    cost: 1
    guard: [feedback_fresh]
    max_duration_ms: 1500
    on_timeout: DAMPING
  - from: quad_stop
    to: q2b
    cost: 3
    guard: [support_valid, clearance_token_fresh]
    max_duration_ms: 2000
    on_timeout: DAMPING
```

上面 `1500/2000 ms` 仅为**示例配置【假设】**，不得启用真实动作；全部节点对应的 `release.status` 仍需独立审核。禁止在 Graph 中添加一个 `safety` Action 以绕过内核。

## 4. RunnerManifest：唯一身份与双维选择

| 位置 | 类型和语义 | 校验/失败 |
|---|---|---|
| `schema_version` | string `1.1` | 其他主版本拒绝激活 |
| `manifest_id,version,action_id,behavior_id` | 非空 ID/版本 | 注册冲突拒绝 |
| `robot_compatibility` | `robot_ids,topology_sha256,calibration_sha256` | 当前机器 Hash 必须匹配 |
| `runner.execution_kind` | `ONNX/CLASSICAL/PLAYBACK/COMPOSITE` | 决定算法执行机制 |
| `runner.behavior_role` | `LOCOMOTION/TRANSITION/BALANCE/POSE/RECOVERY/OVERLAY` | 决定行为接口和守卫 |
| `runner.class_id` | 注册工厂 class ID（唯一解析） | 必须与双维映射表相符 |
| `runner.backend_id` | 例 `onnxruntime_cpu`,`classical_builtin`,`trajectory_engine`,`composite_engine` | 在工厂能力白名单内 |
| `runner.abi_version,period_ms,worker_budget_ms` | ABI 版本/计算周期 ms/预算 ms | budget < period；非 RT |
| `asset.kind,path,sha256` | 模型/轨迹/内置资产与哈希 | 内置无路径，模型带路径与 SHA |
| `tensor_io.inputs/outputs` | `name,dtype,shape,semantic` | 所有端口名称、维度完全覆盖 |
| `obs_spec.path/sha256`,`action_spec.path/sha256` | 完整 CSV 引用 | 所有逐维映射闭合，不允许缺省隐式规则 |
| `owns` | 规范 joint 名数组 | 精确转换成 Bitset 并与 Bundle 匹配 |
| `entry,exit,completion` | `predicates,max_duration_ms,stable_ms?` | 超期转换为内部绝对 deadline，不可无限 WAIT |
| `failure_target` | 安全/阶段已批准 fallback | UNKNOWN form 下不得选择 SAFE_HOLD |
| `golden.path/sha256` | 输入输出签收资产 | 未通过 Golden 拒绝开放 |
| `release.status,release.release_id` | 发布级审批状态和 release ID | 只有 APPROVED 可进入可运动资产库 |

**发布与运行两套状态，不混用：**

- `release.status`：`DISABLED`（禁止发行）/`CANDIDATE`（可测试但不可正常运动）/`APPROVED`（审批通过）。它写在签名发布包里，不随运行变化。
- `runtime.asset_state`：`UNLOADED` → `LOADING` → `AVAILABLE` → `ACTIVE`；任意态可因校验/失效进入 `BROKEN`。运行时 `AVAILABLE` 的前提是 release.status=APPROVED、拓扑/校准匹配、规格校验、资源和 Golden 成功。`ACTIVE` 只表明 RT 已提交该动作当前 Epoch，不能等同 `RUNNING` 的物理稳定。

**工厂唯一选择**：验证 `class_id == Registry[(execution_kind,behavior_role)].class_id` 且 `backend_id ∈ allowed_backend_ids`，不满足则 `MANIFEST_CLASS_MISMATCH`；每个 `(kind,role)` 只注册一个首版工厂，禁止按类名模糊回退。

## 5. ObsSpec 和 ActionSpec CSV：严格语义

### ObsSpec CSV 完整列

`tensor_name,index,block,element,source,source_field,joint_or_axis,unit,frame,transform,offset,scale,clip_min,clip_max,filter_id,history_lag,history_order,include_current,initial_fill,missing_policy_ref,dtype`

- `transform` 枚举：`IDENTITY` / `CENTER_SCALE_CLIP` / `SCALE_CLIP` / `ANGLE_WRAP_SCALE_CLIP` / `QUAT_TO_GRAVITY_SCALE_CLIP`。顺序为源读取→frame/方向换算→滤波（固定阶数/系数/初态）→transform→按 tensor index 写入。`CENTER_SCALE_CLIP`：`clamp((x-offset)*scale,clip_min,clip_max)`；其它 transform 必须有逐值定义和 Golden。
- `history_order`：`OLDEST_TO_NEWEST` / `NEWEST_TO_OLDEST`；`include_current` 是严格 boolean；`history_lag` 为非负整数 Worker tick，0 表示当前拍；`initial_fill`：`REPEAT_FIRST/ZEROS/REFERENCE/ASSET`。即使 `history_length=1` 也显式填写；同一张量的历史参数必须一致。
- `missing_policy_ref` 引用 `safety_limits.yaml`/规格注册表中的已批准缺失策略，如 `STRICT_INVALID`（样例所有项采用），不允许运行时以零替代未定义字段。可选值缺失必须与训练端填充方式一致；跨板时间不同步直接 INVALID。
- `(tensor_name,index)` 唯一且从 0 连续，数目与 tensor IO 声明相等；同一 joint 映射明确 `source_field=q`、关节方向经过 SensorAdapter 归一化；任何 source 缺失、dtype 错误拒绝加载。

### ActionSpec CSV 完整列

`tensor_name,tensor_index,joint_name,mode,unit,scale,default,raw_clip_min,raw_clip_max,activation,kp,kd,tau_ff,limit_profile,owns,sign`

- 端口每一维都必须恰好覆盖，`owns=true` 的 joint 不得出现两行，关节名与规范映射一一对应；`sign ∈ {-1,+1}`、`scale>=0`，`activation` 取 `IDENTITY/TANH`。`default` 位于 **机器人规范关节坐标系**，不是电机坐标系。
- **唯一解码公式**：`a0 = activation(raw)` → `a1 = clamp(a0,raw_clip_min,raw_clip_max)` → `a2 = sign * a1` → `value = default + scale*a2`（TORQUE 在此基础上加 `tau_ff`）；再匹配 `kp/kd/mode`。因此 sign 是**训练输出到规范关节正方向**的变换，仅在 Codec 执行一次。
- **`RobotDescription.direction` 是规范关节到电机坐标正方向的设备变换**，仅 HAL 执行一次。不得在 ObsBuilder、Codec、OutputGuard 和 HAL 重复变号。反馈从电机坐标到规范关节坐标也仅在 HAL 的反馈适配端应用一次逆变换。若 `sign=-1` 且硬件 `direction=-1`，它们服务两个不同坐标边界，并不互相抵消到可省略的意义。
- `raw_clip` 属模型域，不是物理安全限幅；OutputGuard/HAL 另检查 `q/dq/tau/kp/kd`、估计扭矩、命令变化率和受限模式。未知模式禁止转换。

### 16 关节**完整演示**映射

`examples/demo16_obsspec.csv` 与 `examples/demo16_actionspec.csv` 都恰好包含 **16 行**，按 `fl_hip,fl_thigh,fl_calf,fr_hip,fr_thigh,fr_calf,rl_hip,rl_thigh,rl_calf,rr_hip,rr_thigh,rr_calf,fl_wheel,fr_wheel,rl_wheel,rr_wheel` 顺序；`tensor_io` 定义演示端口 `demo_obs FLOAT32 [1,16] → demo_act FLOAT32 [1,16]`；前 12 个演示为 POSITION (rad)，后 4 个为 VELOCITY (rad/s)。这是**虚构的结构完整性测试夹具**，【非 Collie 事实】【不可上机】，`release.status=CANDIDATE`、硬件限幅未签发。逐行的 `sign`、default、gain、limit_profile 均显式列出，没有“其余关节类推”的隐含实现。

## 6. 黑匣子唯一容量

- `blackbox.ring_bytes = 134217728`，即 **128 MiB**，仅是**初版内存预算【建议】**，不是 Collie 已测可用 RAM。
- 合计编码预算：Worker 全部运行实例合计 `8192 B × 50 Hz = 409600 B/s`，RT `256 B × 200 Hz = 51200 B/s`，总 `460800 B/s ≈ 0.4395 MiB/s`；在这个上界下，可容纳 `128 MiB / 0.4395 MiB/s ≈ 291 s`（尚未预留索引）。
- 保留 `16 MiB` 用于索引、事件与容量浮动，允许记录容量 `112 MiB`：可保存约 `255 s`；故障前 30 s 加后 10 s，最少需 `460800×40 ≈ 17.58 MiB`，加上 `16 MiB` 预算仍低于 128 MiB。
- **容量准入条件**：包括 Header/对齐/辅助模型在内的**全部活跃 Runner** 平均上界及最坏单窗 `recorded_max_bytes_per_s ≤ (128−16) MiB/40 s = 2.8 MiB/s`。若超出，则该 Action 的“完整故障窗”能力标志为 `UNAVAILABLE` 并拒绝声称满足黑匣子验收；在批准增大内存预算或减少记录维度且仍满足需求前，禁止开放要求完整回放的高风险动作。
- RT 不调用写盘；故障触发时 ring 保存事件锚点并继续记录 10 s，异步转储最近 30 s + 后 10 s；超容量时不得静默覆盖故障前窗口。

## 7. 仓库布局、生成与 CI

```text
proto/collie_mc_v11.proto                   # 对外 / RT / HAL 消息字段唯一来源
schemas/action_graph.schema.json            # YAML 资产 schema
schemas/runner_manifest.schema.json        # 策略资产 schema
schemas/obs_spec.row.schema.json            # 逐行 CSV schema
schemas/action_spec.row.schema.json         # 逐行 CSV schema
schemas/safety_limits.schema.json           # 物理限额配置结构schema
safety_limits.yaml                           # 机型物理边界（不得从示例自动签发）
examples/action_graph.yaml
examples/demo16_runner_manifest.yaml
examples/demo16_obsspec.csv
examples/demo16_actionspec.csv
tests/check_examples.py
```

CI 强制流程：① `protoc` 生成 C++/ROS2 适配并检查无未提交变更；② YAML/CSV 与安全限额配置结构通过 JSON Schema 与 `mcctl validate` 跨资产语义校验；③ 文档中标为完整示例的代码块与 `examples` 做一致性比对并校验；④ schema 版本不匹配或未知字段拒绝；⑤ 检查旧语法的**活动配置/代码行**（禁止旧 Graph 根，禁止旧 RPC 截止字段，禁止旧黑匣子配置）；⑥ `golden`/哈希/模型端口真实加载在目标环境验证；⑦ schema break 必须增加 major 版本与迁移测试。详情及可运行检查参见 `tests/check_examples.py`。

## 8. V1.0 各章的必须覆盖位置

| V1.0 位置 | V1.1 覆盖要求 |
|---|---|
| D3.2 | `ExitDecision` 扩字段并以 `SealedExitDecision` 消除 Epoch/Runner ABA |
| D3.3/D3.4 | runner 双维矩阵、唯一工厂选择 |
| D4.1 | `release.status` 与 `runtime.asset_state` 不混用 |
| D4.2 与 D9.6 | 同一份 `action_graph.yaml`，仅 `nodes` 根；安全态不入图 |
| D4.6 与 D6.2/D6.1 | `MotionStatus` 与 proto 完全一致，不能使用删减版 |
| D5.3/D5.5 与 D9.5 | Obs/Action CSV 列与方向/历史公式完全一致 |
| D6.1/D6.2/D6.4 | 外部 `timeout_ms`、内部 `deadline_ns`，边相位 `max_duration_ms` |
| D8.4 与 D10.1 和 D6/D13 | 黑匣子唯一默认 128 MiB、40 s 准入上界 |
| D9.3/D9.4/D9.5 | Runner 新三个维度字段与 release 状态；现有 JSON schema 的 `runner` required enum、`guard` 字段同步 |

**注意**：本文件的 schema 是软件接口/配置的规范，不是物理稳定性、硬件急停或功能安全认证的证明。
