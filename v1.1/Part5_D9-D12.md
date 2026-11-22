# Collie 运控服务软件架构 V1.1 — Part 5（D9–D12）

> 合并说明：本 Part 以 V1.1 的 `SCHEMA_CANON`、`schemas/`、16 关节 examples、128 MiB 黑匣子、36 个 SIL/合同测试为准；V1.0 的配置/测试/网络安全结构保留。  
> 唯一权威：`proto`（消息）、`schemas/*.json`（配置）、`safety_limits.yaml`（物理界限）；示例均为不可部署夹具。

---

## D9. 配置、资产、签名与升级

### D9.1 四级配置

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

## D10. 可观测性、黑匣子与回放

### D10.1 Trace 与每拍日志

每个 RPC/Event/Candidate/JointTarget/安全事件共享 `trace_id`，并传播 `request_id/execution_id/action_epoch/tick_id/boot_id/release_id`。日志线程不参与 RT；RT 写预分配二进制环，单独线程转储。

| 层 | 字段 | 采样 |
|---|---|---|
| SAMPLE | 实际使用的关节/IMU/接触、每源 timestamp/valid/seq、时基质量 | Worker 10 ms；HAL 高频故障窗按容量 |
| REFERENCE | source/seq/TTL/坐标变换前后速度、限制/失源原因 | 每 Worker tick + 源变更 |
| OBS | 逐维 tensor 名/shape/dtype/数组/历史顺序/摘要 | 每次推理（故障环完整） |
| MODEL | 模型 SHA/provider/IO/耗时/raw output | 每次推理（故障环完整） |
| CODEC | 解码目标/模式/增益/own_mask | 每次候选 |
| RT | Epoch/Mux/Guard clamp/原因/HAL 目标/seq/deadline | 每 5 ms |
| SWITCH | 阶段/物理守卫/fallback/原子接管 tick | 事件 |
| SAFETY | fault/latch/lease_seq/状态迁移/硬件确认 | 事件+周期摘要 |
| SYSTEM | CPU/内存/温度/时统/队列/磁盘 | 1 Hz |

### D10.2 黑匣子容量（唯一 128 MiB）

`blackbox.ring_bytes = 134,217,728`（128 MiB，建议）。编码预算：所有活跃 Worker 合计 `8192 B×100 Hz=819200 B/s`，RT `256 B×200 Hz=51200 B/s`，总 `870400 B/s≈0.8301 MiB/s`；128 MiB 可容约 154 s，未含索引。预留 16 MiB，允许记录 112 MiB，约 135 s；故障前 30 s+后 10 s 最少约 33.20 MiB，仍低于 128 MiB。准入条件：含 Header/对齐/辅助模型的全部活跃 Runner，平均与最坏单窗 `recorded_max_bytes_per_s ≤ (128−16) MiB/40 s = 2.8 MiB/s`；超出则该 Action 的“完整故障窗”标 `UNAVAILABLE`，不得声称满足黑匣子验收。

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

## D11. 测试、故障注入与签收

### D11.1 测试金字塔与门槛

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

阶段门：P0 影子（0 HAL 写）；P1 单 Action（Golden/100/200 Hz HIL/断流/封闭实机）；P2 切换/叠加（全开放边/非法边/超时/回放）；P3 安全联锁（杀 Worker/RT/Safety、硬件急停、HAL watchdog）；P4 形态（Q2B/B2Q/Balance 全 phase/接触/回退）。

### D11.4 CI 与证据

每次 PR：format/lint → compile → schema/static → unit/fuzz → Golden → graph-generated test → replay → deterministic IPC → report。每个候选 Release 补目标平台长稳时效/内存/线程泄漏/HIL fault matrix；涉及本体标定/Guard/模型张量/HAL 固件的改变必须触发相关真实设备回归。CI 产出带 `git SHA/compiler/OS image/robot_description_sha/model_sha/manifest_sha/golden_sha/test suite` 的不可变验收包，不能只留绿色勾号。

### D11.5 Q13 裁决

| 问题 | 决策 | 替代 | 切换条件 |
|---|---|---|---|
| Q13 测试 | Unit+Golden+Graph 全边+Fault+HIL+真实场景分级开放 | 只仿真/现场手测 | 自动化成熟后减少人工重复，但保留安全/回归门 |

---

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
