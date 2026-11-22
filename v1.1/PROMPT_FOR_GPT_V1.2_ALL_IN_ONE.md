# 任务书：把 V1.1 架构讲透，并一次性产出全部交付物

> 用法：把本文件从“## 0”开始整段发给网页版 GPT；同时附上 V1.1 合并版与附录。  
> **本版要求一次性完成全部交付物**，不要停在 Stage 1 等确认。  
> **两套产物，边界必须分开**：  
> - **A. 报告融合包**：`01_BIG_PICTURE`、`02_CONCEPT_DEEP_DIVE`、`03_PART_ENRICHMENT/Part1..6`、`05_INTEGRATION_GUIDE`、`06_SELF_CHECK` —— 这些要能直接融合进 V1.1 报告。  
> - **B. 独立演示**：`04_ARCHITECTURE_REVIEW.html` —— 单独打开、单独讲，不并入 Markdown 报告，也不依赖报告里的链接/资源。  
> 若单条消息长度不够，按 §8 的文件顺序续写；保持文件名、编号、结构不变，不要重写已完成部分。
>
> **在线入口（优先读这个）**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/00_READ_ME_FIRST.md`
> 在线版文件名：`Full_D0-D16.md`、`Part1_D0-D2.md` … `Part6_D13-D16.md`、`Appendix_A_HAL_Contract.md`、`Appendix_B_Schema_Canon.md`、`Appendix_C_Protocol_Examples_Tests.md`、`REVIEW_V1.1.md`。本地文件名不同时，按内容对应。

---

## 0. 你是谁、我是谁、要解决什么

你同时扮演三个角色：

1. **资深机器人运控软件架构师**：懂 Runner、实时控制、HAL、功能安全、量产落地；
2. **技术讲师**：能把 DDD、实时线程、Lease、Manifest 这类概念用白话、类比和具体例子讲给非软件背景的人；
3. **架构汇报设计者**：能把架构拆成一套 25–30 页的 HTML 评审 deck，让软件同事听懂、能提问、能落地。

我是项目负责人，**不是软件设计出身**。我已经大致看完 V1.1，但感觉是：

> “每一个单独的东西，好像都觉得是这么一回事；但连不到一起。讲架构的时候，我讲不清楚。”

我的具体疑问（只是例子，不是全部）：

- HAL 到底是什么？
- D1.3 的“逻辑模块”是什么？和进程/线程是什么关系？
- “五个限界上下文”是什么意思？
- ControlLease 到底在链路里的什么位置？
- RunnerManifest 是什么？为什么需要它？
- 为什么说“八类 Runner”，但 `ExecutionKind × BehaviorRole` 看起来不止八种？
- 这八类 Runner 分别用于什么场景？我需要能判断“这个动作用哪个 Runner”是否合理。
- D3.7 三条关键时序图看不懂：谁先谁后、每条箭头什么意思、为什么要这样？
- `mc_rt`、`worker`、`gateway`、`safety`、`HAL` 分别是什么？它们怎么协作？
- D9.1 四级配置，每一级对应什么？长什么样？一个完整 Action 到底要哪些文件？
- 每个概念单看有道理，但整体串不起来；我担心给软件同事讲的时候讲不清楚。

**你的任务不是再写一份更长的架构文档，而是：先给我一个能背下来的大图景，再把每个概念讲到“我知道它为什么存在、放在哪、失败会怎样”，最后做成一套可汇报的 HTML deck。**

---

## 1. 输入材料（优先读 GitHub）

**在线入口（先读这一页）**：

`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/00_READ_ME_FIRST.md`

然后是：

1. **任务书（本文）**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/PROMPT_FOR_GPT_V1.2_ALL_IN_ONE.md`
2. **V1.1 合并全文**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Full_D0-D16.md`（最重要，先读）；
3. 6 个分 Part（用于细化）：
   - `.../v1.1/Part1_D0-D2.md`
   - `.../v1.1/Part2_D3-D4.md`
   - `.../v1.1/Part3_D5-D6.md`
   - `.../v1.1/Part4_D7-D8.md`
   - `.../v1.1/Part5_D9-D12.md`
   - `.../v1.1/Part6_D13-D16.md`
4. **附录 A**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Appendix_A_HAL_Contract.md`（HAL 细节）；
5. **附录 B**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Appendix_B_Schema_Canon.md`（字段/配置细节）；
6. **附录 C**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Appendix_C_Protocol_Examples_Tests.md`（proto/schema/example/test 索引）；
7. **评审意见**：`https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/REVIEW_V1.1.md`（已知 P0/P1）。

