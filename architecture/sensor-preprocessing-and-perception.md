# 第 6 章 特性域 B：传感器数据预处理与通用感知服务

| 项 | 内容 |
|---|---|
| 所属文档 | QDOG-SFS-001《四足狗软件特性设计说明书》（见 [README](./README.md)） |
| 章节版本 | V0.7（草案，2026-11-19；接口前缀 `/qdog/`→`/robot/` 并回靠 T1 命名——IF-SP-05 改 `set_camera_stream`/`set_tof_stream` 双服务、IF-SP-08 `targets`→`target_info`、消息包 qdog_msgs→robot_msgs） |
| 域码 | SP（Sensor preprocessing & Perception services） |
| 证据基线 | 启元 T1 Pro（备份 SKU=T1-2X，固件 qy2501_2_v2d2-soc0-v1.0.0.5-R）；EV 条目见 §6.10 与主控文档 §5 |

## 版本表

| 版本 | 日期 | 变更摘要 | 作者 |
|---|---|---|---|
| V0.1 | 2026-11-10 | 首版：需求条目、T1 Pro 对标实证分析、设计方案、设计决策、验证考虑 | liqiliang |
| V0.2 | 2026-11-10 | 新增 §6.6 功能、规格与工作量分析；原 §6.6–6.9 顺延为 §6.7–6.10；新增 OP-SP-07 与 EV-T1P-61 | liqiliang |
| V0.3 | 2026-11-11 | §6.6.3 对照表完善：列名「功能简称」改「功能名称」，新增「功能简介」列；参考实现列改为两行式（上行 T1 Pro 是否提供开源实现、下行业界开源实现），全部开源实现附仓库地址（地址均经在线核实） | liqiliang |
| V0.4 | 2026-11-11 | 新增 §6.6.5 端到端场景走查（SP 视角，完整走查见第 5 章 §5.6.5） | liqiliang |
| V0.5 | 2026-11-12 | **感知服务归属调整（暂定）：平台 → 小脑**（第 3 章 OP-ARCH-05 修订）。§6.1.1/§6.3.1 增归属声明；FR-SP-09/10/11 主语由「平台」改为「SP 域（感知服务类，归小脑·暂定）」；图 6-1 SVC 层与职责矩阵标注归属；预处理类条目（FR-SP-01~08/13/14）归属平台不变；部署视图不变（感知板） | liqiliang |
| V0.6 | 2026-11-19 | 代码量单位统一为 K LoC：§6.9 对照表/汇总「N~Mk 行」→「N~M K LoC」、「约 N~M 万行」→「约 N×10~M×10 K LoC」（20 处），数值不变 | liqiliang |

---

## 6.1 特性域概述

### 6.1.1 范围

本章规定传感器数据从**硬件采集**到**算法就绪输入**之间的全部公共加工，以及在此之上沉淀的**通用感知服务**：

> **子系统归属声明（2026-11-12 调整，暂定）**：本特性域（SP）的交付物跨两个子系统——**传感器数据预处理归平台子系统**（数据就绪供给）；**通用感知服务归小脑子系统（暂定）**（目标/点云/代价图/感知场景等结果级能力，OP-ARCH-05 修订，见第 3 章 §3.10）。部署视图不变：两者同在感知算力板（单板机型同板）。本章以下内容为设计基线，子系统归属的变更不影响接口与管线设计。

1. **传感器数据预处理**：格式转换、去畸变、缩放、旋转、深度→点云、点云/图像滤波、时间同步与时间戳、坐标变换与标定加载、质量监控、零拷贝传输。
2. **通用感知服务**：以统一服务面向外的结果级能力——融合避障查询、目标检测/跟踪、语义理解（室内外/可通行性/楼梯）、局部代价图、本体里程计（IMU+关节状态融合）、感知场景编排（能力组合启停）。

不在本章范围：检测/分割/融合的算法原理（归算法规格书）、导航规划（NV 章）、语音交互语义（VI 章；但音频**前端预处理**（AEC/VAD/波束）作为传感预处理的一员纳入本章约束）、传感供电的业务策略（TS 章资源场景，本章只提供执行接口）。

### 6.1.2 价值与用户场景

| 干系人 | 场景 | 价值 |
|---|---|---|
| 用户 | 昏暗走廊里跟随不丢失；镜头被泥点遮挡时机器人自知「看不清」并降速 | 质量随流+降级联动，能力与状态一致 |
| 用户 | 换了一颗左目相机模组（维修换件），标定文件更新后全部算法立即一致生效 | 标定唯一权威，杜绝多处配置漂移 |
| 开发者 | 新增「垃圾分类识别」算法：声明模型输入（尺寸/归一化/letterbox）与所需数据流，直接获得就绪图像流与同步点云 | 预处理公共服务，接入零重复开发 |
| 开发者/测试 | 录制一组现场数据，离线回放后各管线输出与实机逐帧一致 | 确定性管线，问题可复现 |
| 产品 | 待机/工作功耗达标：不用 ToF 时真断流，用时毫秒级恢复 | 供电流控与状态联动 |
| 平台 | 双板机型跨板只传结果级数据，带宽实测 <5Mbps；单板入门机型同一套管线裁剪运行 | 传输契约与机型裁剪 |

### 6.1.3 对标定位

T1 Pro 的感知链是「HAL 公共化成功 + 算法侧预处理高度分散」的混合体（§6.4）：其相机/ToF HAL 已把格式转换、去畸变、缩放、点云生成、硬件时间戳、板间同步做成了公共底座（值得直接继承）；但点云滤波在 6 处各自实现、外参在 ≥6 处分散加载、时间同步 6 种策略并存。本章设计=**继承其底座 + 抽取其散落的公共部分**。

---

## 6.2 概念模型与术语

| 术语 | 定义 |
|---|---|
| **传感数据链四层** | L0 采集层（HAL 驱动采集）→ L1 预处理层（公共加工）→ L2 通用感知服务层（结果级能力）→ L3 算法模块层（模型推理与模型特定预处理） |
| **采集侧预处理** | 与传感器硬件强绑定、必须紧贴采集完成的加工（格式转换/去畸变/缩放/旋转/深度→点云/无效点过滤/曝光），在 HAL 内一次完成 |
| **一次转换原则** | 同一几何/格式变换全链只做一次，产出多规格流供多消费者零拷贝共享，禁止各消费者对同一原始流重复做相同变换 |
| **算法侧预处理** | 与模型输入强绑定的加工（letterbox/归一化/NCHW/ReID 尺寸），声明在模型配置中，由算法 runner 执行 |
| **时间基（Time Base）** | 采集时刻的权威时钟语义：硬件时间戳（PWM 触发/fsync/内核单调钟）优先，附 `acquisition_ts / receive_ts` 双时戳 |
| **同步策略** | 多源数据对齐方式三选一（规约见 §6.5.3.3）：新鲜度门控（freshness）、滑窗配对（sync window）、硬件同步（fsync/PWM） |
| **标定数据** | 内参（相机/ToF）、外参（sensor↔base，含形态相关双外参）、一机一档存于受保护区；`calib_server` 为唯一权威发布方 |
| **质量随流** | 数据质量指标（无效点比/曝光水平/遮挡判定/新鲜度/丢帧）作为消息字段随数据流传导，并汇总至健康通道 |
| **感知场景（Perception Scene）** | 感知能力的命名组合（跟随感知场景/避障场景/融合建图场景），BT 编排、tick 驱动、可启停与查询——区别于 TS 域的「资源场景」（档位） |
| **结果不出板契约** | 大带宽原始数据（图像/点云）只在采集板内流动；跨板仅传结果级数据（目标/代价图/状态/指令） |
| **管线（Pipeline）** | 声明式算子链（如点云：ROI→体素→离群→时域确认），一次实现、按配置复用、确定性可回放 |

**本章的概念基石**：预处理不是一个模块，而是**一条分层链**——「公共的往下沉（HAL/中间件），模型的往里收（runner 配置），有状态的独立成服务（EKF 里程计）」。

---

## 6.3 需求与功能点

### 6.3.1 功能需求

> 归属速查：FR-SP-01~08、13、14（预处理/传输/供电流控/裁剪/录制）→ **平台子系统**；FR-SP-09~12（本体融合/感知服务面/感知场景/跨板契约中感知结果输出）→ **小脑子系统（暂定）**。

| 编号 | 需求（规范性表述） | 优先级 |
|---|---|---|
| FR-SP-01 | 平台必须提供统一传感接入框架：各类传感器（RGB 相机/深度·ToF/IMU/关节/BMS/触摸/麦克风阵列/可选激光与鱼眼）以插件接入，输出标准化数据流（统一消息头：硬件时戳、接收时戳、帧序号、质量标记、传感器 ID） | P0 |
| FR-SP-02 | 采集侧预处理必须在 HAL 内一次完成：格式转换（UYVY/RAW→发布格式）、去畸变（LDC，可配焦距缩放）、多档分辨率输出、形态相关旋转、深度→点云生成（内参取自标定服务）；产出多规格流零拷贝分发 | P0 |
| FR-SP-03 | 平台必须统一时间基：采集时戳以硬件时戳为权威（PWM/fsync/内核单调钟），消息携带采集与接收双时戳；多源对齐只允许使用平台提供的同步算子（新鲜度门控/滑窗配对/硬件同步），策略按数据类型在配置中声明 | P0 |
| FR-SP-04 | 标定数据必须统一管理：一机一档存储于受保护区（内参/外参/ToF 专用标定），带版本与校验和；启动时校验、跨板一致性自动校验；以标准话题/参数统一发布；任何模块不得私存标定副本；支持在线观测器（残余误差观测）框架 | P0 |
| FR-SP-05 | 平台必须提供声明式通用点云管线：算子库（ROI 裁剪/高度带/体素降采样/组织点云行列采样/半径与统计离群/距离与高度滤波/重复点去除/时域确认/目标剔除）以配置组合，供全部消费方复用 | P0 |
| FR-SP-06 | 平台应当提供通用图像预处理算子库（几何类：resize/letterbox/旋转/去畸变恢复/颜色空间转换），模型特定参数（归一化均值方差/布局/输入尺寸）声明在模型配置中 | P1 |
| FR-SP-07 | 传感数据质量必须随流监控：无效点比、曝光水平、遮挡判定（含传感器信息一致性）、新鲜度、丢帧率作为数据字段传导，并周期汇总至健康通道（对接 OM 域），支持按阈值产生降级信号 | P0 |
| FR-SP-08 | 平台必须提供传感供电与流控服务：按传感器粒度的电源/出流控制（掩码语义），供系统状态动作与资源场景调用；切换必须幂等且带就绪回报 | P0 |
| FR-SP-09 | SP 域（感知服务类，归小脑·暂定）必须提供本体感知融合服务：IMU+关节状态 EKF 融合输出里程计与躯干位姿（含触地检测、零速修正、运行中静止重标定），输出供导航/跟随/融合消费 | P0 |
| FR-SP-10 | SP 域（感知服务类，归小脑·暂定）必须提供统一感知服务面：定向障碍查询（圆柱/方向/形态参数）、目标列表（检测+跟踪+ReID）、语义理解（室内外/楼梯/可通行性）、局部语义代价图、融合状态——接口统一、QoS 声明、结果级跨板 | P0 |
| FR-SP-11 | SP 域（感知服务类，归小脑·暂定）应当提供感知场景编排：感知能力以场景组合启停（行为树+tick 周期声明），场景状态可查询（运行中/暂停/停止/错误+tick 统计），并与任务/资源场景联动 | P1 |
| FR-SP-12 | 跨板数据契约必须显式：图像与原始点云不得跨板；跨板仅限结果级数据与同步信号；契约以带宽预算（NFR-SP-05）在 CI 中校验 | P0 |
| FR-SP-13 | 预处理与感知配置必须声明式且随机型裁剪：传感器清单、管线配置、场景定义按机型配置文件组合，单板入门机型可裁剪感知功能子集 | P1 |
| FR-SP-14 | 平台可以提供感知数据录制与回放：原始流与管线中间流可录制，回放输出与实机逐帧一致 | P2 |

