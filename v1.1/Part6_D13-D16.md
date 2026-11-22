# Collie 运控服务软件架构 V1.1 — Part 6（D13–D16）

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
| ADR-05 | 100 Hz 策略 + 200 Hz 发布 | 分离推理与发令 | 同频；需 hold/整形 | 【假设+建议】 |
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

## D15. 实施路线、人力、迁移与回滚

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
| P1 单 Action W4–W6 | QuadStand/QuadWheelDrive 二选一；Obs/Codec/Guard、真实 HAL | 单动作 Golden、100/200 Hz HIL、断流保护、封闭实机签收 | HAL watchdog/硬件急停失败即阻断 |
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