如果 GitHub 打不开：用用户提供的附件；若只能附 3 个文件，**Full + 附录 A + 附录 B**，Part 文件用于后续细化。

**约束**：

- 不改变 V1.1 的架构决策；发现矛盾/缺口时，用 `[审阅注记]` 标出并给建议，**不要静默改**。
- T1 的数字/配置不是 Collie 事实；Collie 未冻结项继续标 `【假设】/【待定】`。
- 不要把“设计写了”说成“已经验证”；不要把 SIL 测试说成系统测试。
- 不要用“高内聚低耦合”“视情况而定”作为解释；每个概念要给具体例子。

---

## 2. 先做根因诊断（不要跳过）

在写任何解释之前，先用一页写：

> **为什么一个非软件背景的人看这份架构会觉得“每个东西都对，但连不起来”？**

至少覆盖这些根因，并补充你发现的：

1. **自下而上、术语先行**：先讲 Runner/Manifest/Lease，没有先讲“一次请求从任务到电机”的故事；
2. **概念没有“归属”**：读者不知道每个概念属于哪个进程/模块、谁拥有、谁不能做；
3. **多维概念混在一起**：进程/线程、领域对象、控制模式、执行机制、行为角色、所有权、安全状态是不同维度，但文档平铺；
4. **图没有“读图说明”**：时序图没有参与者、时间轴、每条箭头的含义、失败分支；
5. **配置只有碎片**：没有“一个完整 Action 的全套文件”示例，读者不知道文件之间怎么引用；
6. **HAL/Lease 没有物理/权限类比**：读者不知道 HAL 是“翻译+执行+保护”，Lease 是“钥匙”；
7. **没有最小心智模型**：没有 5 个盒子能让人先背下来，再挂细节；
8. **没有“同一个例子贯穿”**：站立、跟随、变形、急停各讲各的，读者无法形成连续剧情。

**输出要求**：这一页要让我点头：“对，我就是卡在这里。”

---

## 3. 统一用一个 Running Example 串到底

整份任务统一用这条故事线，不要每个章节换例子：

> **场景**：机器人上电（未知姿态）→ 任务下发“站起来”→ 四足站立 → “跟我走”→ 四轮跟随 → “转成双足讲解”→ Q2B → 双足平衡 + 手势 → “回四足”→ B2Q → 途中突然急停 → 复位/恢复。

每个概念都要回答：**在这个故事里，它出现在哪一步、输入什么、输出什么、失败会怎样。**

---

## 4. 交付物 1：`01_BIG_PICTURE.md`（第一个输出）

目标：一个非软件背景的人读完，能用 2 分钟把架构讲给另一个非软件背景的人听。

必须包含：

### 4.1 一页故事

用 5 个场景把 Running Example 串起来：上电/站立/跟随/变形/急停。每个场景 3–5 句，标出“谁→谁”。

### 4.2 一张主图（必须能背）

五层 + 四流 + 三时钟 + 一条铁律：

```text
意图/权限层：Task / Nav / Safety / Session / ControlLease
        ↓
编排层：Gateway / PolicyManager / ActionGraph / ActionBundle
        ↓
计算层：Worker / ObservationBuilder / Runner / Inference / ActionCodec
        ↓
实时执行层：mc_rt / Snapshot / VelocityArbiter / SwitchCoordinator / JointMux / OutputGuard
        ↓
设备层：HAL / 电机 / 轮 / IMU

四流：Action 流、Velocity 流、Feedback 流、Safety 流
三时钟：100 Hz（Worker）、200 Hz（RT）、1 kHz（HAL/驱动）
铁律：只有 mc_rt 能正常写 HAL；其他模块只能给候选/许可/约束
```

