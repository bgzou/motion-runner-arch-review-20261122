<!-- BEGIN_V12: APPENDIX-SELF-CHECK -->
# 附录 E：V1.3 频率修订自检

> 只记录 V1.3 的频率/文档一致性，不是 V1.1 架构或实机安全评分。

## 1. 已改

- 策略推理：100→50 Hz，`period_ms=20`；
- Worker：10→20 ms，预算 7.6/10→15/20 ms；
- `can_exit`：10→25 ms，`snapshot_seq` 差 2→4；
- 候选 deadline：tick+8→tick+15 ms；`max_hold` 10→25 ms；
- 黑匣子：Worker 100→50 Hz，819200→409600 B/s；
- Deck：19 页版按 50 Hz/20 ms 重画第 2/3/4/9/10 页；
- 全文 6 个 Part + 附录 D 的 100/10/7.6 已同步。

## 2. 未改

- T1 的 100 Hz、196 Hz 发布、WBC 10.5 ms 是 T1 实证，保留对照；
- `mc_safety` 100 Hz、SafetyLease 30 ms、HAL 15 ms、PD 1 kHz 不变；
- `can_exit` pre-step READY 的 P0 没有因为改频率而修复；
- 36/36 仍是 SIL/合同/Schema/文本检查，不是 HIL。

## 3. 残留与阻断

| 事项 | 状态 | 下一步 |
|---|---|---|
| `can_exit` P0 | 50 Hz 把窗口从 10 ms 放大到 20 ms | 先修 READY 发布顺序/完成序号，再开放切换 |
| 50 Hz 模型 WCET | 预算 15/20 ms 是目标 | 在目标平台测 obs+model+codec |
| ZOH 保持 | 默认保持，不插值 | HIL 验证 4:1 保持的跟踪/舒适性 |
| HAL watchdog/双足/Q2B | 未签收 | 不能上机 |

## 4. 结论

**V1.3 的频率基线可评审、可拆编码任务；P0/HIL 未闭环，不能上机。**
<!-- END_V12: APPENDIX-SELF-CHECK -->
