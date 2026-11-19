---
layout: default
title: "附录 C 核心数据字典"
nav_order: 311
parent: "附录"
---

# 附录 C 核心数据字典

## 路网

如表 C-1 所示。
表 C-1 路网
| 对象 | 关键字段 | 说明 |
|---|---|---|
| Node | id, type, geom, masterNodeId | 路网节点 |
| Road/Link | upNodeId, downNodeId, length, roadLevel | 有向道路或路段 |
| Site | siteNo, nodeId, factory, master | 受信号控制的路口 |

## 信号结构

如表 C-2 所示。
表 C-2 信号结构
| 对象 | 关键字段 | 说明 |
|---|---|---|
| Phase | phaseNo, controlChannel, currencyPhase, minGreenTime | 同时通行流向和过渡灯色 |
| PhaseStage | phasestageNo, phaseNoList, joint | 阶段控制相位 |
| SplitSequence | phasestageId, sequenceNo | 阶段顺序 |
| SplitPlan | cycleTime, splitValueMode, rSplitPlanId | 周期和绿信比 |
| SplitPlanDetail | splitPhasestageId, phasestageTime, phasestageSign | 阶段时间 |
| OffsetPlan | keySiteId, criticalPhaseStageId, mainOffset | 协调相位差 |

## 调度

如表 C-3 所示。
表 C-3 调度
| 对象 | 关键字段 | 说明 |
|---|---|---|
| ControlPlan | splitPlanId, offsetPlanId | 组合控制方案 |
| DayPlanInfo | siteId, dayPlanNo | 日计划 |
| SchedulePlanInfo | month, day, date, dayPlanId | 调度规则 |

## 实时状态

如表 C-4 所示。
表 C-4 实时状态
| 字段 | 说明 |
|---|---|
| cycleTime | 当前周期 |
| currentTime | 当前周期已运行秒数 |
| currentPhageStageNo/currentStageId | 当前阶段 |
| controlMode | 设备或平台控制模式 |
| source | 数据来源 |
| pushTime | 推送时间 |