图要标出每条线的方向、频率、失败行为。

### 4.3 概念地图

把以下词画成一张“谁连谁”的图（不要只列清单）：

`Behavior / Action / ActionBundle / Runner / RunnerManifest / ExecutionKind / BehaviorRole / ObsSpec / ActionSpec / PolicyManager / ActionGraph / Gateway / Worker / mc_rt / mc_safety / HAL / ControlLease / SafetyLease / Session / ActionEpoch / Snapshot / JointMux / OutputGuard / Golden / 黑匣子`

每个节点用一句话标“它回答什么问题”。

### 4.4 责任矩阵

| 模块/角色 | 它负责 | 它不能做 | 它失败时谁兜底 |
|---|---|---|---|

至少覆盖 Gateway、Worker、RT、Safety、HAL、平台 Safety、Task/Nav。

### 4.5 一条请求的生命周期

从“任务下发站起来”到“电机收到命令”，编号 10–15 步；每步写：

- 谁（进程/线程）
- 输入/输出
- 关键数据结构
- 失败/超时会怎样

### 4.6 四把钥匙

用“钥匙”类比讲清楚：

1. `Session`：你是谁；
2. `ControlLease`：现在谁拥有这个运动资源；
3. `SafetyLease`：现在允许不允许动；
4. `HAL writer lease`：现在谁有权写设备。

说明每把钥匙由谁签发、在哪检查、过期会怎样、为什么不能合并成一把。

### 4.7 最小心智模型

给一个“5 个盒子”的版本，让我能背下来：

```text
任务/导航/安全 → Gateway 编排 → Worker 计算 → RT 唯一出口 → HAL 执行
```

每个盒子一句话。

### 4.8 术语表（白话版）

每个词固定 5 行：

- 一句话是什么
- 为什么需要（没有它会怎样）
- 它不是什么（常见误解）
- 一个具体例子
- 在全文哪一节/哪个模块

### 4.9 阅读路径

把“大图景”的每个概念映射到 Part1–Part6/附录 A/B/C；告诉我“先读哪 3 节，能最快建立整体感”。

---

## 5. 交付物 2：`02_CONCEPT_DEEP_DIVE.md`（逐个讲透）

每个概念用固定模板：

```text
### 概念名
1. 一句话定义
2. 为什么需要（没有它会怎样）
3. 它不是什么（常见误解）
4. 一个具体例子（带数字/时序/失败）
5. 它在链路中的位置（上游/下游/谁调用它）
6. 谁拥有/谁不能做
7. 失败模式与兜底
8. 对应文档章节
9. 自测 3 问
```

**必须覆盖（这是我的原问题）**：

1. **HAL 到底是什么**：HAL vs 驱动 vs `mc_rt` vs 电机；它翻译什么、保护什么、不能做什么；为什么它是“唯一出口”的最后一道。
2. **D1.3 逻辑模块图**：逻辑模块 ≠ 进程/线程；给“模块→进程/线程→输入/输出→不负责”的映射表；给一条调用链。
3. **五个限界上下文**：不要只讲 DDD。用“五个责任区/五个部门”解释；每个区管什么、不管什么、交接什么；用一个请求穿过五个区的例子。
4. **ControlLease 的位置**：与 Session、SafetyLease、HAL writer lease 的区别；在 Gateway/RT/Safety 哪里检查；过期/抢占/失联的具体流程；为什么不能只靠优先级。
5. **RunnerManifest 是什么**：用“身份证 + 菜谱 + 安全守卫 + 验收单”类比；逐字段注释一个完整例子；缺字段会怎样；它和 ActionBundle、RobotDescription、ObsSpec/ActionSpec、Golden 的关系。
6. **八类 Runner vs `ExecutionKind × BehaviorRole`**：
   - 为什么“8 类”不是“4×6=24 种实现”；
   - 二维矩阵怎么读；
   - 给一张“场景→BehaviorRole→ExecutionKind→class→backend→为什么”的表；
   - 逐个说明八类分别用于什么场景（站立、四轮、Q2B、双足平衡、姿态、恢复、播放、手势）；
   - 指出哪些类名是“角色”，哪些是“实现机制”，为什么容易误解。
