---
layout: default
title: "附录 D Java 与 Python 接口映射"
nav_order: 321
parent: "附录"
---

# 附录 D Java 与 Python 接口映射

如表 D-1 所示。
表 D-1 Java 与 Python 接口映射
| Java 调用意图 | Python 路由 | 主要用途 |
|---|---|---|
| 单点方案计算 | `GET /get_site_pattern_lib` | 路口方案推荐 |
| 子区方案计算 | `POST /get_region_pattern_lib` | 子区协调和时段方案 |
| 时空图 | `POST /gettimespace` | 双向绿波带 |
| 单点自适应 | `POST /singleadaptive` | 单点实时调整 |
| 子区自适应 | `POST /subadaptive` | 子区实时调整 |
| 周期自适应 | `POST /cycleadaptive` | 周期级调整 |
| SDK 单点优化 | `POST /lightflow/singlenodeopt` | 测试或 SDK |
| SDK 子区优化 | `POST /lightflow/subareaopt` | 测试或 SDK |
