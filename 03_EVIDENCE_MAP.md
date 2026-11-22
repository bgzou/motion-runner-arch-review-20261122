# 03 Evidence Map（论断 → 证据）

> 用途：让 GPT 和评审者知道每条关键论断来自哪里、证据强度如何。**路径均相对于 GitHub 仓库根目录**。
> 强度：`A` = 原始配置/IDL/符号可直接核对；`B` = 由多份证据推断；`C` = 需求/访谈/二手整理，需验证。

## 1. T1 架构与运行机制

| # | 论断 | 证据 | 强度 |
|---|---|---|---|
| E1 | T1 是双板：RK3576 运控板 + Orin 感知板；`mc` 在 RK3576 | `system/t1-architecture-deep-dive.md` §0.2；`reference/t1-pro-orin-rk-analysis.md` | A |
| E2 | `mc` 是单进程，约 36 线程（3 实时 + 33 普通） | `system/t1-architecture-deep-dive.md` §0.2、§2.3 | A |
| E3 | 运控频率金字塔：策略 10 ms、关节命令 ≈196 Hz、状态 50 Hz、PD/CAN 1 kHz | `system/t1-architecture-deep-dive.md` §0.3、§6.6；`system/t1-4plus1-architecture.md` | A |
| E4 | 换动作与换速度源是两条独立通道 | `system/t1-architecture-deep-dive.md` §3.3；`system/t1-mc-decomposition.md` §2 | A |
| E5 | 三台状态机：系统模式 / 任务 / 动作 | `system/t1-architecture-deep-dive.md` §0.5；`architecture/task-engine-and-state-machine.md` | A |
| E6 | 安全八层 + 跌倒三通道 + 50 ms 看护 | `system/t1-safety-design.md`；`system/three-links-safety-switching-shaping.md` Part A | A/B |
| E7 | 7 个速度源，优先级 70–100，TTL 1000 ms | `evidence/configs/mc_T1.yaml`；`system/t1-architecture-deep-dive.md` §8.4 | A |

## 2. T1 Runner 与 Action 机制

| # | 论断 | 证据 | 强度 |
|---|---|---|---|
| R1 | 存在 `RunnerBase`，生命周期钩子 `Configure/PreInit/Init/Trig/Run/Pause/Resume/Shutdown/EnterCheck/ExitCheck/PreRunOnce/AfterExit` | `runner/runner-integration-master.md` §2.2（`.dynsym` 检查记录） | A |
| R2 | `ActionManager` 持有/装配 Runner；区分 `TransitionTask` 与 `ResidentTask` | 同上；`runner/t1-mc-decomposition.md` §2 | A |
| R3 | 每个 Runner `.so` 导出 `CreateRunner/DestroyRunner`，由工厂装载 | `runner/runner-integration-master.md` §2.2 | A |
| R4 | `RunnerContext`/`RunnerDataBoard` 存在，传递动作上下文与数据槽 | 同上 | A |
| R5 | `action_setting.yaml` 定义 Action → 执行组 → runner/cfg/period/priority；一个 Action 可含多个 Runner | `evidence/configs/action_setting.yaml`；`runner/runner-integration-master.md` §4.2 | A |
| R6 | `action_ruler.yaml` 定义合法切换边与出口 | `evidence/configs/action_ruler.yaml`；`runner/runner-integration-master.md` §5.2 | A |
| R7 | 58 动作 / 62 执行组 / 42 RL 条目 / 34 份现役权重 / 15 经典控制；换乘图 52 节点/197 边 | `evidence/model-list/action-execution-runner.md`、`evidence/model-list/rule-graph-stats.md` | A |
| R8 | ONNX 常见双输入：`observations[1,N]` + `observation_history[1,N*10]`；不同模型 N=49/51/57 | `runner/runner-interface-and-dataflow.md` §6；`evidence/configs/rl_quad_walk.yaml`、`rl_bi_wbc_run.yaml`、`rl_quad_to_bi_run.yaml` | A |
| R9 | ONNX 输出不能直接下发；需 `action_clip/action_scale/default_dof_pos/kps/kds/activation/tau_limit` 后处理 | `evidence/configs/rl_quad_walk.yaml`；`runner/runner-interface-and-dataflow.md` §7 | A |
| R10 | 二进制符号不能还原完整 `RunnerContext` 字段、虚函数语义、每拍时序与 ABI | `runner/runner-integration-master.md` §2.2 | A（负面证据） |