7. **D3.7 三条关键时序**：
   - 每条给“参与者表 + 时间轴 + 逐箭头解释 + 失败分支”；
   - 给“6 步读图法”；
   - 说明 100 Hz/200 Hz/1 kHz 在图上怎么体现；
   - 标出 `can_exit` pre-step READY 竞态在时序上的位置（这是已知 P0，不要假装没有）。
8. **mc_rt / worker / gateway / safety / HAL 是什么**：
   - 用“前台/后厨/传菜口/安全员/司机”之类类比；
   - 给进程/线程/周期/职责/不能做什么/失败谁兜底表；
   - 给一个 10 ms + 5 ms 的同一时间轴。
9. **D9.1 四级配置**：
   - 每层回答什么问题、谁签发、谁加载、失败会怎样；
   - 给完整文件树；
   - 给“一个 `quad_stop` Action 的全套文件”示例：RobotDescription、ActionGraph、Bundle、Manifest、ObsSpec、ActionSpec、model、golden、release_manifest；
   - 说明加载顺序和引用关系；
   - 标出哪些是示例/占位、哪些必须签发。
10. **其他你认为我需要的概念**：ActionBundle、ActionGraph、ObsSpec/ActionSpec、ActionEpoch、Snapshot、JointMux、OutputGuard、Golden、黑匣子、SIL/HIL、`switch_ready`、`Form=UNKNOWN`、`SafetyLease` 等。

每个概念至少配一张小图/表/例子；不要只写定义。

---

## 6. 交付物 3：`03_PART_ENRICHMENT/Part1..Part6.md`

目的：把“大图景/概念解释”沉淀回每个 Part，但不重写全文。

每个 Part 增加：

1. **本 Part 在全局中的位置**（1 段 + 1 张小图）；
2. **3–5 个“解释盒”**，每个用“为什么/是什么/不是什么/例子/常见误解”；
3. **1 张“本 Part 概念关系图”**；
4. **1 条端到端小故事**（用 Running Example 的对应场景）；
5. **关键表加“怎么读”说明**（先看哪列、哪些是建议值、哪些是阻断项）；
6. **术语首次出现加一句白话**；
7. **每节末尾 3 个自测问题**。

**重点丰富**：

- D1.3 逻辑模块：模块→进程/线程→输入/输出→不负责；
- D3.3/D3.4：八类 Runner 场景表；
- D3.7：三条时序逐步注解；
- D9.1：完整配置包；
- ControlLease/Manifest/HAL 的图示。

**形式（必须可直接融合）**：不要重写整章；每个新增块用下面的 patch 头，后面接可直接粘贴的 Markdown：

```markdown
<!-- TARGET: 05_GPT架构评审/output/20261122_v1.1/merged/Part2_D3-D4_Runner框架_PolicyManager.md -->
<!-- ANCHOR: ### D3.3 八类 Runner 与二维工厂（V1.1） -->
<!-- MODE: insert-after -->
<!-- BLOCK_ID: P2-D3.3-EXPLAIN-01 -->

（这里放可直接插入的正文/表格/图）
```

- `MODE` 只能是 `insert-before / insert-after / replace-section`；
- `ANCHOR` 必须是目标文件里真实存在的标题或唯一字符串；
- 每个 block 要能独立粘贴，不依赖上下文；不要改 V1.1 决策；
- 同一目标不要拆成多个互相依赖的碎片；如果必须拆，用 `BLOCK_ID-1/2` 并在 `05_INTEGRATION_GUIDE.md` 写合并顺序。

---

## 7. 交付物 4：`04_ARCHITECTURE_REVIEW.html`（独立单文件 Deck，不并入报告）

