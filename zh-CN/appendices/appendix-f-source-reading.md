---
layout: default
title: "附录 F 生产源码阅读路线"
nav_order: 341
parent: "附录"
---

# 附录 F 生产源码阅读路线

读源码时不要从顶层目录顺序阅读。建议按控制流程阅读。

## 第一阶段：领域模型

1. 阅读 `Site`、`Road`、`Phase`、`PhaseStage`。
2. 阅读 `SplitPlan`、`SplitPlanDetail`、`CyclePlan`、`OffsetPlan`。
3. 阅读 `ControlPlan`、`DayPlanInfo`、`SchedulePlanInfo`。

## 第二阶段：算法输入

1. 阅读 `AiComputeController`。
2. 阅读 `AiComputeServiceImpl`。
3. 阅读 `IAiCommputeClient`。
4. 对照 `apiserver.py` 路由。

## 第三阶段：单点算法

1. `single_opt.py`
2. `minute_single_adaptive.py`
3. `cycle_single_adaptive.py`
4. `althms/adaptive_single.py`
5. `flowinfra/algorithms/webster.py`

## 第四阶段：子区算法

1. `subregion_opt.py`
2. `minute_subregion_adaptive.py`
3. `maxband.py`
4. `green_wave.py`
5. `green_wave_band.py`

## 第五阶段：运行与设备

1. `ControlServiceController`
2. `IControlService`
3. 实时周期和阶段服务
4. 厂商适配器
5. `offline-dw-flinkjob-parameter-java` 的 Kafka/Flink 作业

## 第六阶段：前端

按菜单顺序阅读：

```text
基础信号控制
AI 辅助控制
AI 自动控制
分区管理
任务管理
控制评价
调控日志
```