### 6.3.2 非功能需求

| 编号 | 需求 | 验收准则 | 优先级 |
|---|---|---|---|
| NFR-SP-01 | 相机端到端时延：采集→算法可用输入 ≤ 2 帧周期 | 时戳打点实测分布 | P0 |
| NFR-SP-02 | 障碍查询时延：ObstacleCheck 响应 P99 ≤ 50ms，数据新鲜度 ≤ 1 帧周期 | 服务压测 + 新鲜度断言 | P0 |
| NFR-SP-03 | 里程计：/odom ≥100Hz、躯干位姿 ≥50Hz，硬件时戳误差 ≤1ms | 频率与时戳对齐实测 | P0 |
| NFR-SP-04 | 板内零拷贝：图像/点云自 HAL 至消费者无 CPU 拷贝（dmabuf/共享内存） | 内存带宽实测/代码审查 | P0 |
| NFR-SP-05 | 跨板带宽：业务态 ≤5Mbps（待机更低） | 板间网口流量实测 | P0 |
| NFR-SP-06 | 回放确定性：同一录制输入，各管线输出逐帧一致（时间戳/内容） | CI 回放比对 | P1 |
| NFR-SP-07 | 预处理预算：采集+预处理 CPU ≤1.5 核（感知板口径），GPU/NPU 占用按场景声明并计量 | 资源实测（对标 T1 静置：hal_camera 42.9%+hal_rgbd 38.9% 单核口径 [EV-T1P-59]） | P1 |

---

## 6.4 对标实证分析（启元 T1 Pro）

### 6.4.1 融合感知业务的模块盘点（不止 coreon_fusion）

T1 Pro 上「融合感知」业务由 **8 类模块**共同承担（感知计算全部在 orin 大脑板，本体融合在 rk）：

| # | 模块 | 职责 | 预处理相关内容 | 关键证据 |
|---|---|---|---|---|
| 1 | **coreon_fusion**（/coreon_fusion_ros2_node） | 多源融合避障+感知场景引擎：5×ToF+相机+IMU+UWB → 融合点云/目标/避障状态/速度改写；BT 场景（跟随 100ms/避障 50ms tick） | 配置声明订阅 33 个话题（含跨机型遗留）；传感器路由表+新鲜度门控 0.1s；634 行避障预处理参数；内联 9 组外参+在线俯仰观测器 | [EV-T1P-42][EV-T1P-43][EV-T1P-44][EV-T1P-45][EV-T1P-39] |
| 2 | **percep**（/perception） | 语义分割/室内外判定/楼梯检测/语义局部代价图/双目视差 | 图像校正缩放（→640×480）、双目同步窗 20ms、ToF 去噪（体素+连通+时域）、目标剔除、三层记忆代价图、形态×传感器双外参 | [EV-T1P-49] |
| 3 | **person_track**（target_follow_perception） | 跟随候选检测+ReID 跟踪+深度估计 | GPU resize、合并 remap（resize+去畸变+旋转一次完成）、LDC 恢复、外部内参启动覆盖、letterbox 640×640、近场点云 ROI→体素→离群→DBSCAN、四阶段深度过滤 | [EV-T1P-54] |
| 4 | **brightness_detection** | 亮度门控（过暗禁跟随） | 灰度均值（阈值 82、隔行采样、每 5 帧取 1、确认 1s 防闪烁） | [EV-T1P-55] |
| 5 | **nav2_perception**（pointcloud_combiner+perception_node） | 前+后 ToF 合并、点云过滤 | 合并=TF 变换拼接（无滤波）；过滤=体素 0.1+距离 0.4-3m（统计滤波/拖尾滤波/关节自点云剔除均备而未启用） | [EV-T1P-50] |
| 6 | **legged_odom**（rk） | 足式里程计（/odom、/tf、躯干位姿） | EKF（误差状态）：IMU 500Hz→100Hz、关节 1kHz→250Hz 缓冲、滑动平均、触地检测状态机、bias 上电标定+运行中静止重标定 | [EV-T1P-51] |
| 7 | **aimrt_slam / map_manager / aprilgrid_loc**（orin） | 建图/定位/标定定位 | 图像 resize 640、双目同步容差 3ms、传感器外参内联配置 | [EV-T1P-56] |
| 8 | **音频前端**（rk：audio_manager+agent 侧 SDK） | 采音/回声消除/唤醒 | PipeWire WebRTC AEC、silero VAD（onnx）、DTLN AEC、4 麦波束（讯飞 VTN）、80Hz 高通+7kHz 低通重采样 | [EV-T1P-53] |

其下是公共底座：**hal_camera（双板）**与 **hal_rgbd（orin 数据面/rk 控制面）**、**device_manager**（关节 1kHz/躯干 IMU 500Hz，iceoryx）[EV-T1P-46][EV-T1P-47][EV-T1P-48][EV-T1P-52][EV-T1P-59]。

### 6.4.2 数据预处理的现状：无统一模块，两层观察

**判定：T1 Pro 没有独立的/统一的数据预处理模块。预处理分布在「HAL 内嵌的采集侧公共预处理」与「各算法模块内嵌的算法侧预处理」两层，后者高度重复。**

#### 6.4.2.1 采集侧：HAL 已是事实上的公共预处理层（成功面，值得继承）

| 能力 | T1 Pro 实现（证据） | 公共化程度 |
|---|---|---|
| 图像格式转换+缩放 | orin：UYVY→CUDA LDC 去畸变（fov_scale 0.5）→NvBufSurface/VPI 缩放；rk：UYVY→RGA→NV12（864×648 多档可选）+旋转（狗形态 180°）+OpenCL LDC，dmabuf 池零拷贝 [EV-T1P-48] | **公共**（在 HAL，一次转换多流输出） |
| ToF 深度处理 | V4L2 5 路→厂商 SDK 深度计算→点云；每相机独立滤波 ini（26 项：幅值阈值/飞点角限制/MPI/平滑/自动曝光分位数）+独立 spc 标定 [EV-T1P-46] | **公共**（在 HAL） |
| 硬件时间戳 | ToF 用 PWM 时戳节点（pwm_ts0/1）+绑定触发；相机 fsync；BMI08 400Hz [EV-T1P-46][EV-T1P-48] | **公共**（在 HAL） |
| 板间同步 | `/aima/hal_camera/soc_sync/ready`（相机采集门控）+ `/ofilm/tof/inter_board`（ToF 帧同步）；ToF 控制面（rk I2C 曝光+FSYNC 监测）与数据面（orin）分板协作 [EV-T1P-46][EV-T1P-47] | **公共** |
| 高频本体流 | 关节 1kHz/躯干 IMU 500Hz iceoryx 直连（生产模式不出 DDS）[EV-T1P-52] | **公共**（直连，不过管线——正确） |
| 零拷贝传输 | iceoryx+dmabuf；跨板仅结果级（实测 ≈2Mbps，视频零跨板）[EV-T1P-57][EV-T1P-59] | **公共** |

#### 6.4.2.2 算法侧：同类预处理在各模块重复实现（失败面，需抽取）

| 预处理能力 | T1 Pro 重复实现处（证据 [EV-T1P-56]） |
|---|---|
| **点云去噪/滤波** | ① hal_rgbd 滤波 ini（幅值/飞点/MPI）② coreon_fusion 光心脏污分析（体素 0.015+SVD 判据）③ coreon_fusion fused_obstacle_assist（体素 0.05+去重 0.075）④ percep tof_denoise（体素 0.05+连通分量+时域确认）⑤ nav2 perception_node（体素 0.1+距离/高度滤波）⑥ person_track 近场（体素 0.01+半径离群）——**6 处** |
| **图像 resize/去畸变** | ① hal_camera 双板 LDC ② percep ImageProcess（校正+2.8 倍视角缩放）③ person_track（fx/fy 统一缩放 0.5+LDC 恢复+GPU resize）④ coreon_fusion runner（Decode+Letterbox+NCHW）⑤ aimrt_slam resize 640——**5 处** |
| **深度→点云/视差处理** | coreon_fusion runner（GeneratePointCloud/FilterDisparity）、percep Fusion（视差域过滤+sobel 边缘滤除）、hal_rgbd SDK 内部——**≥3 处** |
| **时间同步策略** | coreon_fusion 新鲜度 0.1s；percep 双目窗 20ms；person_track rgb 500ms/rgb-depth 300ms/odom 100ms；aimrt_slam 容差 3ms；legged_odom 同步阈 0.05s；combiner 最大年龄 0——**6 种策略各自实现** |
| **深度 ROI 四阶段过滤** | coreon_fusion tracking_params（S1 多峰分解/S2 多线索打分/S3 体型校验/S4 EMA+限幅）与 person_track algorithm_params **两套几乎同构的参数体系各自维护** |
| **外参/内参加载** | ≥6 处独立加载：coreon_fusion 内联 9 组+protected 副本（同值双拷贝）、percep 两套外参文件、person_track 4 个形态外参文件+遗留绝对路径（`/home/agiuser/下载/标定/…`）、aimrt_slam 内联、legged_odom URDF、nav2 launch 静态 TF 发布器——**无统一标定服务** [EV-T1P-58] |

#### 6.4.2.3 传输与配置治理的缺口

- **无全局 QoS profile**：各模块自带 QoS 表（hal_camera 逐话题、legged_odom 逐发布、person_track profile 化），语义不一致风险由各模块自负 [EV-T1P-57]。
- **交付物冗余**：每个 aimrt 应用包各带一份 iox-roudi/aimrte 运行时（20+ 份副本），版本漂移治理成本高 [EV-T1P-57]。
- **标定同步机制被停用**：hal_camera 的跨板标定同步脚本整体注释停用，靠产线保证一致性，缺省时回退 default_param 兜底 [EV-T1P-58]。

### 6.4.3 公共性分析：哪些预处理是「公共部分」

对上述重复项做可抽取性判定：

