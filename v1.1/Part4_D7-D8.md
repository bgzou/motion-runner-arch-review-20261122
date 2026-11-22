# Collie 运控服务软件架构 V1.1 — Part 4（D7–D8）

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

## D8. 并发、实时性与内存

### D8.1 线程与 CPU

以抽象核 H0（HAL）、R0（RT）、S0（Safety）、W0（Worker）、N0（非实时）说明；平台冻结后映射物理核。核数不足时必须重新做共核预算/隔离并通过 HIL，不能直接删安全调度证明。

| 进程.线程 | 工作 | 周期 | 优先级建议 | 核/栈 | 队列 | 超时 |
|---|---|---|---|---|---|---|
| device_hal.bus_loop | 执行器命令/反馈 | 设备要求，目标 1 kHz | FIFO 95（同 OS 时） | H0/128 KiB | 固定 4 槽 | MC 命令 15 ms 超时→设备保护 |
| mc_rt.control_publish | Snapshot/Arbiter/Switch/Mux/Guard/publish | 5 ms/200 Hz | FIFO 90 | R0/256 KiB | 最新候选 4 槽 | 自监测 WCET；HAL 超时兜底 |
| mc_safety.monitor | 独立监控/Lease | 10 ms/100 Hz | **S0 独立核/FIFO92** | S0/128 KiB | 重要事件 16 槽 | 不续租→RT 禁正常输出 |
| mc_runner_worker.step | Obs/模型/Codec/Runner | 10 ms/100 Hz | SCHED_OTHER 或测试过的 DEADLINE | W0/512 KiB | snapshot/candidate 4 槽 | 超 8 ms 结果作废；超时计数 |
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

WCET 是上界，p99 不等于 WCET。RT 5 ms 预算 2.10 ms（Snapshot 0.20、校验 0.20、仲裁 0.15、候选 0.20、Mux 0.25、整形 0.35、Guard 0.30、发布 0.25、统计 0.20），保留 2.9 ms。Worker 7.6/10 ms，保留 2.4 ms。超期：Worker 晚于 deadline 一律无效；RT 任一 5 ms miss 记录 `RT_DEADLINE_MISS` 与真实最大时间，不补发过期 tick；Safety Lease 不续→RT 停正常输出；HAL 永久无更新→独立 watchdog 保护。不能依赖“超了三次才处理”。

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
