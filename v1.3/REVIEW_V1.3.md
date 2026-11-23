# 评审意见：V1.3 50 Hz 频率修订

**对象**：V1.2 讲解合并版 → V1.3 50 Hz 修订  
**依据**：[ADR-25](ADR-25_策略频率50Hz.md)、训练 `dt=0.02`、T1 100 Hz 实证  
**结论**：频率基线已统一为 **50 Hz 策略 / 50 Hz Worker / 200 Hz RT / ZOH / 15/20 ms / 25 ms TTL**；T1 100 Hz 证据保留；P0 未修，不能上机。

---

## 1. 本版做了什么

| 项 | V1.2 | V1.3 |
|---|---:|---:|
| 策略推理 | 100 Hz / 10 ms | **50 Hz / 20 ms** |
| Worker | 100 Hz / 10 ms | **50 Hz / 20 ms** |
| Worker 预算 | 7.6 / 10 ms | **15 / 20 ms** |
| `can_exit` `valid_until` | 10 ms | **25 ms** |
| `snapshot_seq` 差 | ≤2 | **≤4** |
| 候选 deadline | tick+8 ms | **tick+15 ms** |
| `max_hold` | 10 ms | **25 ms** |
| RT | 200 Hz | **200 Hz，ZOH** |
| 黑匣子 Worker | 100 Hz / 819200 B/s | **50 Hz / 409600 B/s** |
| 黑匣子总量 | 870400 B/s | **460800 B/s** |

**没有改**：T1 的 100 Hz、≈196 Hz 发布、WBC 10.5 ms；`mc_safety` 100 Hz；SafetyLease 30 ms；HAL 15 ms；PD 1 kHz；RT 200 Hz。

---

## 2. 为什么是 Worker 50 Hz

训练 `dt=0.02`，一个策略步 20 ms。Worker 100 Hz 只会：

- 多出 10 ms 空转；
- 让观测/历史按 10 ms 更新，与训练 20 ms 不一致；
- 让读者误以为策略是 100 Hz。

所以首版 Worker 50 Hz；未来 100 Hz 策略再把 `period_ms=10`、Worker 100 Hz。多 Runner 混频才用“100 Hz 基 tick + due 计数器”。

---

## 3. RT 200 Hz 是保持，不是插值

```text
策略：  q0            q1            q2
RT：    q0 q0 q0 q0   q1 q1 q1 q1   q2 ...
        └─ 4 个 5ms tick = ZOH ─┘
```

- 训练侧 action 保持 20 ms，部署用 ZOH 与训练一致；
- 200 Hz 仍每 5 ms 检查 SafetyLease/Epoch/候选年龄/Guard/HAL；
- 插值只能作为 `ActionCodec/ReferenceShaper` 的显式设计，经训练/HIL 验证；不是默认；
- T1 的 ≈196 Hz 发布也是 ZOH，不是 50→100 插值。

---

## 4. 已改的文件

| 文件 | 改动 |
|---|---|
| `00_导读` / 全文 | 五层 50 Hz、20 ms、50/200/1k；新增 V1.3 频率横幅 |
| Part1 | 进程表/时序表/ADR-05：50 Hz；候选 tick+15 ms |
| Part2 | `can_exit` 15 ms、TTL 25 ms、`snapshot_seq` 4、`on_20ms_tick` |
| Part3 | D5.7 标题/预算 15/20 ms；Model ≤12；5 ms 裕量；15 ms Worker |
| Part4 | Worker 20 ms/50 Hz；超 15 ms；15/20 ms、5 ms 裕量 |
| Part5 | 黑匣子 50 Hz、409600 B/s、460800 B/s、17.58 MiB/40 s |
| Part6 | ADR-05/ADR-25：50 Hz + ZOH |
| Appendix B | `ExitDecision` 序差≤4、年龄≤25 ms；黑匣子预算 |
| Appendix D | Worker/时序/Manifest 示例改 50 Hz/20 ms/15 ms |
| Appendix E | 重写为 V1.3 频率自检 |
| Deck | 19 页版第 2/3/4/9/10 页改 50 Hz/20 ms/15 ms |

---

## 5. 仍然存在的风险

1. **P0 `can_exit` pre-step READY**：未修；50 Hz 把窗口从 10 ms 放大到 20 ms，切换前必须先修。
2. **50 Hz WCET**：15/20 ms 是目标，不是实测；模型+obs+codec 必须在目标平台测。
3. **ZOH 跟踪**：4:1 保持对接触/力矩的影响未做 HIL；位置目标通常可接受，力矩/速度另评。
4. **T1 vs Collie**：T1 100 Hz、10.5 ms WBC 是 T1 事实；Collie 50 Hz 不是“T1 降频”，而是训练频率对齐。
5. **不能上机**：拓扑/双足/Q2B/HAL watchdog/WCET/功能安全/密钥未签收；36/36 不是 HIL。

---

## 6. 结论

**V1.3 频率口径一致、可评审、可拆编码任务；P0/HIL 未闭环，不能上机。**  
下一步：先修 `can_exit`，再做 50 Hz 的 WCET 与 ZOH HIL；之后才考虑 100 Hz 策略。