| 预处理类别 | 判定 | 依据 |
|---|---|---|
| 几何类图像变换（去畸变/缩放/旋转/去畸变恢复） | **公共**（采集侧一次完成；算法侧仅允许引用已发布流） | 一次转换原则；T1 已在 HAL 做对，但 person_track 又做了「LDC 恢复」——上下游变换语义未对齐的证据 [EV-T1P-48][EV-T1P-54] |
| 点云滤波算子 | **公共**（声明式算子链） | 6 处重复；算子语义一致仅参数不同（体素/离群/距离/时域） |
| 时间同步与时间戳 | **公共**（统一时间基+标准算子） | 6 种策略并存说明需求同源、实现各异；且策略选择本身可以规约化（按数据类型与频率定） |
| 标定加载与外参变换 | **公共**（唯一权威+发布） | ≥6 处分散、同值多拷贝、遗留路径——漂移风险已现实发生 |
| 质量监控（无效比/遮挡/曝光/新鲜度） | **公共**（随流字段+健康汇总） | T1 的 sensor_info/occlusion 分析已证明需求，但只在 coreon_fusion 内做 |
| 模型输入特定加工（letterbox 尺寸/均值方差/NCHW/ReID 128×256） | **不公共**（留在模型配置+runner） | 与模型强耦合、参数随模型版本变；T1 的模型 yaml 声明模式已合理 [EV-T1P-45][EV-T1P-54] |
| 有状态融合（EKF 里程计/触地检测） | **不公共为算子，独立成服务** | 状态性强、频率高、参数体系独立（噪声/接触状态机/标定），不适合作无状态管线算子 [EV-T1P-51] |
| 高频本体流（1kHz 关节/500Hz IMU） | **不进管线**（iceoryx 直连） | 时延确定性；T1 生产模式连 DDS 都不上 [EV-T1P-52] |

### 6.4.4 提取「统一独立数据预处理模块」的权衡

| 方案 | 内容 | 优点 | 缺点 | 判定 |
|---|---|---|---|---|
| A. 全集中预处理服务 | 一个独立进程承担所有预处理（含模型输入加工），算法只消费「就绪输入」 | 单点归口、复用彻底 | ① 模型输入异质（尺寸/归一化/布局随模型变），集中式必然配置爆炸；② 跨进程多一跳拷贝与时延（GPU 缓冲区共享复杂）；③ 单点故障影响全部算法；④ 平台相关加速（CUDA/RGA/VPI）被迫抽象漏水 | 否决 |
| B. 维持分散（T1 Pro 现状） | HAL 做采集侧；各算法自带预处理 | 实现自由、无框架税 | ① 6 处点云滤波/5 处图像变换重复开发与测试；② 两套同构深度过滤双份维护；③ 外参 6 处分散+遗留路径+同值双拷贝——一致性风险已现实；④ 新算法接入重复造轮子 | 不足以支撑本产品 |
| **C. 分层抽取（推荐）** | 三段式：**采集侧下沉 HAL**（一次转换，继承 T1 成功面）＋**通用管线中间件**（点云/图像算子库+同步算子+标定服务+质量随流，进程内库+轻量服务）＋**模型相关留在 runner 配置**（继承 T1 合理面） | 见下 | 需要框架开发与算子库建设；跨进程管线需共享内存规划 | **采用**（DD-SP-01） |

**方案 C 相对 B 的价值**：

1. **一致性**：标定一处生效（对比 T1 外参 6 处分散、文档/配置漂移两案 [EV-T1P-29][EV-T1P-58]）；滤波与同步语义全系统唯一，参数可全局审计。
2. **重复计算与维护削减**：同一点云不再被两个消费者各自滤波（T1 的 fused_obstacle_cloud 与 pointcloud_filter 链路即存在此类重叠 [EV-T1P-43][EV-T1P-50]）；算子一次优化（GPU 加速）全体受益。
3. **可观测**：质量与时延指标随流统一采集（无效比/遮挡/新鲜度/处理耗时），对标 T1 的 sensor_info+occlusion 分析但覆盖全部传感。
4. **可测试**：管线确定性（NFR-SP-06）使「录制-回放-比对」成为标准测试手段；T1 每模块各自维护 bag 工具（coreon_fusion 自带 avoid_aimrt2bag [EV-T1P-42]）不可复用。
5. **接入成本**：新算法声明依赖（数据流+几何规格），即得就绪输入；对标 person_track 为对接上游 LDC 所写的「去畸变恢复」补丁代码——上下游契约不清的直接代价 [EV-T1P-54]。

**方案 C 的边界（不应统一的部分）**：模型输入加工留 runner；EKF 类有状态融合独立服务；1kHz/500Hz 本体流直连不过管线；音频前端（AEC/VAD/波束）物理上紧贴麦阵硬件与专有 SDK，作为 HAL 侧插件对待而非通用管线算子 [EV-T1P-53]。

### 6.4.5 对标结论

1. 融合感知≠coreon_fusion 一个模块，而是 8 类模块+HAL 底座的协作——**通用感知服务的「服务面」设计必须覆盖全部结果级能力**（FR-SP-10）。
2. T1 Pro 无统一预处理模块；其采集侧 HAL 公共化是正确且已验证的，直接继承；算法侧 6 处滤波/5 处图像变换/6 种同步/6 处外参的分散是明确的公共性候选，按方案 C 抽取。
3. 传输治理（全局 QoS、交付物去重）与标定治理（唯一权威+跨板校验+停用脚本复活）是需要补齐的平台缺口。

---

## 6.5 设计方案

### 6.5.1 设计目标与原则

1. **一次转换**：几何/格式变换只在 HAL 做一次，多规格流分发（FR-SP-02）。
2. **公共下沉、模型内收、有状态独立**（§6.4.4 方案 C 三段式）。
3. **结果不出板**：大带宽板内消化，跨板只传结果级（FR-SP-12）。
4. **质量随流**：质量是数据的一部分，不是旁路系统（FR-SP-07）。
5. **声明式与确定性**：管线/场景/标定全部声明式；同输入必同输出（NFR-SP-06）。

### 6.5.2 总体设计

```mermaid
flowchart LR
    HW(["传感硬件<br/>RGB×N / ToF×N / IMU×2 / 关节×12 / BMS / 触摸 / 麦阵 / 可选:鱼眼·激光"])
    subgraph HAL["L0/L1 传感接入与采集侧预处理（sensor_hal，每板一个）"]
        CAM["相机插件<br/>UYVY→LDC→多档流+旋转"]
        TOF["ToF/深度插件<br/>滤波→深度→点云(组织点云)"]
        AUD["音频前端插件<br/>AEC/VAD/波束"]
        BODY["本体插件<br/>关节1kHz/IMU 500Hz 直连"]
        TS["硬件时间戳/板间同步"]
        PWR["供电与流控执行"]
    end
    subgraph MW["通用预处理中间件（库 + 轻量服务）"]
        PCP["点云管线 pointcloud_pipeline<br/>声明式算子链"]
        IP["图像算子库 image_ops"]
        SYNC["同步算子（freshness/滑窗/硬同步）"]
        CALIB["标定服务 calib_server<br/>唯一权威+发布+校验+在线观测"]
        QUAL["质量随流聚合→健康通道"]
    end
    subgraph SVC["L2 通用感知服务（结果级）——归小脑子系统（暂定）"]
        FUS["融合避障服务<br/>ObstacleCheck/融合点云/避障状态"]
        ODOM["本体融合服务<br/>EKF 里程计/躯干位姿"]
        DET["目标服务<br/>检测+跟踪+ReID"]
        SEM["语义服务<br/>室内外/楼梯/可通行/代价图"]
        SCENE["感知场景编排（BT+tick）"]
    end
    ALGO["L3 算法模块（模型 runner：<br/>模型特定预处理在模型配置中）"]
    CONS["消费者：任务调度/导航/跟随/交互/App/云"]

    HW --> HAL
    CAM & TOF & AUD -->|"零拷贝多流（dmabuf/iceoryx）+统一QoS"| MW
    BODY -->|"iceoryx 直连（不过管线）"| ODOM
    MW --> SVC
    SVC --> ALGO
    ALGO --> SVC
    SVC -->|"结果级跨板（≤5Mbps）"| CONS
    CALIB -.->|"内参/外参发布"| HAL & MW & SVC
    QUAL -.->|"健康/降级信号"| CONS
    SCENE <-->"任务/资源场景联动（TS 域）"
```

职责矩阵：

| 组件 | 职责 | 不做 |
|---|---|---|
| sensor_hal | 采集、采集侧一次预处理、硬件时戳、供电流控执行、质量原始指标 | 不做算法级滤波；不跨板发原始流 |
| pointcloud_pipeline/image_ops/sync | 声明式算子链、几何变换算子、同步算子 | 不含模型参数；无全局状态 |
| calib_server | 标定唯一权威：存储/校验/发布/在线观测框架 | 不做标定算法本身（工具链负责，产出物入库） |
| 融合避障/目标/语义服务 | 结果级能力输出、场景编排（**归属小脑子系统，暂定**） | 不做任务决策（TS 域） |
| 本体融合服务（EKF） | 里程计/躯干位姿/触地 | 不进通用管线（高频有状态） |

### 6.5.3 关键机制设计

#### 6.5.3.1 相机链路（一次转换规范）

```text
采集(UYVY/RAW) → [LDC 去畸变(可配 fov_scale)] → ┬→ 算法流（全分辨率/按需，BGR，带 CameraInfo）
                                                ├→ 编码流（NV12 低分辨率多档，供 App/RTSP/录制）
                                                └→ 质量流（统计指标，低频）
形态相关旋转（如四足/双足安装方向差异）在 HAL 内完成，消费者感知不到
后端抽象：GPU LDC（CUDA/NPU）/ RGA / OpenCL 按平台选择，接口统一（对标 T1 双板异构实现 orin CUDA vs rk RGA+OpenCL [EV-T1P-48]）
```

约束：同一几何变换全链一次（发布流的 CameraInfo 必须与实际发布图像严格一致）；算法模块禁止对已发布流再做去畸变/再旋转（上下游契约由 CameraInfo 与坐标系声明表达——修复 T1 person_track「LDC 恢复」补丁问题 [EV-T1P-54]）。

#### 6.5.3.2 深度/ToF 链路

- 深度滤波参数化（幅值阈值/飞点/MPI/平滑——对标 Ofilm 滤波 ini 26 项 [EV-T1P-46]），随机型标定一机一档。
- 深度→点云在 HAL 一次生成，内参取自 calib_server；保留**组织点云结构**（行×列），支持消费者按行列步长降采样（对标 T1 row_step/col_step 采样 [EV-T1P-44][EV-T1P-50]）。
- 无效点比随流输出（质量字段），遮挡判定（多传感器信息一致性窗口）在服务层汇总（对标 occlusion_analysis [EV-T1P-44]）。

#### 6.5.3.3 时间基与同步策略（标准选择表）

时间戳标准：`hw_ts`（硬件采集时戳，权威）+ `recv_ts`；跨板时钟用既有同步机制（对标 T1 板间亚毫秒 RTT 基线 [EV-T1P-59]）。