## 3. 对外接口与数据

| # | 论断 | 证据 | 强度 |
|---|---|---|---|
| I1 | `SetMcAction{source, McActionCommand{action, action_desc}} → CommonTaskResponse{task_id,state}` | `evidence/interfaces/MC_INTERFACE_CATALOG.md`（SetMcAction / McActionCommand / CommonTaskResponse） | A |
| I2 | 速度接口 `McLocomotionVelocity{source, vx, vy, wz, pitch, level}`，话题 `/aima/mc/locomotion/velocity` | `evidence/interfaces/MC_INTERFACE_CATALOG.md`；`evidence/configs/mc_T1.yaml` | A |
| I3 | 关节反馈 `JointStateArray` 每关节含 `name,position,velocity,effort,coil_temp,motor_temp,motor_vol` | `evidence/interfaces/MC_INTERFACE_CATALOG.md` | A |
| I4 | 关节命令 `JointCommandArray` 每关节含 `name,position,velocity,effort,stiffness,damping` | 同上 | A |
| I5 | 状态 `McCommonState` 含 action/form/switch_ready 等，不能合并成一个布尔 | 同上；`runner/runner-integration-master.md` §2.1 | A |
| I6 | MC 对外 11 个 RPC（动作/查询/播放/预设/输入源/运行模型/录制） | `system/t1-mc-decomposition.md` §2.1；`evidence/configs/mc_T1.yaml` | A/B |
| I7 | 真机 14 关节，CAN0/CAN1 映射，零偏/方向/限位/MIT 范围 | `reference/real-machine-evidence-notes.md`；`system/t1-architecture-deep-dive.md` §10 | A |

## 4. 需求与产品约束

| # | 论断 | 证据 | 强度 |
|---|---|---|---|
| P1 | 17 个 UC + 展馆 3 个 IR；覆盖迎宾/领路/跟随/合影/运镜/看护/载物/楼梯等 | `requirements/requirements-scenarios.txt` | C |
| P2 | 产品形态包含四足轮式、双足直立、静态稳定/后双轮自平衡等表述，存在冲突 | `requirements/requirements-scenarios.txt`；`runner/runner-integration-master.md` §12 | C |
| P3 | 展馆拥挤限速、30 cm 避障、被撞 5 s 恢复等是需求草案，检测与自动恢复条件不完整 | `requirements/requirements-scenarios.txt`；`runner/runner-integration-master.md` §12 | C |
| P4 | 头/前肢手势与平衡策略可能争用关节，需 `owns_mask` 或重训练 | `runner/runner-integration-master.md` §4.4、§12 | C |

## 5. 参考实现

| # | 论断 | 证据 | 强度 |
|---|---|---|---|
| X1 | `roboparty_deploy` 已有 `PolicyRuntime`、配置化观测块、历史缓冲、ONNX Runtime、`/cmd_vel` 接入、推理/控制循环 | `runner/runner-integration-master.md` §9；`reference/quadruped-software-architecture.md` | A/B |
| X2 | 现有 `setup_model` 拒绝多输入 ONNX；`RobotInterface::apply_action` 支持 `p/v/kp/kd/tau`，但控制路径主要用位置 | `runner/runner-integration-master.md` §9 | A/B |
| X3 | 默认 RPO 配置 23 关节；T1 `qd1_t2d0` 14 关节；不能混用 | `runner/runner-integration-master.md` §0；`reference/quadruped-software-architecture.md` | A |

## 6. 使用规则

1. **引用数字必须带证据编号**（E/R/I/P/X），不要凭印象补数。
2. 证据强度 `C` 的内容只能作为需求/约束，不能当作已实现的接口。
3. 若两份文档冲突，优先原始配置/IDL（A），其次多源推断（B），最后二手整理（C）。
4. T1 的数值只用于**校准量级与结构**，不用于 Collie 的最终参数。
5. 找不到证据的论断，写 `【假设】` 并给验证方法，不要伪装成事实。
