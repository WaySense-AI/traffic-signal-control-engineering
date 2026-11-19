---
layout: default
title: "附录 B 交通控制公式速查"
nav_order: 301
parent: "附录"
---

# 附录 B 交通控制公式速查

## 饱和流率

```text
S = 3600 / saturation_headway_seconds
```

## 流量比

```text
y = q / S
```

## 平均容量

```text
c = S * effective_green / cycle
```

## 饱和度

```text
x = q / c
```

## Webster 周期

```text
C0 = (1.5 * L + 5) / (1 - Y)
```

`Y >= 1` 时公式没有有限的非负周期，应进入过饱和控制而不是直接截断使用。

## 阶段时间分配

```text
available_green = cycle - sum(clearance)
extra_green = available_green - sum(minimum_green)
green_i = minimum_green_i + extra_green * weight_i / sum(weight)
```

## 理论行程时间

```text
travel_time = distance / speed
```

## 下游相位差

```text
offset_down = (offset_up + travel_time) mod common_cycle
```

公式方向必须与相位差字段的实际定义一致。