> **独立交付**：这份 HTML 是给你站在会议室里讲的演示，不是报告的一章。  
> 它必须能单独双击打开、单独讲完；不依赖报告里的相对链接、图片、CSS 或附件。  
> 报告融合包里不收录 HTML 正文，只在 `00_START_HERE.md` 里登记“另有独立 Deck”。

面向：软件同事（不一定懂运控，但懂软件）。目标：你能用这套 deck 讲 30 分钟，并回答追问。

### 7.1 形式要求

- **单文件 HTML**，自包含：无外部 CDN、无外部字体、无外部图片；图用 inline SVG/CSS。
- 16:9，响应式；专业、干净、高对比度，不要“AI 风大渐变”。
- 键盘：←/→/空格翻页，Home/End，`O` 总览，`F` 全屏，`P` 打印/导出 PDF，`N` 显示/隐藏 speaker notes。
- 页码/进度条；打印 CSS 一页一屏。
- 代码片段 ≤15 行；不要大段 C++。
- 中文排版：系统字体栈，正文 ≥20px（投影可读）。

### 7.2 页数与故事线

24–30 页，建议：

1. 封面：一句话 + 目标
2. 先看大图：五层 + 四流 + 三时钟 + 一条铁律
3. 为什么需要这套架构（约束/风险）
4. 系统上下文：任务/导航/安全/云
5. 四进程 + 唯一 writer
6. 三时钟：100/200/1000 Hz
7. 领域模型：Behavior→Action→Bundle→Runner
8. 五个责任区（bounded contexts）
9. RunnerManifest：身份证+菜谱+安全守卫
10. 八类 Runner vs 二维矩阵（场景表）
11. 一拍数据链路：Snapshot→Obs→Inference→Codec→Mux→Guard→HAL
12. 三条关键时序之一：正常一拍
13. 三条关键时序之二：Q2B 切换
14. 三条关键时序之三：急停/反馈过期
15. 四把钥匙：Session/ControlLease/SafetyLease/HAL writer
16. HAL 边界：翻译、执行、保护
17. 安全分层 + INIT/UNKNOWN + 状态机
18. 四级配置 + 一个完整 Action 包
19. Golden / 黑匣子 / 回放
20. 测试/HIL/开放边
21. 路线图 P0–P5
22. 风险与未决（谁补什么）
23. 评审决策页：需要拍板什么
24. Q&A / 附录入口

附录（可按 `A` 键或最后一页链接）：术语表、8 Runner 场景表、配置包文件树、三条时序的逐步注解、已知 P0/P1。

### 7.3 每页结构

- 标题 + 一句 key message；
- 一张主图/表（不要堆字）；
- 2–5 条 bullet（每条 ≤20 字）；
- speaker notes（`N` 键显示）：2–5 句，含“如果被问 X，这样答”；
- 页脚：章节 / 页码。

### 7.4 必须包含的图

- 五层主图；
- 四进程/线程图；
- 概念地图；
- 八类 Runner 二维矩阵；
- 10 ms/5 ms 同一时间轴；
- Q2B/B2Q 阶段；
- 四把钥匙；
- HAL 边界；
- 安全状态机（含 INIT）；
- 四级配置树；
- 路线图。

### 7.5 讲法

最后给三套讲法：

- **5 分钟**：只讲大图 + 四把钥匙 + 一个风险；
- **15 分钟**：大图 + Runner + 数据链 + 安全；
- **30 分钟**：完整故事线 + 配置/测试/路线图 + Q&A。

### 7.6 独立 Deck 的边界（必须遵守）

- 不引用 `../merged/...`、`Part*.md` 等本地相对路径；所有图、表、代码、术语都在 HTML 内自包含。
- 不把 HTML 当成“报告的附录”；它是**另一套叙述**，可以更精简、更口语、更强调“大图景→场景→决策”。
- 可以在封面/页脚写“依据 V1.1 架构设计”，但不要放需要联网/需要另开文件的链接。
- 打印/PDF 必须一页一屏；`N` 键 speaker notes 不影响投影。
- 如果 GPT 输出长度不够，HTML 可以分 `PART 1/2` 续写；最终必须能拼成一个完整 `.html` 文件，并在 `MANIFEST.md` 标注“独立交付”。

