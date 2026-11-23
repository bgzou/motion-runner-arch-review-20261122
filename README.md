# Motion Runner Architecture Review · 2026-11-22

> 输入包：为网页版 GPT 提供 **Collie 轮足机器人运控（MC）Runner 框架**完整架构设计所需的架构、接口、真机配置与逆向证据。
> 目标：让 GPT 产出一份**可评审、可落地、可验收**的软件架构设计，而不是文档润色。

## 从这里开始

1. **[00_READ_ME_FIRST.md](00_READ_ME_FIRST.md)** — 阅读顺序、证据规则、两套候选抽象的张力。
2. **[01_PROMPT_FOR_GPT.md](01_PROMPT_FOR_GPT.md)** — 正式任务书：角色、边界、14 个必须裁决的问题、D0–D16 交付物、评分 rubric、分 6 段输出。
3. **[02_CONTEXT_BRIEF.md](02_CONTEXT_BRIEF.md)** — 15 分钟项目背景。
4. **[03_EVIDENCE_MAP.md](03_EVIDENCE_MAP.md)** — 每条关键论断的证据与强度。
5. **[04_OPEN_QUESTIONS.md](04_OPEN_QUESTIONS.md)** — 必须拍板的问题与默认建议。
6. **[05_GLOSSARY.md](05_GLOSSARY.md)** — 术语表。
7. **[v1.3/README.md](v1.3/README.md)** — V1.3 50 Hz 频率修订版（全文 + 6 Part + 附录 + 19 页 Deck）。
8. **[PROMPT_FOR_GPT_V2_RESTRUCTURE.md](PROMPT_FOR_GPT_V2_RESTRUCTURE.md)** — V2 重写任务书：先全貌、再模块、再接口；先只交 Stage 1。

## 核心问题

Collie 的 Runner 框架要同时满足：

- **一个关节出口**：任务/导航/安全不能绕过 `OutputGuard` 直接写电机；
- **一套策略契约**：模型 + manifest + 本体映射 + obs/action 规格 + 进入/退出守卫 + 验收向量；
- **一条可回放的每拍链路**：采样 → 快照 → 观测 → 推理 → 解码 → 合成 → 限幅 → 发布；
- **一条不依赖推理的安全路径**：急停、反馈过期、NaN、越界、推理超时都能独立进安全态；
- **一套可扩展的切换/叠加机制**：连续、一次性、过渡、叠加、安全五类行为用同一模型表达。

## 仓库地图

```text
README.md
00_READ_ME_FIRST.md          阅读入口
01_PROMPT_FOR_GPT.md         任务书
02_CONTEXT_BRIEF.md          背景综合
03_EVIDENCE_MAP.md           论断→证据
04_OPEN_QUESTIONS.md         必须裁决的问题
05_GLOSSARY.md               术语
architecture/                第 3/5/6/12 章原文（总体架构、任务、感知、安全）+ HTML
runner/                      Runner 主文档、接口与数据链路、T1 MC 拆解
system/                      4+1、安全、三链路、对外接口、简化交付
requirements/                17 UC + 3 IR 需求原文
evidence/
  interfaces/                MC 相关 .msg/.srv 全量目录
  configs/                   真机 action_setting/action_ruler/mc_T1/rl 配置
  model-list/                58 动作/62 执行组/42 RL/34 权重/换乘图统计
  diagrams/                  策略切换/策略链路图
reference/                   T1 硬件/OS/SDK/参考实现
v1.3/                        V1.3 50Hz 全文、6 Part、附录、Deck、contracts
PROMPT_FOR_GPT_V2_RESTRUCTURE.md  V2 重写任务书（先全貌/再模块/再接口）
MANIFEST.csv                 文件清单 + SHA256
SHA256SUMS.txt               校验和
```

## 证据规则

- **【事实】**：原始配置/IDL/符号/日志可核对；
- **【假设】**：Collie 未冻结，先按此设计，必须给验证方法；
- **【建议】**：架构选择，需评审拍板；
- **【待定】**：需实验/标定/产品输入。

T1 的 Action 数字、关节顺序、模型尺度、阈值**不可直接复制**到 Collie；只复用结构关系与工程约束。

## 来源与边界

- 来源项目：`D:\Projects\Athena\运动控制\Collie\T1运控架构分析`（2026-11-22 整理版）。
- 真机证据来自 T1 Pro 部署态 dump；逆向结论来自本地 YAML/IDL/ONNX/`.so` 符号，不是运行验证。
- 本仓库**不含**代码、训练资产、ONNX 权重、二进制；模型库与 `roboto_origin-main` 留在本地。
- 需求中的速度、高度、载荷、恢复时限均为草案，需本体/产品/安全联合签发。

## 使用方式

把 **[01_PROMPT_FOR_GPT.md](01_PROMPT_FOR_GPT.md)** 从“任务”一节开始整段复制给网页版 GPT，并确保它已开启联网/浏览。它会按 Part 1–6 输出；每部分结尾有完成度，便于你逐段追问。

如果 GPT 打不开某个链接：让它读 [00_READ_ME_FIRST.md](00_READ_ME_FIRST.md) 的索引，或把对应 `.md` 原文粘贴给它。
