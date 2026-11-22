# 启动 Prompt（GitHub 在线版）

> 现在 V1.1 合并版、评审、任务书都已传到 GitHub。  
> 用法：把下面“聊天框里发的话”整段发给网页版 GPT；不需要先上传附件（除非 GitHub 打不开）。

## 在线入口

**https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/00_READ_ME_FIRST.md**

## 聊天框里发的话（直接复制）

```text
请先打开并阅读这个 GitHub 入口页：
https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/00_READ_ME_FIRST.md

然后严格按其中的任务书执行：
https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/PROMPT_FOR_GPT_V1.2_ALL_IN_ONE.md

必读输入：
- V1.1 合并全文：https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Full_D0-D16.md
- HAL 合同：https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Appendix_A_HAL_Contract.md
- Schema Canon：https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/Appendix_B_Schema_Canon.md
- 评审意见（已知 P0/P1）：https://github.com/bgzou/motion-runner-arch-review-20261122/blob/main/v1.1/REVIEW_V1.1.md

任务要求：
- 一次性完成全部 13 个交付物，不要分 Stage，不要停在 Stage 1 等确认。
- 交付物分两套：
  A. 报告融合包：00_START_HERE、01_BIG_PICTURE、02_CONCEPT_DEEP_DIVE、03_PART_ENRICHMENT/Part1–6、05_INTEGRATION_GUIDE、06_SELF_CHECK、MANIFEST。这些要能直接融合进 V1.1 报告。
  B. 独立演示：04_ARCHITECTURE_REVIEW.html。单独打开、单独讲，不并入报告，不引用报告路径/图片/附件。
- 每个文件用 `FILE: <路径>` 开头；Part 细化必须用 `TARGET / ANCHOR / MODE / BLOCK_ID` 的 patch 头，能直接插入或替换 V1.1 合并版。
- 如果单条消息长度不够，按任务书 §8.2 续写；保持文件名/结构不变，不能删减后面的交付物。
- 最后给 MANIFEST 和 06_SELF_CHECK，明确写：交付物 13/13、可讲解/可评审/可编码/不可上机。

我的背景：我不是软件设计出身，最怕“每个概念单看有道理，但连不起来”。所以请先用 Running Example 把大图景串起来，再逐概念讲透，最后做独立 HTML Deck。不要只给更长的定义，要给“是什么/为什么/不是什么/具体例子/失败会怎样”。

现在开始，不要先提问；信息不足时做最合理假设并标注。
```

## 如果 GPT 说 GitHub 打不开

补一句：

```text
如果 GitHub 链接打不开，请先告诉我缺哪个文件，不要猜内容；我可以把对应 .md 原文粘贴给你。
```

## 收到结果后先验收 3 项

1. `01_BIG_PICTURE.md` 能不能 2 分钟讲完；
2. `03_PART_ENRICHMENT/Part2_D3-D4.md` 的八类 Runner 场景表是否每个场景都能唯一映射；
3. `04_ARCHITECTURE_REVIEW.html` 能否直接双击打开、按 `N` 看 speaker notes。