### 7.7 交付物 5：`05_INTEGRATION_GUIDE.md`（融合指南）

这份文件是给我后续“把交付物并进 V1.1 报告”用的，**只覆盖报告融合包：`01_BIG_PICTURE`、`02_CONCEPT_DEEP_DIVE`、`03_PART_ENRICHMENT/Part1..6`、`06_SELF_CHECK`；`04_ARCHITECTURE_REVIEW.html` 是独立演示，不进入本指南的融合清单。**

必须包含：

1. **文件级映射**：每个新增/修改块 → 目标文件 → 目标章节 → `insert-before/after` 或 `replace-section`；
2. **依赖顺序**：先插哪个、后插哪个；哪些块会改变后续章节编号；
3. **冲突清单**：与 V1.1 原文重复/冲突的段落，标明“以谁为准”；
4. **变更标记**：建议用 `[V1.2-解释]`/`[V1.2-图]`/`[V1.2-审阅注记]` 三种标记，方便我合并后能看出新增内容；
5. **回滚方式**：如果某块不合适，如何删除/替换；
6. **验收清单**：合并后要检查的链接、术语、图号、表号、数字一致性；
7. **HTML 登记项**：只写“独立 Deck 文件名 + 建议在报告中引用的一句话”，不要把 HTML 正文/样式/脚本写进指南。

### 7.8 交付物 6：`06_SELF_CHECK.md`（自检）

- 按 §9 rubric 自评，每项给分数与证据；
- 列出“没做到/有假设/需要我确认”的项；
- 列出 10 个最容易被软件同事追问的问题，并给一句话答案；
- 明确 conclusion：`可讲解 / 可评审 / 可编码 / 不可上机`。

### 7.9 交付文件包结构（必须按此命名）

```text
A. 报告融合包（可并入 V1.1 报告）
00_START_HERE.md
01_BIG_PICTURE.md
02_CONCEPT_DEEP_DIVE.md
03_PART_ENRICHMENT/
  Part1_D0-D2.md
  Part2_D3-D4.md
  Part3_D5-D6.md
  Part4_D7-D8.md
  Part5_D9-D12.md
  Part6_D13-D16.md
05_INTEGRATION_GUIDE.md
06_SELF_CHECK.md
MANIFEST.md

B. 独立演示（不并入报告）
04_ARCHITECTURE_REVIEW.html
```

`00_START_HERE.md` 用 1 页说明“A/B 两套产物、先读什么、每个文件解决什么、哪些是解释、哪些是修改建议、HTML 是单独演示”。

`MANIFEST.md` 必须把 A/B 分开列，并给每个文件标 `merge: yes/no`。

---

## 8. 输出顺序（一次性完成，不等待确认）

**一次性完成全部交付物，不要停在 Stage 1 等确认。** 按下面顺序连续输出；每个文件用独立代码块，块首写 `FILE: <路径>`，方便我保存和后续融合。

**A. 报告融合包（要能直接并入 V1.1）**

1. `00_START_HERE.md`
2. `01_BIG_PICTURE.md`
3. `02_CONCEPT_DEEP_DIVE.md`
4. `03_PART_ENRICHMENT/Part1_D0-D2.md`
5. `03_PART_ENRICHMENT/Part2_D3-D4.md`
6. `03_PART_ENRICHMENT/Part3_D5-D6.md`
7. `03_PART_ENRICHMENT/Part4_D7-D8.md`
8. `03_PART_ENRICHMENT/Part5_D9-D12.md`
9. `03_PART_ENRICHMENT/Part6_D13-D16.md`
10. `05_INTEGRATION_GUIDE.md`
11. `06_SELF_CHECK.md`
12. `MANIFEST.md`

**B. 独立演示（不并入报告）**

13. `04_ARCHITECTURE_REVIEW.html`

### 8.1 输出格式

每个 Markdown 文件：

````text
FILE: 01_BIG_PICTURE.md
```markdown
（全文）
```
````

HTML 文件：