| 数据组合 | 规定策略 | 对标依据 |
|---|---|---|
| 双目左右帧 | 硬件同步（fsync）+滑窗严格配对（窗 ≤20ms） | T1 stereo_sync 20ms [EV-T1P-49] |
| 图像×点云（检测+深度） | 滑窗配对（容差按任务 100-300ms 可配）+新鲜度兜底 | T1 rgb_depth_max_delta 300ms [EV-T1P-54] |
| 传感×odom（时间对齐坐标变换） | 滑窗插值（odom 历史缓存） | T1 odom 历史 20-300 帧 [EV-T1P-49][EV-T1P-54] |
| 融合避障多 ToF | 新鲜度门控（≤1-2 帧周期） | T1 freshness 0.1s [EV-T1P-43] |
| IMU×关节（EKF） | 固定同步阈值+缓冲降采样 | T1 sync 0.05s、500→100Hz [EV-T1P-51] |
| ToF 板间（双板机型） | 硬件同步信号（inter_board 等价） | T1 /ofilm/tof/inter_board [EV-T1P-46] |

#### 6.5.3.4 标定服务 calib_server

- 唯一权威仓库：`/robot/protected/calib/<机型>/<SN>/`（内参/外参/ToF 专用标定/IMU 温补），条目带版本与校验和（对标 T1 protected 一机一档与 spc md5 一致性 [EV-T1P-46][EV-T1P-58]）。
- 发布：`camera_info` 标准话题随流、外参以参数/服务发布 + TF 静态发布器统一生成（**修复 T1 外参 6 处分散、同值双拷贝、遗留绝对路径三个问题** [EV-T1P-58]）。
- 校验：启动校验和核对；双板机型跨板一致性**自动**校验（复活 T1 被注释停用的同步机制，改为服务内建 [EV-T1P-58]）；标定缺失时显式告警+出厂默认参数兜底（对标 default_param，但必须上报降级标记）。
- 形态相关外参：双外参制（工厂标定值/输出修正值分离）+在线观测器框架（对标 T1 human_main_pitch_observer 与 dog_head_extended_transform [EV-T1P-44]、t_extrinsics 双外参制 [EV-T1P-49]）。

#### 6.5.3.5 通用点云/图像管线（声明式算子链）

```yaml
# cfg/pipelines/obstacle_cloud.yaml —— 示例：避障点云管线
pipeline: obstacle_cloud
input:  {source: /robot/sensor/tof/front/points, organized: true}
ops:
  - roi:        {x: [-0.2, 2.5], z: [0.05, 3.0]}        # ROI/近地裁剪
  - stride:     {row: 2, col: 2}                         # 组织点云降采样
  - voxel:      {size: 0.05}
  - outlier:    {type: radius, radius: 0.05, min_neighbors: 20}
  - temporal:   {confirm_frames: 2, ttl_ms: 350, iou: 0.4}   # 时域确认
  - target_removal: {topic: /robot/perception/target_info, radius: 0.9, depth_tol: 0.6}
output: {topic: /robot/perception/cloud/obstacle_front, frame: base_link}
```

算子库覆盖 T1 六处重复实现的全部算子（体素/离群/距离/高度/组织采样/时域确认/去重/目标剔除/地面分割/非地面提取——对标 coreon_fusion detectGround 系与 percep tof_denoise [EV-T1P-45][EV-T1P-49]）；地面分割（RANSAC+形态阈值）作为复合算子提供。图像算子库同理（resize/letterbox/旋转/颜色空间——几何类公共，归一化留模型配置）。

#### 6.5.3.6 本体融合服务（EKF 里程计）

对标 T1 legged_odom 全参数体系 [EV-T1P-51]：误差状态 EKF；IMU/关节缓冲降采样（500→100Hz、1k→250Hz）；前置滑动平均（可配窗）；触地检测（力矩阈值+置信度状态机）；bias 上电静态标定（N 帧）+运行中静止重标定（静止判据+最小间隔）；输出抽取（odom 100Hz、躯干位姿 50Hz）；运动状态门控（引用 MC 状态）。作为独立服务实现，不经通用管线（DD-SP-08）。

#### 6.5.3.7 感知服务面与感知场景

- 结果级服务（统一 QoS+统一响应模型）：ObstacleCheck（圆柱范围/方向/形态参数 → 有无障碍+方向+置信度+类型）、targets（Detection2DArray+track id）、semantic_env（室内外/楼梯/可通行性）、costmap_local（语义代价图：占据+语义类别+通行代价——对标 PercepCostmap [EV-T1P-49]）、fusion_state（避障中标志+触发源）。
- 感知场景：BT 编排+tick 周期声明（跟随感知场景 100ms/避障场景 50ms——对标 coreon_fusion scenes [EV-T1P-39]）；场景状态可查询（含 tick 统计——对标 scene_status 0-5+tick_count [EV-T1P-39]）；与 TS 域联动：任务启动感知场景（跟随任务→跟随感知场景）、资源场景提供 NPU/GPU 配额、系统状态门控启停。
- 场景内传感器自动注入（对标 sensors.auto_inject_to_scene [EV-T1P-43]）：场景声明所需数据流，编排器负责订阅路由与供电申请。

#### 6.5.3.8 传输治理

- **全局 QoS profile**（三类：sensor=best_effort 浅深度、state=reliable+transient_local、command=reliable）——修复 T1 无全局 profile [EV-T1P-57]；DDS/iceoryx 配置全局唯一（对标 FastDDS xml 白名单 [EV-T1P-57]）。
- 共享内存池统一规划（按流规格预算，含大图池——对标 T1 roudi mempool 18MB×10 大图段 [EV-T1P-57]）。
- 交付物治理：iceoryx/运行时单版本统一分发，应用包不各带副本（对标 T1 20+ 份冗余 [EV-T1P-57]）。

### 6.5.4 接口设计（IF 条目，草案）

| 编号 | 接口 | 类型 | 语义要点 |
|---|---|---|---|
| IF-SP-01 | `/robot/sensor/camera/{id}/{algo\|encode}` + `camera_info` | topic | 算法流/编码流分离；CameraInfo 与图像严格一致；质量字段在消息头 |
| IF-SP-02 | `/robot/sensor/tof/{id}/points`（组织点云）+ `/sensor_info` | topic | 行列结构保留；sensor_info 含曝光/温度/无效比 |
| IF-SP-03 | `/robot/sensor/imu/{id}`、`/robot/sensor/joint/state` | topic | 关节/IMU 板内 iceoryx 直连（跨板不出） |
| IF-SP-04 | `/robot/sensor/quality` | topic | 全传感质量汇总（低频）→ 健康通道/降级信号 |
| IF-SP-05 | `/robot/sensor/set_camera_stream`、`set_tof_stream`（`SetCameraStream.srv`/`SetTofStream.srv`） | service | 电源/流掩码控制（供 TS 域状态动作与场景调用）；幂等+就绪回报（回靠 T1 SetHalCameraStream/SetHalTofStream 双服务与电源+流双掩码语义 [EV-T1P-46]） |
| IF-SP-06 | `/robot/calib/camera_info/{sensor}`、`/robot/calib/extrinsics`（param/srv） | topic/srv | 标定唯一发布面；含版本与校验和 |
| IF-SP-07 | `/robot/perception/obstacle_check`（`ObstacleCheck.srv`） | service | 圆柱/方向/形态查询（对标 ObstacleCheck [EV-T1P-45]） |
| IF-SP-08 | `/robot/perception/target_info`、`/robot/perception/fusion_state` | topic | 目标列表（检测+跟踪+ReID）、避障状态 |
| IF-SP-09 | `/robot/perception/semantic_env`、`/robot/perception/costmap_local` | topic | 室内外/楼梯/可通行性；语义代价图 |
| IF-SP-10 | `/robot/perception/scene/{list,state,command}` | srv/topic | 感知场景启停/查询（含 tick 统计；对标 T1 set_follow_perception_task 单场景开关的一般化） |
| IF-SP-11 | `/robot/odom`、`/robot/odom/torso`、`/robot/tf` | topic | EKF 里程计/躯干位姿/TF（odom→base 动态、base→sensor 静态由 calib 生成） |
| IF-SP-12 | `robot_msgs/`：`SensorHeader`（hw_ts/recv_ts/seq/quality/sensor_id）、`PointCloudOrganized`、`CommonResponse` 族 | 消息 | 统一消息头与组织点云（IF 复用 TS 域 IF-TS-13 响应模型） |

### 6.5.5 数据与配置设计

| 配置 | 路径（规划） | 内容 | 治理 |
|---|---|---|---|
| 传感清单 | `cfg/sensors/<机型>.yaml` | 传感器实例、插件、流规格、电源组 | 机型裁剪入口（FR-SP-13） |
| 管线库 | `cfg/pipelines/*.yaml` | 算子链（§6.5.3.5 示例） | 算子版本化；CI 一致性 |
| 标定库 | `/robot/protected/calib/<机型>/<SN>/` | 内参/外参/ToF/IMU 标定+校验和 | 一机一档；只读挂载 |
| 感知场景库 | `cfg/perception/scenes/*.yaml` | 场景 BT+tick+数据流声明+资源需求 | 与 TS 场景库联编校验 |
| QoS profile | `cfg/transport/qos.yaml` | 三类全局 profile | 全局唯一 |
| 同步策略表 | `cfg/sync_policy.yaml` | 数据组合→策略+参数 | 按规约校验 |

### 6.5.6 部署与资源预算

| 组件 | 板位 | 形态 | 预算（V1 目标） | 对标参照 |
|---|---|---|---|---|
| sensor_hal | 各板 | 独立进程（per 板） | 采集+采集侧预处理 CPU ≤1.5 核（感知板） | T1 静置：hal_camera(orin) 42.9% + hal_rgbd 38.9%（单核口径）[EV-T1P-59] |
| 管线中间件 | 感知板 | 库（随宿主）+calib_server 轻量服务 | calib_server CPU ≤1%、RSS ≤50MB | — |
| 感知服务/算法 | 感知板 | 独立进程组 | GPU/NPU 按场景声明计量 | T1 NPU 双核常跑交互视觉 [EV-T1P-59] |
| 本体融合 | 运控板 | 独立进程 | CPU ≤0.8 核 | T1 legged_odom 行走 43% 单核 [EV-T1P-51 源：A §6.3] |
| 单板机型 | 单板 | 全栈同板裁剪 | 原始流仍不出「板内」共享内存 | — |

### 6.5.7 容错、安全与降级

