# 附录 C：协议、Schema、示例与测试索引

> 本附录不复制 `proto/schemas/examples/tests` 全文，只给“看什么、在哪、证明什么”。原始文件在 `../contracts/`。

## 1. 协议（唯一消息字段源）

| 文件 | 内容 | 看什么 |
|---|---|---|
| [`proto/collie_mc_v11.proto`](../contracts/proto/collie_mc_v11.proto) | 请求/状态/ExitDecision/HalCommand/HalStatus/ControlLease | 字段名、单位、枚举；`MotionStatus` 32 字段；`HalStatus` ack/reject |

**注意**：V1.1 PartA-E 的 C++ 伪代码里 `ExitKind` 写成了 `READY=0/WAIT=1/REFUSE=2`，而 proto 是 `EXIT_READY=1/WAIT=2/REFUSE=3`。合并版 Part2 已按 proto 改为 1/2/3；编码时必须由 proto 生成，不能手写第二套枚举。

## 2. 配置 Schema

| 文件 | 用途 | 关键约束 |
|---|---|---|
| [`schemas/runner_manifest.schema.json`](../contracts/schemas/runner_manifest.schema.json) | RunnerManifest | `execution_kind/behavior_role/class_id/backend_id`；release.status；entry/exit/completion |
| [`schemas/action_graph.schema.json`](../contracts/schemas/action_graph.schema.json) | ActionGraph | 根 `nodes`；安全态不入图；边 `max_duration_ms/on_timeout` |
| [`schemas/obs_spec.row.schema.json`](../contracts/schemas/obs_spec.row.schema.json) | ObsSpec 逐行 | 21 列；transform/history/include_current/missing_policy |
| [`schemas/action_spec.row.schema.json`](../contracts/schemas/action_spec.row.schema.json) | ActionSpec 逐行 | 16 列；sign/limit_profile/owns |
| [`schemas/safety_limits.schema.json`](../contracts/schemas/safety_limits.schema.json) | 安全限额结构 | `release_approved/physical_limits_signed/limit_profiles` |

**已知缺口**：`ModeTransitionPlan`、Q2B/B2Q phase 表、Factory 矩阵、HAL 能力表尚未成为独立 schema/config；目前只在 PartA-E 文档与测试硬编码中。编码前需补 `mode_transition_plan.schema.json`、`factory_matrix.yaml`、`hal_capabilities.yaml`。

## 3. 示例（不可部署）

| 文件 | 内容 | 用途 |
|---|---|---|
| [`examples/demo16_runner_manifest.yaml`](../contracts/examples/demo16_runner_manifest.yaml) | 16 关节演示 Manifest | 结构完整性；`release.status=CANDIDATE` |
| [`examples/demo16_obsspec.csv`](../contracts/examples/demo16_obsspec.csv) | 16 行 ObsSpec | 逐维字段/索引/历史 |
| [`examples/demo16_actionspec.csv`](../contracts/examples/demo16_actionspec.csv) | 16 行 ActionSpec | 位置/速度/`sign=-1` 示例 |
| [`examples/action_graph.yaml`](../contracts/examples/action_graph.yaml) | Graph 示例 | `nodes` 根 |
| [`safety_limits.yaml`](../contracts/safety_limits.yaml) | 未签发限额 | `approved=false`，必须拒绝正常运动 |

**示例不是 Collie 拓扑**：16 关节 = 12 腿 + 4 轮，是结构测试夹具；真实机器人以 RobotDescription/URDF/标定为准。

## 4. 测试（SIL/合同，不是系统测试）

| 文件 | 测试数 | 证明什么 | 不证明什么 |
|---|---:|---|---|
| [`tests/check_examples.py`](../contracts/tests/check_examples.py) | 12 | Schema/16 关节/Graph/工厂/128 MiB/ExitDecision 合同分支 | 真实模型/RT |
| [`tests/hal_contract_sil.py`](../contracts/tests/hal_contract_sil.py) | 9 | FakeHal 的 ack/reject/watchdog/双写/epoch/CRC | 真实 HAL/固件/电机 |
| [`tests/init_and_lease_sil.py`](../contracts/tests/init_and_lease_sil.py) | 11 | INIT/UNKNOWN、Lease 竞争/过期/撤权/失租 | 生产 C++/硬件 |
| [`tests/check_doc_contracts.py`](../contracts/tests/check_doc_contracts.py) | 4 | 文档示例与 examples 一致、旧字段不出现 | 编译器/生成器 |

运行：

```bash
cd v1.3/contracts
python tests/check_examples.py
python tests/hal_contract_sil.py
python tests/init_and_lease_sil.py
python tests/check_doc_contracts.py
```

合计 36/36 PASS，但请按“约 20 项状态机/SIL 模型、12 项 schema/样例/合同、4 项文档一致性”理解，不要当成 36 项系统测试。

## 5. 编码前必须补的三份机器可读文件

1. `schemas/mode_transition_plan.schema.json` + `examples/demo16_mode_transition_plan.yaml`；
2. `factory_matrix.yaml`（`(execution_kind,behavior_role) → class_id/backend` 的白名单）；
3. `hal_capabilities.yaml`（每机型支持的 JointMode、kp/kd 范围、watchdog 能力、状态 ACK 语义）。

没有这三份，PartA-E 里对应的表仍然只是“文档约定”，不是可加载/可校验的配置。
