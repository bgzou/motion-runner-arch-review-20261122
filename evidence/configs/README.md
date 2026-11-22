# T1 real-machine configs

| File | What to read |
|---|---|
| `action_setting.yaml` | Action → 执行组 → runner/cfg/period/priority |
| `action_ruler.yaml` | 合法切换边与出口 |
| `action_state.yaml` | Action 状态定义 |
| `mc_T1.yaml` | 话题/服务/速度源优先级/TTL/发布频率 |
| `motion_list.yaml` | MIMIC/ANIMATION 动作资源 |
| `robot_model.yaml` | 关节名/限位/模型元数据 |
| `security_guard.yaml` | 安全看护配置 |
| `rl_quad_walk.yaml` | 四足行走 obs/act/增益/后处理 |
| `rl_quad_to_bi_run.yaml` | Q2B 过渡策略 |
| `rl_bi_wbc_run.yaml` | 双足 WBC |
| `rl_quad_walk_terrain.yaml` | 地形行走 |
| `rl_quad_recovery.yaml` | 恢复策略 |

> 这些是 T1 `qd1_t2d0` 的部署态配置，只用于对标结构与量级；数值不可直接用于 Collie。