| 故障场景 | 行为（必须） | 对标依据 |
|---|---|---|
| 传感器离线/无数据 | 新鲜度超时→质量降级标记→依赖该流的服务按声明降级（避障降级为保守限速/任务拒绝+reason） | T1 freshness 门控 [EV-T1P-43] |
| 镜头遮挡/脏污 | 遮挡判定（无效比/曝光/多传感一致性）→告警+能力降级 | T1 occlusion_analysis [EV-T1P-44] |
| 过暗环境 | 亮度门控信号→跟随类任务拒绝或预警 | T1 brightness（阈值 82、防闪烁确认）[EV-T1P-55] |
| 时戳跳变/时钟异常 | 检测跳变→重同步→受影响管线复位状态 | — |
| 标定缺失/校验失败 | 出厂默认参数兜底+显式降级标记上报（不得静默使用默认值） | T1 default_param 兜底改良 [EV-T1P-58] |
| 管线算子异常 | 单算子超时/崩溃→管线降级跳过该算子或切换备份路径+健康上报 | — |
| 感知板掉电/休眠 | 运控板本体感知（EKF+安全）独立可用；自主移动类任务按门控拒绝 | 双板职责分离设计 [EV-T1P-59] |

### 6.5.8 可配置性与可扩展性

- **新增传感器**（NFR 类比 TS 域演练项）：实现插件（采集+一次预处理+质量指标）→ `sensors/<机型>.yaml` 登记 → 流规格与标定条目入库 → 完成。
- **新增算法模块**：声明数据依赖（流+几何规格+同步策略）→ 模型配置（输入尺寸/归一化）→ 消费就绪流；禁止自带重复滤波。
- **机型裁剪**：传感器清单与场景库按机型组合；单板入门机型裁剪感知服务子集，HAL/管线不变。
- **算子扩展**：新算子以插件注册（含 GPU 实现），管线配置引用。

---

## 6.6 功能、规格与工作量分析

### 6.6.1 概念界定（同第 5 章 §5.6.1）

**功能＝系统能做什么（WHAT，能力单元）；规格＝做到什么程度/什么条件下成立（HOW WELL / HOW MUCH，量化约束与验收边界）**。规格未定的功能不具备估算条件；同一功能规格翻倍、或有无可复用开源实现，工作量可差数倍到一个数量级。完整界定与使用规则见第 5 章 §5.6.1；本章表中「规格」列摘自 §6.3 的 FR/NFR 量化参数。

### 6.6.2 估算口径与假设

- **代码量/工作量口径**与第 5 章 §5.6.2 相同（人月含单测/评审/文档，不含算法研究与选型评审；联调单列）。
- **参考优先序**：① T1 Pro 实用的**开源基座与同款模型**（ROS 2、iceoryx、Fast DDS、OpenCV〔SDK 附完整源码 `examples/opencv`〕、PipeWire、linuxptp/chrony；模型同款 YOLOv8/CLIP-ReID/SOLIDER/silero-vad/DTLN——EV-T1P-61）；② T1 闭源模块（coreon_fusion/percep/person_track/hal_* 等，EV-T1P-60）的**社区同类最佳开源实现**；③ 无开源等价者（厂商 ToF SDK、供电流控）按厂商对接+自研薄层估。
- **模型对接**：模型获取优先用开源同款权重；微调、格式转换（engine/rknn）、精度达标计入对应行的「模型对接」部分。
- **许可证风险**：YOLOv8（AGPL-3.0）、CLIP-ReID/SOLIDER（研究性许可）等商用合规需评审（OP-SP-07），必要时替换为宽松许可模型——该项为法务/选型工作，不计入本章工作量。

### 6.6.3 功能-规格-参考实现-工作量对照表

> 参考实现列约定：**上行**＝启元 T1 Pro 是否提供对应的开源实现（基座/板上实装开源件/同款模型，附仓址）；**下行**＝业界能提供类似功能的开源实现（附仓址）。

| 功能名称 | 功能简介 | 规格（量化要点，对应 FR/NFR） | 可参考的开源代码仓与对应实现目录 | 代码量预估 | 工作量预估 |
|---|---|---|---|---|---|
| 相机 HAL 插件（P0） | 相机采集与采集侧一次预处理（格式转换/去畸变/多档缩放/形态旋转），多规格流零拷贝分发 | ≥2 路 RGB；2592×1944@10-30fps 采集；UYVY→LDC（fov_scale 可配）→算法流+NV12 编码流（864×648 等 ≥4 档）；形态旋转；dmabuf 零拷贝（FR-SP-01/02、NFR-SP-01/04） | **T1 Pro：未提供**（hal_camera 闭源，仅参数级实证 EV-T1P-48）<br>**业界开源**：usb_cam https://github.com/ros-drivers/usb_cam（`src/usb_cam.cpp`——V4L2 采集/格式/缓冲管理）；OpenCV https://github.com/opencv/opencv（`modules/imgproc/src/undistort.cpp`、`imgwarp.cpp`〔remap〕、`resize.cpp`——几何变换；SDK 附完整源码 `examples/opencv`）；板端加速 librga/VPI 为闭源库（公开 API） | 6~9 K LoC | 1.5 人月 |
| ToF/深度 HAL 插件（P0） | ToF 深度数据采集、参数化滤波与组织点云生成，随流携带质量标记 | ≥5 路 ToF；深度滤波参数化（≥20 项，等价 T1 滤波 ini）；深度→组织点云（576×380 级）@20Hz；无效比质量字段；一机一档标定加载（FR-SP-01/02/07） | **T1 Pro：未提供**（hal_rgbd 闭源+厂商 SDK 商业授权 EV-T1P-46）<br>**业界开源**：image_pipeline https://github.com/ros-perception/image_pipeline（`depth_image_proc/src/point_cloud_xyz.cpp`——深度→点云+内参投影；`image_proc/src`——组织图像流处理） | 5~8 K LoC | 1.5 人月（含厂商 SDK 对接） |
| 本体插件·高频直连（P0） | 关节与躯干 IMU 高频数据的 iceoryx 直连采集与诊断上报（不过通用管线） | 关节 1kHz/IMU 500Hz iceoryx 直连；500ms 诊断上报；生产模式不出 DDS（FR-SP-01、DD-SP-09） | **T1 Pro：未提供**（device_manager 闭源 EV-T1P-52）<br>**业界开源**：ros2_control https://github.com/ros-controls/ros2_control（`hardware_interface/src`——硬件接口声明与状态接口模式）；can-utils https://github.com/linux-can/can-utils（CAN 收发工具链） | 3~5 K LoC | 1 人月 |
| 硬件时间戳与板间同步（P0） | 为全部传感数据提供权威硬件时戳基准与跨板/板间同步信号 | PWM/fsync 硬件时戳 ≤1ms（NFR-SP-03）；跨板同步信号（ToF inter_board 等价）；相机 soc_sync 就绪门控（FR-SP-03、DD-SP-05） | **T1 Pro：未提供**（板级机制；板上实装开源件 linuxptp/chrony，EV-T1P-60）<br>**业界开源**：linuxptp https://github.com/richardcochran/linuxptp（作者维护镜像；`ptp4l.c`/`sk.c`——PTP 硬件时戳用法）；chrony https://github.com/mlichvar/chrony（系统时钟同步） | 2~4 K LoC | 1 人月（含内核/驱动联调） |
| 零拷贝传输与 QoS 治理（P0） | 全局 QoS profile、共享内存池规划与 DDS 配置的统一传输底座 | 全局 3 类 QoS profile；iceoryx mempool 规划（含大图池）；DDS XML 统一；跨板 ≤5Mbps 契约校验（FR-SP-12、NFR-SP-04/05、DD-SP-07） | **T1 Pro：提供基座**——AimRT https://github.com/AimRT/AimRT（`src/plugins/iceoryx_plugin`、`src/plugins/ros2_plugin`——通道后端封装可复用；aimrte 增强层闭源 EV-T1P-57/60）<br>**业界开源**：iceoryx https://github.com/eclipse-iceoryx/iceoryx（`iceoryx_posh`——零拷贝发布订阅，T1 板上实装 2.95）；Fast-DDS https://github.com/eProsima/Fast-DDS（XML QoS profiles，T1 板上实装 2.6.12） | 2~4 K LoC | 0.5~1 人月 |
| 点云管线算子库（P0） | 声明式点云预处理算子链（滤波/降采样/时域确认/地面分割等），一处实现全系统复用 | ≥10 算子（ROI/高度带/体素/半径离群/组织行列采样/时域确认/去重/目标剔除/地面分割/非地面提取）；声明式 YAML；确定性回放（FR-SP-05、NFR-SP-06） | **T1 Pro：未提供**（六处闭源重复实现 EV-T1P-56）<br>**业界开源**：PCL https://github.com/PointCloudLibrary/pcl（`filters/src/{voxel_grid,radius_outlier_removal,statistical_outlier_removal,crop_box}.cpp`、`segmentation/src/sac_segmentation.cpp`——T1 六处重复算子的标准实现） | 6~10 K LoC | 1.5~2 人月 |
| 同步算子库（P0） | 多源数据对齐算子（新鲜度门控/滑窗配对/插值）与统一时间戳语义 | freshness/滑窗/插值三策略+odom 历史缓存；策略表驱动（FR-SP-03、DD-SP-05） | **T1 Pro：未提供**（六种同步策略各自闭源实现 EV-T1P-56）<br>**业界开源**：message_filters https://github.com/ros2/message_filters（`include/message_filters/sync_policies/{exact_time,approximate_time}.h`——标准同步策略实现） | 2~3 K LoC | 0.5 人月 |
| calib_server 标定服务（P0） | 内外参一机一档唯一权威管理、校验与发布、TF 生成与在线观测框架 | 一机一档+版本 md5；跨板一致自动校验；camera_info/extrinsics 发布+TF 静态生成；缺失兜底+降级标记；在线观测框架（FR-SP-04、DD-SP-03） | **T1 Pro：未提供**（protected 机制与停用脚本实证 EV-T1P-58）<br>**业界开源**：image_pipeline https://github.com/ros-perception/image_pipeline（`camera_info_manager`——标定加载与 camera_info 发布）；geometry2 https://github.com/ros2/geometry2（`tf2_ros`——静态 TF 广播） | 4~6 K LoC | 1 人月 |
| 质量随流与健康聚合（P0） | 传感质量指标随数据流传导，聚合为阈值告警与能力降级信号 | 无效比/曝光/遮挡/新鲜度/丢帧五类指标随流；阈值告警+降级信号（FR-SP-07、DD-SP-10） | **T1 Pro：未提供**（occlusion/sensor_info 分析闭源 EV-T1P-44）<br>**业界开源**：diagnostics https://github.com/ros/diagnostics（`diagnostic_updater`、`diagnostic_aggregator`——诊断上报与聚合范式） | 2~4 K LoC | 0.5 人月 |
| 传感供电流控（P0） | 传感器粒度的电源/出流掩码控制，供系统状态动作与资源场景调用 | 电源/流掩码 bit 级；幂等+就绪回报 ≤1s；与状态动作/场景联动（FR-SP-08） | **T1 Pro：未提供**（SetHalTofStream/SetHalCameraStream 闭源服务，掩码语义实证）<br>**业界开源**：无直接同类（自研薄层：V4L2 stream on/off+内核电源管理）；相关工具 i2c-tools https://git.kernel.org/pub/scm/utils/i2c-tools/i2c-tools.git/（I2C 寄存器直控，T1 setlight.sh 同类用法 EV-T1P-47） | 1.5~3 K LoC | 0.5 人月 |
| 本体融合 EKF 服务（P0） | IMU+关节状态误差状态卡尔曼滤波，输出里程计与躯干位姿（含触地检测与 bias 重标定） | /odom ≥100Hz、躯干位姿 ≥50Hz；触地检测状态机；bias 上电标定+运行中静止重标定；URDF 运动学（FR-SP-09、NFR-SP-03、DD-SP-08） | **T1 Pro：未提供**（legged_odom 闭源，参数体系全盘实证 EV-T1P-51）<br>**业界开源**：robot_localization https://github.com/cra-ros-pkg/robot_localization（`src/ekf.cpp`、`src/filter_base.cpp`——误差状态 EKF 标准实现）；pronto https://github.com/ori-drs/pronto（`pronto_core`/`pronto_quadruped`——四足足式里程计+触地估计，ROS2 Humble）；kdl_parser https://github.com/ros/kdl_parser（URDF 运动学） | 8~12 K LoC | 2~2.5 人月 |
| 融合避障服务（P0） | 多源点云+图像融合的障碍检测、局部绕障栅格与避障状态，提供定向障碍查询服务 | 5 路点云+图像融合；ObstacleCheck P99≤50ms（NFR-SP-02）；局部绕障栅格（0.025m 级）；避障状态广播；目标从点云剔除（FR-SP-10） | **T1 Pro：未提供**（coreon_fusion 闭源，结构实证 EV-T1P-42~45）<br>**业界开源**：navigation2 https://github.com/ros-navigation/navigation2（`nav2_costmap_2d/src/layers`——obstacle/voxel 障碍层）；spatio_temporal_voxel_layer https://github.com/SteveMacenski/spatio_temporal_voxel_layer（时域体素层）；地面分割见 PCL | 10~15 K LoC | 2.5~3 人月 |
| 目标服务·检测/跟踪/ReID（P0） | 行人等目标的检测、多目标跟踪、重识别与深度估计，输出统一目标列表 | ≥30Hz；letterbox 640 级输入；ReID 128×256；跟踪+深度 ROI 四阶段过滤（FR-SP-10） | **T1 Pro：未提供代码**（person_track 闭源）；其实用模型为开源同款（EV-T1P-61）<br>**业界开源**：ultralytics https://github.com/ultralytics/ultralytics（YOLOv8 检测/分割，T1 实用同款）；CLIP-ReID https://github.com/Syliz517/CLIP-ReID（T1 实用 ViT-B/16 同款，MIT）；OC_SORT https://github.com/noahcao/OC_SORT（多目标跟踪，T1 实用 OCSort 参数 EV-T1P-45；另 SOLIDER ReID 亦为 T1 同款，见 EV-T1P-61）；推理部署链 onnxruntime https://github.com/microsoft/onnxruntime（T1 实用 1.19.2） | 4~6 K LoC（集成胶水+模型转换） | 1~1.5 人月 |
| 集成与性能达标（P0） | 端到端时延/带宽/零拷贝/确定性/资源预算等 NFR 的集成验证与达标 | NFR-SP-01..07 全部达标（时延/带宽/零拷贝/确定性/资源预算） | **T1 Pro：未提供**<br>**业界开源**：navigation2 https://github.com/ros-navigation/navigation2（`nav2_system_tests`——系统级测试组织）；rosbag2 https://github.com/ros2/rosbag2（回放比对） | 3~5 K LoC（测试代码） | 1 人月 |
| 图像算子库（P1） | 几何类图像变换算子（resize/letterbox/旋转/颜色空间/remap）与 GPU 后端抽象 | resize/letterbox/旋转/CSC/remap；≥4 档输出；GPU 后端抽象（CUDA/RGA）（FR-SP-06） | **T1 Pro：未提供**（各模块内嵌实现 EV-T1P-56）<br>**业界开源**：OpenCV https://github.com/opencv/opencv（`modules/imgproc/src/resize.cpp`、`imgwarp.cpp`；SDK 附源码）；ultralytics https://github.com/ultralytics/ultralytics（`ultralytics/data/augment.py`——letterbox 参考） | 3~5 K LoC | 1 人月 |
| 语义服务·室内外/楼梯/代价图（P1） | 语义分割驱动的场景理解（室内外/楼梯/可通行性）与语义局部代价图输出 | 语义代价图 10m/0.05m、三层记忆（0.5s/3s/40s）；室内外/楼梯判定；形态代价表（FR-SP-10） | **T1 Pro：未提供**（percep 闭源，参数实证 EV-T1P-49）<br>**业界开源**：navigation2 https://github.com/ros-navigation/navigation2（`nav2_costmap_2d/src`——rolling costmap+图层机制）；PaddleSeg https://github.com/PaddlePaddle/PaddleSeg（分割模型库，Apache-2.0，PP-OCR 同生态——T1 实用 PP-OCR 同源 EV-T1P-61） | 8~12 K LoC（+模型对接） | 2 人月 |
| 感知场景编排（P1） | 感知能力以行为树场景组合启停（tick 驱动），与任务/资源场景联动 | 场景 ≥3（跟随/避障/融合）+tick 50~100ms 级；场景状态+tick 统计；传感自动注入；与任务/资源场景联动（FR-SP-11、DD-SP-06） | **T1 Pro：未提供**（coreon_fusion BT 场景闭源，bt_xml 同形态实证 EV-T1P-39）<br>**业界开源**：BehaviorTree.CPP https://github.com/BehaviorTree/BehaviorTree.CPP（BT 引擎与 XML 树）；navigation2 https://github.com/ros-navigation/navigation2（`nav2_bt_navigator/src`——BT×ROS 集成范式） | 3~5 K LoC | 0.5~1 人月 |
| 录制回放工具（P2） | 原始流与管线中间流的录制，离线逐帧一致回放 | 原始+管线中间流录制；逐帧一致回放（FR-SP-14、NFR-SP-06） | **T1 Pro：未提供**（coreon_fusion 自带 avoid_aimrt2bag 为闭源工具 EV-T1P-42）<br>**业界开源**：rosbag2 https://github.com/ros2/rosbag2（录制回放框架） | 1.5~3 K LoC | 0.5 人月 |

