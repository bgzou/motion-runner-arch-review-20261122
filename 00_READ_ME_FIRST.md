# 00_READ_ME_FIRST

**给 GPT / 评审者的入口。先读这一页，再按顺序读核心文件。**

## 这是什么

这是 **Collie 轮足机器人运控（MC）软件架构**的评审输入包，目标只有一个：

> 以启元 T1 Pro 的真机证据为参照，设计一套可落地、可验收的 **Runner 框架**——包括上下游、接口、数据链路、切换、安全、配置、测试与运维。

它不是代码仓库，也不是训练资料；所有原始配置/IDL/逆向证据都按主题放在 `architecture/`、`runner/`、`system/`、`evidence/`、`reference/` 下。

## 你要产出什么

一份**完整的软件架构设计**，不是读书笔记、不是原则清单。最低要求：

- 能让开发据此拆模块、写接口、排期；
- 能让测试据此做 golden 回放、切换图覆盖、故障注入、HIL；
- 能让运控据此交付策略资产（manifest / obs spec / action spec / golden fixture）；
- 能让非软件背景的决策者看懂“为什么这样分层、代价是什么、还要拍板什么”。

完整交付物清单、评分 rubric 与输出分段方式，见 **[01_PROMPT_FOR_GPT.md](01_PROMPT_FOR_GPT.md)**。

## 15 分钟阅读顺序

| 顺序 | 文件 | 为什么 |
|---|---|---|
| 1 | [02_CONTEXT_BRIEF.md](02_CONTEXT_BRIEF.md) | 项目背景、T1 事实、当前两套候选抽象、未冻结假设 |
| 2 | [04_OPEN_QUESTIONS.md](04_OPEN_QUESTIONS.md) | 14 个必须裁决的问题；不要回避 |
| 3 | [03_EVIDENCE_MAP.md](03_EVIDENCE_MAP.md) | 每条关键论断的证据与强度 |
| 4 | [05_GLOSSARY.md](05_GLOSSARY.md) | 术语对齐，避免同词异义 |
| 5 | [01_PROMPT_FOR_GPT.md](01_PROMPT_FOR_GPT.md) | 正式任务书与交付物 |

## 核心设计输入（按优先级）

### 第一优先：总体架构与 Runner 主文档

1. [architecture/architecture-design.md](architecture/architecture-design.md) — 第 3 章：大脑/小脑/平台三子系统职责划分、边界判据、场景协同。
2. [runner/runner-integration-master.md](runner/runner-integration-master.md) — 当前 Runner 主文档：边界、外部接口、`IRunner`/`ActionBundle`、逐拍链路、切换、配置、验收。
3. [runner/runner-interface-and-dataflow.md](runner/runner-interface-and-dataflow.md) — 字段、tensor、obs/action 规格、golden fixture。
4. [system/t1-architecture-deep-dive.md](system/t1-architecture-deep-dive.md) — T1 双板三机、频率金字塔、Runner、数据链路、安全（第 0/2/3/6/8/10 章）。
5. [system/motion-control-architecture-delivery.md](system/motion-control-architecture-delivery.md) — 另一套简化交付方案：Behavior/Mode/Scope、4 RPC、Lease、线程模型。**与第 2 份存在张力，必须统一。**

### 第二优先：安全、任务、接口

6. [architecture/security-module-architecture.md](architecture/security-module-architecture.md) — 第 12 章安全模块架构。
7. [system/three-links-safety-switching-shaping.md](system/three-links-safety-switching-shaping.md) — 安全/切换/整形三条链路。
8. [system/t1-safety-design.md](system/t1-safety-design.md) — T1 安全 4+1。
9. [architecture/task-engine-and-state-machine.md](architecture/task-engine-and-state-machine.md) — 第 5 章任务调度与状态机（上游）。
10. [evidence/interfaces/MC_INTERFACE_CATALOG.md](evidence/interfaces/MC_INTERFACE_CATALOG.md) — MC 相关 `.msg/.srv` 全量定义。
11. [evidence/configs/mc_T1.yaml](evidence/configs/mc_T1.yaml)、[action_setting.yaml](evidence/configs/action_setting.yaml)、[action_ruler.yaml](evidence/configs/action_ruler.yaml) — 真机话题/服务/速度源/执行组/切换边。
12. [evidence/model-list/action-execution-runner.md](evidence/model-list/action-execution-runner.md)、[evidence/model-list/rule-graph-stats.md](evidence/model-list/rule-graph-stats.md) — 58/62/42/34/15、52 节点/197 边。