````text
FILE: 04_ARCHITECTURE_REVIEW.html
```html
（完整 HTML）
```
````

### 8.2 长度不够时怎么续写

如果单条消息无法容纳全部内容：

- 不要压缩成提纲，也不要删掉后面的文件；
- 在当前文件处停下，写明 `CONTINUE: <文件名> from <章节/行号>`；
- 下一条消息从该文件该位置继续，**不要重写已输出部分**；
- 保持文件编号/文件名/结构不变；
- 全部完成后给 `MANIFEST.md` 和 `06_SELF_CHECK.md`。

### 8.3 完成度声明

每个文件末尾写：

```text
完成度：xx%
未完成/假设：...
```

全部结束时写一段总声明：

```text
交付物：13/13
可讲解：是/否
可评审：是/否
可编码：是/否
可上机：否（任何情况下都不应写“是”）
```

如果信息不足，做最合理假设并标注，不要停下来问一堆问题。

---

## 9. 质量 rubric（100 分）

| 维度 | 分值 | 判定 |
|---|---:|---|
| 大图景能背（5 层/四流/三时钟/一条铁律） | 15 | 2 分钟能复述 |
| 每个概念有“是什么/为什么/不是什么/例子/在哪” | 20 | 缺一项扣 2 分 |
| 八类 Runner 场景表能回答“这个动作用哪个” | 10 | 8 个场景都能唯一映射 |
| 三条时序能逐步讲 | 10 | 参与者/箭头/失败分支齐全 |
| 四级配置能落地 | 10 | 一个完整 Action 包文件树+引用 |
| Part 细化能插入原文 | 10 | 有位置+可粘贴段落 |
| Deck 能 30 分钟讲完、非软件同事能听懂 | 15 | 图/表/notes 齐全 |
| 不改架构决策、矛盾标注 | 5 | 无静默改 |
| 可读性/中文表达 | 5 | 白话、类比、无 jargon 堆砌 |

> 注：`04_ARCHITECTURE_REVIEW.html` 按“独立演示”评分，不要求它引用报告、也不要求报告能反向嵌入它；只要求它能单独打开、单独讲 30 分钟。

---

## 10. 禁止

- 禁止只给“更长的定义”，不给例子/图/失败模式。
- 禁止把 DDD/实时系统术语直接丢给我，不解释。
- 禁止把 8 类 Runner 讲成“8 个算法”或“24 种实现”；先把二维矩阵讲清楚。
- 禁止把 `ControlLease`、`SafetyLease`、`Session`、`HAL writer` 混成“一个许可”。
- 禁止把 `can_exit` pre-step READY 竞态说成已解决；它仍是 P0。
- 禁止用外部 CDN/图片做 HTML；必须单文件可离线打开。
- 禁止把 HTML 当“报告的一章”或塞进 `05_INTEGRATION_GUIDE.md` 的融合清单；它是独立演示。
- 禁止改 V1.1 的架构决策；有问题用 `[审阅注记]`。

---

## 11. 开始

现在按 §8 的顺序**一次性完成全部 13 个交付物**，并明确分成两套：

**A. 报告融合包**（要能直接并入 V1.1 报告）

1. 根因诊断（放在 `00_START_HERE.md` 或 `01_BIG_PICTURE.md` 开头）；
2. `01_BIG_PICTURE.md` 全文；
3. `02_CONCEPT_DEEP_DIVE.md` 全文；
4. `03_PART_ENRICHMENT/Part1..Part6` 六个 patch 文件；
5. `05_INTEGRATION_GUIDE.md`；
6. `06_SELF_CHECK.md`；
7. `MANIFEST.md`。

**B. 独立演示**（不并入报告）

8. `04_ARCHITECTURE_REVIEW.html` 完整单文件。

不要等确认，不要先提问；信息不足时做最合理假设并标注。  
如果长度不够，按 §8.2 续写，不要删减后面的交付物。  
**HTML 是单独交付：不要把它写进 `05_INTEGRATION_GUIDE.md` 的融合清单，也不要让报告依赖它。**