### 6.6.4 汇总与配比建议

| 范围 | 代码量 | 工作量 |
|---|---|---|
| V1（P0 全部，14 行） | 约 65~85 K LoC | 约 16~17 人月 |
| 全量（P0+P1+P2，18 行） | 约 85~105 K LoC | 约 20~21 人月 |

- **配比建议**：3 名工程师并行（1 负责 HAL 与传输/时戳、1 负责管线与标定/EKF、1 负责感知服务与集成），V1 基线约 6~7 个月。
- **工作量前三**：融合避障（2.5~3）、本体融合 EKF（2~2.5）、语义服务（2）——三者均无 T1 开源对应（coreon_fusion/percep 闭源），但有 nav2/PCL/robot_localization/pronto 强参照，属「对标移植+自研」混合型。
- **模型依赖与许可证**：目标服务直接复用 T1 同款开源模型（YOLOv8/CLIP-ReID/SOLIDER，EV-T1P-61），转换与部署已计入该行；商用许可证风险单列 OP-SP-07，不计入工作量。
- **裁剪提示**：单板入门机型（假设 A-1）可先裁掉语义服务与感知场景编排（约 -2.5~3 人月），管线与 HAL 不变。
- **联动**：OP-SP-01（传感器组合）与 OP-SP-04（深省电恢复时延）的定标计入「集成与性能达标」行。

### 6.6.5 端到端场景走查（SP 视角）

完整走查见第 5 章 §5.9.1（UC-A「跳舞中被跟随抢占」，含流程图+时序图）。本节仅给出 SP 功能在该 usecase 中的出场视角：

| SP 功能 | 出场点（见 §5.9.1） |
|---|---|
| 相机 HAL 插件 / 图像算子库 | T3-2：follow 场景启动后提供 letterbox 检测流 |
| ToF/深度 HAL 插件 / 点云管线算子库 | T3-3：组织点云 → 滤波 → 避障栅格 |
| 本体插件·高频直连 / 本体融合 EKF 服务 | T0 常驻（odom）；T2 仲裁门控（odom 可信）；T3-4 跟随规划输入 |
| 硬件时间戳与板间同步 / 同步算子库 | T3-2：图像×odom 多源对齐的前提 |
| 目标服务·检测/跟踪/ReID | T3-2 锁定说话人；T4 目标丢失防抖 |
| 融合避障服务 | T3-3/4 避障叠加改写；T4 障碍路径；ObstacleCheck 供任务门控 |
| 传感供电流控 | T3-1：follow_mode 场景切换时的上电确认（就绪回报） |
| 质量随流与健康聚合 | T4：过暗降级/遮挡告警 |
| 感知场景编排 | T3-2：follow 场景（BT tick 100ms）启停与数据路由 |
| calib_server / 零拷贝传输与 QoS 治理 | 隐性前提（坐标正确性/零拷贝底座），全程在场但不显性出场 |
| 语义服务 / 录制回放工具 | 本 usecase 不出场（建图、运镜类 usecase 登场） |

**SP 侧异常路径**（对应 §5.9.1 异常路径中 SP 主导的行）：目标丢失（目标服务防抖→任务态停步不取消）、过暗（质量随流→跟随门控预警）、障碍（融合避障改写速度/拒绝继续）——三条异常链共同体现「质量随流 + 门控 + 降级信号」的跨域协同（FR-SP-07/10 与 TS 域 FR-TS-07 的联动）。

---

## 6.7 关键设计决策记录（DD）

| 编号 | 决策 | 备选与取舍 | 结论依据 |
|---|---|---|---|
| DD-SP-01 | 预处理采用「采集侧下沉 HAL + 通用管线中间件 + 模型相关留 runner」三段式，而非全集中模块或维持分散 | 方案 A（全集中）否决：模型异质/拷贝时延/单点；方案 B（维持 T1 现状）否决：6 处滤波重复、外参 6 处分散已现实漂移 | §6.4.4 |
| DD-SP-02 | 一次转换原则：去畸变/格式/缩放/旋转在 HAL 一次完成、多规格流分发 | 各消费者自变换（否决：T1 person_track「LDC 恢复」补丁即上下游契约不清的代价 [EV-T1P-54]） | 继承 T1 HAL 成功面 [EV-T1P-48] |
| DD-SP-03 | 标定唯一权威仓库+统一发布+跨板自动校验 | 各模块自存副本（否决：T1 同值双拷贝/遗留路径/同步脚本停用三案 [EV-T1P-58]） | §6.4.2.2 |
| DD-SP-04 | 点云/图像滤波以声明式算子链复用 | 各模块自实现（否决：T1 六处点云滤波、两套同构四阶段深度过滤 [EV-T1P-56]） | §6.4.2.2 |
| DD-SP-05 | 时间同步标准化：统一时间基+策略选择表+公共算子 | 各模块自定义（否决：T1 六种策略并存 [EV-T1P-56]） | §6.5.3.3 |
| DD-SP-06 | 感知场景编排（BT+tick）继承并扩展：与任务/资源场景显式联动 | 三套场景词汇并存（否决：T1「场景」四义教训 [EV-T1P-23][EV-T1P-39]，见 TS 章 §5.4.1.3） | [EV-T1P-39] |
| DD-SP-07 | 全局 QoS profile 与传输配置统一 | 各模块自带 QoS（否决：T1 无全局 profile [EV-T1P-57]） | §6.5.3.8 |
| DD-SP-08 | 本体融合（EKF 里程计）独立服务，不进通用管线 | 作管线算子（否决：有状态+高频+独立参数体系 [EV-T1P-51]） | §6.4.3 |
| DD-SP-09 | 高频本体流（关节 1kHz/IMU 500Hz）iceoryx 直连、不上 DDS、不过管线 | 统一走管线（否决：时延确定性；T1 生产模式连 DDS 都不出板 [EV-T1P-52]） | NFR-SP-03/04 |
| DD-SP-10 | 质量随流：质量作为消息字段传导+低频汇总，不另建旁路探测 | 独立质量探测模块（否决：重复订阅大带宽流） | [EV-T1P-43][EV-T1P-44] |
| DD-SP-11 | 结果不出板为硬契约（图像/原始点云禁跨板） | 跨板传原始流（否决：T1 实测板间 2Mbps 结论——任何一路视频都超预算 [EV-T1P-59]） | FR-SP-12/NFR-SP-05 |

