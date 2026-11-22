# MC interfaces

[MC_INTERFACE_CATALOG.md](MC_INTERFACE_CATALOG.md) 汇总了 `aimdk_msgs` 中与 MC/关节相关的 89 个 `.msg/.srv` 原文，按 `action/common/motion/msg/srv` 分组。

这是 T1 真机接口语义的直接证据，但**不等于** `libmc_common_runner.so` 的 C++ ABI；Runner 的领域接口应按 Collie 自己的 `IRunner` 设计。