### 第三优先：按需查阅

| 文件 | 用途 |
|---|---|
| [system/t1-4plus1-architecture.md](system/t1-4plus1-architecture.md) | T1 完整 4+1 视图 |
| [runner/t1-mc-decomposition.md](runner/t1-mc-decomposition.md) | T1 MC 线程/服务/速度源/`SetMcAction` 全链路 |
| [runner/runner-integration-early.md](runner/runner-integration-early.md) | 早期评审稿（已被主文档取代，仅追溯） |
| [system/motion-external-interfaces.md](system/motion-external-interfaces.md) | 运控对外接口与场景交互 |
| [requirements/requirements-scenarios.txt](requirements/requirements-scenarios.txt) | 17 UC + 3 IR 需求原文（数字为草案） |
| [reference/t1-pro-orin-rk-analysis.md](reference/t1-pro-orin-rk-analysis.md) | T1 硬件/OS/启动链/线程模型 |
| [reference/t1-pro-developer-sdk-analysis.md](reference/t1-pro-developer-sdk-analysis.md) | 官方 SDK 接口与限制 |
| [reference/quadruped-software-architecture.md](reference/quadruped-software-architecture.md) | 四足软件总体架构与参考实现 |
| [reference/t1-pro-30min-talk.md](reference/t1-pro-30min-talk.md) | T1 架构 30 分钟摘要 |
| [reference/primebot-sdk-interface.md](reference/primebot-sdk-interface.md) | SDK 接口全表（可选） |
| [architecture/task-engine-and-state-machine.md](architecture/task-engine-and-state-machine.md) | 第 5 章：任务/状态机 |
| [architecture/sensor-preprocessing-and-perception.md](architecture/sensor-preprocessing-and-perception.md) | 第 6 章：传感器/感知（观测上游） |

## 证据与事实规则

- **【事实 E#/R#/I#/P#/X#】**：有原始配置、IDL、符号或日志可核对；编号见 [03_EVIDENCE_MAP.md](03_EVIDENCE_MAP.md)。
- **【假设】**：Collie 尚未冻结，先按此设计，必须给验证方法。
- **【建议】**：架构选择，需评审拍板。
- **【待定】**：需要实验/标定/产品输入，本轮不能闭环。

**T1 的 Action 数字、关节顺序、模型尺度、阈值不可直接复制到 Collie**；只能复用其结构关系与工程约束。

## 两套候选抽象的张力（务必先看）

| 维度 | Runner 中心（`runner-integration-master`） | 简化交付（`motion-control-architecture-delivery`） |
|---|---|---|
| 行为表达 | `ActionBundle`（primary + overlay + owns_mask） | `Behavior + CONTINUOUS/ONE_SHOT + ALL/LEGS/UPPER` |
| 过渡 | 独立 `TransitionRunner`（phase 驱动） | `ONE_SHOT + return_to` |
| 叠加 | `OverlayRunner` + 冲突检查 | `Scope=UPPER` 与 `LEGS` 并行 |
| 对外 | 3 类领域接口 + Adapter | 4 个 RPC |
| 复杂度 | 高，贴近 T1 | 低，易交付 |

你的任务不是简单选一个，而是给出**统一模型**：用一套最小概念同时表达连续、一次性、过渡、叠加、安全五类行为，并说明如何裁剪/迁移。

## 仓库结构

```text
README.md
00_READ_ME_FIRST.md
01_PROMPT_FOR_GPT.md
02_CONTEXT_BRIEF.md
03_EVIDENCE_MAP.md
04_OPEN_QUESTIONS.md
05_GLOSSARY.md
architecture/    第 3/5/6/12 章原文 + HTML 版
runner/          Runner 主文档、接口与数据链路、T1 MC 拆解
system/          4+1、安全、三链路、对外接口、简化交付
requirements/    需求原文
evidence/        MC 接口目录、真机配置、模型清单、图
reference/       T1 硬件/OS/SDK/参考实现
MANIFEST.csv     文件清单 + SHA256
SHA256SUMS.txt   校验和
```

## 开始

读完以上，直接打开 **[01_PROMPT_FOR_GPT.md](01_PROMPT_FOR_GPT.md)**，从 Part 1 开始输出。不要等确认，不要先提问；信息不足时做最合理假设并标注。