---

## 6.8 验证与测试考虑

| 层级 | 用例族 | 覆盖需求 |
|---|---|---|
| 单元 | 算子库：体素/离群/时域确认/目标剔除等逐算子正确性（合成点云） | FR-SP-05/06 |
| 单元 | 同步算子：新鲜度/滑窗/插值边界（乱序/丢帧/时戳跳变） | FR-SP-03 |
| 集成 | 标定链路：入库→校验→发布→消费一致性；篡改检测；跨板不一致注入 | FR-SP-04 |
| 集成 | 管线确定性：同一 bag 回放逐帧比对（NFR-SP-06） | FR-SP-05、NFR-SP-06 |
| 集成 | 质量链路：遮挡/过暗/离线注入→降级信号→任务门控联动 | FR-SP-07、TS 域 FR-TS-07 |
| 集成 | 供电流控：掩码切换幂等/就绪回报/与状态动作联动 | FR-SP-08 |
| 系统（实机） | 时延预算：相机端到端、ObstacleCheck P99、odom 频率与时戳 | NFR-SP-01/02/03 |
| 系统（实机） | 跨板带宽：业务态/待机态实测（对标 T1 ≈2Mbps 基线 [EV-T1P-59]） | NFR-SP-05 |
| 系统（实机） | 资源预算：静置/跟随/建图三档场景计量（对标 T1 资源基线 [EV-T1P-59]） | NFR-SP-07 |
| 系统（实机） | 对标复现：T1 类场景（过暗禁跟随/ToF 遮挡告警/跟随目标从点云剔除） | FR-SP-07/10 |

---

## 6.9 开放问题

| 编号 | 问题 | 影响 | 建议 |
|---|---|---|---|
| OP-SP-01 | 传感器组合基线（双目+前 ToF 起步，还是前+后 ToF，是否引入激光） | 管线配置与标定体系规模 | 与硬件联合评审；框架按可裁剪设计已留余地 |
| OP-SP-02 | 音频前端归属：算子归本章（HAL 插件），唤醒/波束专有 SDK 的参数外露程度 | 与 VI 章边界 | 专有 SDK 参数不强制外露，但质量指标须随流（对标 T1 VTN 参数不外露现状 [EV-T1P-53]） |
| OP-SP-03 | 在线标定（pitch observer 类）产品化程度：观测 only 还是闭环修正 | 标定服务复杂度 | V1 观测+告警，V2 评估闭环 |
| OP-SP-04 | 深省电（PS_DEEP）下感知流的恢复时延指标（断流→可用） | 功耗与体验权衡 | 与 TS 章 OP-TS-05 联合定标 |
| OP-SP-05 | 感知场景与 TS 资源场景的联编粒度（一对一映射还是能力矩阵） | 配置治理复杂度 | 场景库联编 CI 先行，粒度评审定 |
| OP-SP-06 | 多机同款产品的标定产线流程（一机一档的生成与入库自动化） | 量产一致性 | 与制造工程联合定义，早于 EVT |
| OP-SP-07 | 开源许可证审查：YOLOv8（AGPL-3.0）、CLIP-ReID/SOLIDER（研究性许可）、DTLN 自训权重商用合规 | 法务/商用风险 | 商用前完成清单化审查；必要时替换为宽松许可替代（Apache/MIT 系，如 RT-DETR 检测、开源 ReID 替代） |

---

## 6.10 对标证据引用清单

> 编号接续第 5 章（EV-T1P-01..41）。路径缩写：`RK`/`ORIN`＝backup_20261102 两板 `/robot/software` 前缀。

| 证据 | 内容 | 来源 |
|---|---|---|
| EV-T1P-42 | coreon_fusion 结构：11 个自研 so（scene=避障/绕障/跟踪/占据栅格主体、action=ObstacleCheck、config、utils、runner×5、engine_tensorrt、tc-engine）；tools（avoid_aimrt2bag 录制回放/coreon_log_diagnosis/ground_calibration 地面标定/tof_check）；pipeline.json 构建信息 | B：`ORIN/coreon_fusion/{lib,bin,cfg,tools}`、`version.json`、`pipeline.json` |
| EV-T1P-43 | coreon_fusion 通道配置：channel.backends=ros2+local+iceoryx、服务回调独立互斥组；订阅声明 33 话题（含 `_orin`/`bgr_centra`/`metoak`/`pmd_royale` 跨机型遗留）；5×ToF 点云走 iceoryx、sensor_info 走 ros2；传感器表（8 sensor_item、routes、freshness_threshold_sec: 0.1、default_target_fps 30、timeout 100ms）；发布 7 路（target_info/velocity 改写/融合点云/避障状态/trace/诊断/sm 心跳） | B：`ORIN/coreon_fusion/bin/cfg/coreon_fusion_config.yaml:20-423` |
| EV-T1P-44 | avoidance_config_t1.yaml（634 行）预处理参数全集：点云采样（row_step 288/height 190/sample_step 2/无效比阈值 0.99）、遮挡诊断（队列 3/无效比 0.96/低曝光 800/一致性窗 150ms/确认恢复各 5 帧）、采样点裁剪、光心脏污分析（深度带 0-0.35m/体素 0.015/SVD 判据/5 帧窗）、地面分割 RANSAC（阈值 0.03/坡度按形态 15°-30°）、碰撞盒（狗 0.75×0.5×0.55/轨迹预测 3s/稀疏簇过滤）、局部绕障栅格（0.025m/96×64）、IMU 姿态安全（orientation_max_age 300ms）、9 组 optical→camera 外参内联+human_main_pitch_observer（在线俯仰观测）+dog_head_extended_transform；fused_obstacle_assist（体素 0.05/去重 0.075/动态类 11,13,14/玻璃镜面类 17,18） | B：`ORIN/coreon_fusion/bin/cfg/avoidance_config_t1.yaml`（L18-624） |
| EV-T1P-45 | coreon_fusion 无独立预处理 so：符号分布——scene 库含 detectGround/extractNonGroundUsingPlane/removeExactDuplicates/FilterT1TofSmallNoise/T1TofOriginNoiseAnalyzer/traversability::ProjectObstacleCloudToGround；runner 自带 PreProcess（PercepFusion/Yolov8/Face/Reid）；PercepFusionRunnerBase 含 DecodeImage/PrepareNchwFloatInput/FilterDisparity/BuildDisparityFromStereoOutput/GeneratePointCloud；scene_percep_fusion.yaml 内联内参 fx 288.13/baseline 0.06；tracking_params（OCSort det 0.45/ReID 128×256 归一化/深度 scale 0.001+ROI 四阶段 S1-S4+EMA/相机内参+rgb2tof 外参在此重复一份） | B：`ORIN/coreon_fusion/lib/*.so` nm 符号、`bin/cfg/scenes/scene_percep_fusion.yaml`、`cfg/track_config_files/tracking_params_tensorrt.yaml` |
| EV-T1P-46 | hal_rgbd（orin）ToF 数据面：V4L2 5 路（I2C/V4L2 映射）→Ofilm SDK（libdepthcomputation）→AimRT；每路 HARDWARE_BINNING/model_spc_path（标定）/model_ini_path（滤波参数）/自动曝光/输出开关（点云开、深度与 IR 关）/publish_frequency 20；滤波 ini 26 项（amplitudeThreshold 6.0/flyPixAngleLimit 0.3/mpi*/noiseFilterSigma*/smoothingAlpha 0.3/saturation*/useMPI/useRemoveStrayLight…）5 路仅 rear 的 autoExposureQuantile 差异；spc 5 个文件 md5 互不相同且与 protected 分区一致；PWM 时戳节点（pwm_ts0/1+bind_timestamp_trigger）；inter_board 同步话题；QoS best_effort+transient_local | B：`ORIN/hal_rgbd/bin/cfg/t1_v2d1/t1_v2d1_config.yaml:90-363`、`cfg/t1_v2d1/filter/filter_config_*.ini`、`doc/CLAUDE.md`、spc md5 实测 |
| EV-T1P-47 | rk exposure ToF 控制面：5 路 I2C 映射+订阅 inter_board+5 路 sensor_info 回写曝光；FSYNC 脉冲丢失监测诊断；setlight.sh 经 i2ctransfer 直写解串器设曝光模式（10ms/5ms） | B：`RK/hal_rgbd/bin/cfg/exposure/exposure_config.yaml:131-187`、libexposure_module_pkg.so strings、`RK/hal_camera/bin/setlight.sh`、em_run.sh:126-132 |
| EV-T1P-48 | hal_camera 采集侧预处理：orin——calibration_file=protected sensor_calib_params、双目 2592×1944 ldc_enable fov_scale 0.5（CUDA ldc_cuda+NvBufSurface/VPI）、鱼眼条目为本机无硬件的 Q1 遗留、soc_sync 门控 80s、逐话题 QoS 表；rk——use_dmabuf、左目 BGR 流+NV12 第二流 864×648（四档可选/stride 16 对齐）、rotate_angle_dog=180（形态旋转）、OpenCL LDC+RGA、BMI08 IMU 100Hz、soc_sync 超时 86400s、跨板标定同步脚本整体注释停用+default_param 兜底 | B：`ORIN|RK/hal_camera/bin/cfg/*.yaml(+.dump)`、二进制 strings（k_remap_uyvy/ldc_cuda/CodecRK::ensureNV12ScaledDmabuf/rgaRotateJpegNv12/ldc_opencl_nv12）、em_run.sh:45-305 |
| EV-T1P-49 | percep：通道（双目+3 路 ToF 走 iceoryx，控制类走 ros2）；ImageProcess（Undistortion false/Rectification true/up_focal_scale 0.5/view_scale 2.8→640×480，目标框 864×648+四足旋转 180）；stereo_sync require_new+max_delay 20ms；Fusion（downsample 2/视差域 0.001-192/sobel 视差边缘滤除/玻璃平面 RANSAC）；tof_denoise（体素 0.05/组织 288×190/col_stride 2/连通分量 min 6/时域确认 1 帧 TTL 350ms IoU 0.40/双目互证）；代价图（10m/0.05m/log-odds hit 1.10 miss 0.35/三层记忆 dynamic 500ms-short 3s-stable 40s/形态地形代价表）；楼梯检测（台阶高 0.05-0.15/确认 2 帧）；target_removal（半径 0.90/深度容差 0.60/掩膜膨胀 10px）；标定三文件（camera_intrinsic_T：双目 fisheye+tof 内参+stereo_ext+T_cam_tof+IMU 误差项；sensor_extrinsics_T：md5+标定时间戳；t_extrinsics：形态×传感器双外参制） | B：`ORIN/algorithm/perception/config/{percep_aimrt.yaml,PercepParams_T.json,camera_intrinsic_T.yaml,sensor_extrinsics_T.yaml,t_extrinsics.yaml}` |
| EV-T1P-50 | nav2_perception：pointcloud_combiner——输入 /percep/tof/{rear,front}（命名与物理安装相反注释）→TF 变换拼接（target_frame 按形态）→combined，publish_rate 20Hz/max_cloud_age 0/transform_timeout 0.05/require_both_inputs false，内含 2 个静态 TF 发布器；perception_node——VoxelGrid 0.1（统计滤波/拖尾噪声滤波/关节自点云剔除 joint_state 桥均备而未启用）、距离滤波 0.4-3.0m 启用、publish 15Hz、row/col step、frame_id 仅改标签 | B：`ORIN/algorithm/nav2_perception/share/nav2_perception/launch/pointcloud_combiner_t1.launch.py:60-125`、`ORIN/algorithm/nav2_bringup/.../nav2_t1_{wheel,dog}.yaml:425-499` |
| EV-T1P-51 | legged_odom：EKF（误差状态）全参数——过程噪声 position 0.02/velocity 0.05/foot 0.001，观测噪声 foot 0.01/0.05；无接触脚噪声放大 ×1000/×200/×100000；IMU bias 上电标定 300 帧+运行中静止重标定（站立 3s/最小间隔 600s/gyro_bias_abs_max 0.35）；触地检测（RL 膝力矩阈值 L3/R2+接触置信度状态机 0.65/0.35/α0.35/保持 2 帧）；滑动平均（关节窗 1/IMU 窗 2）；缓冲降采样 imu 100Hz/joint 250Hz；输出抽取 odom ÷2、躯干姿态 ÷50（→10Hz）；URDF 运动学+MC 动作门控；sync_threshold_sec 0.05 | B：`RK/legged_odom/bin/cfg/params_legged_odometry_qd1.yaml`、`legged_odom_qd1.yaml:45-176` |
| EV-T1P-52 | device_manager：joint/state publish_interval_ms 1（1kHz）、imu/torso 500Hz，enable_backends 默认 iceoryx（仅 MC_LOW_LEVEL_DEV=true 切 ros2→生产模式跨板拿不到关节流）；500ms 诊断唯一 DDS 出口；CAN FD 1M/5M、14 关节 MIT 参数表 | B：`RK/device_manager/bin/cfg/t1_v2d0_config.yaml:129-258`、em_run.sh:31-37 |
| EV-T1P-53 | 音频前端：PipeWire webrtc AEC（noise_suppression/high_pass/extended_filter/delay_agnostic/voice_detection 开，node.latency 1920/48000）；Agent 侧 omnis_sdk——silero_vad.onnx（threshold 0.5/min_speech 450ms/rms -50dB）+DTLN 双模型 AEC；讯飞 4 麦（circle4/line4 阵型映射、ref 2 通道、16k/512 采样），唤醒/波束在专有 so 参数不外露；重采样前端 hp 80Hz/lp 7kHz；AEC 后音频 /agent/process_audio_output | B：`RK/audio_manager/bin/aec-native.conf.in`、`RK/aimrt_agent/bin/cfg/omnis_sdk/config/omnis_sdk_config.json`、`t1/iflytek_engine_config.json`、`aw_resample_config.json`、agent.yaml:127-129 |
| EV-T1P-54 | person_track：main_loop 33ms（≈30Hz）；use_gpu_resize+use_combined_remap（resize/去畸变/旋转一次 remap）；fx_fy_scale 0.5 全局缩放；rectified_view_restore（恢复上游 LDC 0.5 焦距——上下游变换未对齐证据）；external_intrinsics_file 启动覆盖 catalog（外参遗留绝对路径 /home/agiuser/下载/标定/…）；同步窗 rgb/depth/cloud/odom 500ms、rgb-depth 300ms、odom 100ms+历史 20 帧；检测 letterbox 640×640/pad 114/swap_rb//255/to_chw；ReID 128×256 mean/std 0.5；深度 ROI 四阶段（S1-S4 与 coreon_fusion tracking_params 几乎同构）；近场点云 ROI→高度带→体素 0.01→半径离群 0.04/20→DBSCAN；UWB 角度一阶滤波+滞回；当前 T 配置 detector=yolov8n、分割禁用（seg 引擎存在未启用） | B：`ORIN/algorithm/target_follow_perception/bin/cfg/aimrt_person_track_config_T.yaml`、`bin/core/config/config_T/{target_follow_perception.yaml,intrinsics/intrinsics.yaml,algorithm_params.yaml,model_paths.yaml}`、`core/config/uwb/quanji_uwb_filter.yaml` |
| EV-T1P-55 | brightness：订阅单目（ros2+iceoryx 双后端）；灰度均值判定 disable_threshold 82.0、subsample_stride 2、sample_every_n 5、eval 100ms、freshness 1000ms、confirm 1000ms（防闪烁）；活跃时 10Hz 广播；头注「与感知模块完全解耦」 | B：`ORIN/algorithm/brightness_detection/bin/cfg/aimrt_brightness_status_config_T.yaml:1-116` |
| EV-T1P-56 | 重复度矩阵：点云滤波 6 处（hal_rgbd ini/coreon origin_noise/coreon fused_assist/percep tof_denoise/nav2 perception_node/person_track near_field）；图像 resize/去畸变 5 处（双板 LDC/percep/person_track/coreon runner/aimrt_slam resize 640+crop）；深度→点云 ≥3 处；时间同步 6 种策略；深度 ROI 四阶段两套同构；外参 ≥6 处分散 | B：综合上述各模块配置交叉比对 |
| EV-T1P-57 | 传输层：各 aimrt 包自带 iox-roudi/aimrte 运行时（20+ 份副本）；roudi mempool 含 18874368B×10「用于大分辨率 RGB 图像」段；dmabuf 双板启用；QoS 各模块自带（无全局 profile）；FastDDS xml（SHM 8MB/UDP 缓冲 10MB/interfaceWhiteList） | B：`ORIN/hal_camera/bin/cfg/roudi_config.toml`、`ORIN/entry/cfg/ros_dds_configuration.xml`、find 实证 |
| EV-T1P-58 | 标定管理：sensor_calib_params.yaml 双板 diff 为空（逐字节一致，事实统一）；spc 双板 md5 一致；外参分散——coreon 内联 9 组+protected avoid 副本（同值双拷贝）、percep 两套外参文件、person_track 4 形态外参+遗留绝对路径、aimrt_slam 内联、legged_odom URDF×8、nav2 静态 TF 发布器；hal_camera 跨板标定同步脚本整体注释停用+default_param 兜底；无统一标定服务 | B：`BK/*/robot/protected/camera/`（diff/md5 实测）、各模块外参文件清单、`ORIN/hal_camera/bin/em_run.sh:144-305` |
| EV-T1P-59 | c4 实测跨板边界：ToF 控制面在 rk（I2C/V4L2）、数据面在 orin；板间 ≈2Mbps（155KB/s 下行+80KB/s 上行）远低于任何一路视频（NV12 864×648@10 ≈67Mbps）→视频零跨板；静置负载 hal_camera(orin) 42.9%/hal_rgbd 38.9%/rk hal_camera 13.9%；板间 RTT 0.43-0.76ms；感知消费方配置实证（percep 订阅本地双目+ToF） | C：`docs/primebot/on_device_measured_data/c4_sensor_topology_20261031.md` §3/§5/§8；A：§6.3 |
| EV-T1P-61 | T1 Pro AI 模型开源同款清单（文件实测）：orin——yolov8s-seg/yolov8n（ultralytics）、CLIP-ReID ViT-B/16 b1/b3/b5、SOLIDER Swin-Tiny（微软）、EigenPlaces/SuperPoint/YOLO26-nano-seg/PP-OCR（slam 链，部署未运行）；rk——silero_vad.onnx（snakers4/silero-vad 同款）、DTLN 架构公开自训权重、sherpa-onnx KWS；推理栈 onnxruntime 1.19.2/RKNN 2.3.2/MNN≈3.5/sherpa-onnx 1.12.15 均开源（TensorRT 闭源公开分发） | A：§6.1.2、§6.1.3 |

---

## 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| V0.1 | 2026-11-10 | 首版 | liqiliang |
| V0.2 | 2026-11-10 | 新增 §6.6 功能、规格与工作量分析（含参考开源实现对照、代码量与工作量估算）；原 §6.6–6.9 顺延为 §6.7–6.10；新增 OP-SP-07、EV-T1P-61 | liqiliang |
| V0.3 | 2026-11-11 | §6.6.3 对照表：功能简称→功能名称、新增功能简介列、参考实现列两行式并附核实仓址 | liqiliang |
| V0.4 | 2026-11-11 | 新增 §6.6.5 端到端场景走查（SP 视角） | liqiliang |
| V0.5 | 2026-11-12 | 感知服务归属调整（暂定）：平台 → 小脑——§6.1.1/6.3.1 归属声明、FR-SP-09/10/11 主语改「SP 域（感知服务类，归小脑·暂定）」、图 6-1/职责矩阵标注；设计基线与部署不变 | liqiliang |
| V0.6 | 2026-11-19 | 代码量单位统一为 K LoC（对照表/汇总 20 处，数值不变） | liqiliang |
| V0.7 | 2026-11-19 | **接口前缀改 `/robot/` 并回靠 T1 命名（与第 3 章 V0.20 同步）**：① §6.5.4 IF 表 12 条目 `/qdog/`→`/robot/`；② **IF-SP-05 回靠 T1 双服务形态**——`/qdog/sensor/power`（SensorPower.srv）→ `/robot/sensor/set_camera_stream`、`set_tof_stream`（`SetCameraStream.srv`/`SetTofStream.srv`，对标 SetHalCameraStream/SetHalTofStream 的电源+流双掩码语义）；③ **IF-SP-08 `targets`→`target_info`**（沿用 T1 叶名，与图 3-5 一致）；④ IF-SP-12 消息包 qdog_msgs→robot_msgs；⑤ §6.5.3 管线 yaml 示例同步；EV 证据引用按原文不改 | liqiliang |
