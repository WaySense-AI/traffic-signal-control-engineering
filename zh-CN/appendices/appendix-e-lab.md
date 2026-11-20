---
layout: default
title: "附录 E SignalLab 实验环境"
nav_order: 331
parent: "附录"
---

# 附录 E SignalLab 实验环境

SignalLab 是书稿配套的教学系统，独立仓库根目录为 `signal-lab/`。它要求 Python 3.9 或更高版本，只使用标准库；实验不连接生产仓库、生产消息或真实信号机。

书稿仓库里保留了同名目录 `signal-lab/`；如果读者克隆的是独立仓库，已经位于该目录，不需要再执行 `cd`。

## E.1 运行方式

在书稿仓库根目录执行：

```bash
cd signal-lab
python3 run_all.py
```

在独立仓库根目录直接执行：

```bash
python3 run_all.py
```

`run_all.py` 依次运行 57 个单元测试和 8 个实验，全部通过时最后一行是：

```text
SignalLab: 57 tests, 8 examples passed
```

也可以分开运行：

```bash
# 只跑测试
python3 -m unittest discover -s tests -v

# 只跑实验
python3 run_all.py --examples-only

# 只跑某一个实验
python3 -m examples.timeline_lab
```

所有实验使用合成数据。输出是当前输入下的确定性结果，不是现场效果证明。

## E.2 时间轴实验：timeline_lab

对应第 8、16、18 章。实验使用 S2 的 150 秒三阶段方案：

```text
A：纯绿 59 s，清空 8 s，总时长 67 s
B：纯绿 41 s，清空 8 s，总时长 49 s
C：纯绿 26 s，清空 8 s，总时长 34 s
```

运行：

```bash
python3 -m examples.timeline_lab
```

需要检查：

1. 三个阶段窗口是否无重叠地覆盖 `[0, 150)`；
2. 纯绿累计是否为 126 秒；
3. 跨界绿灯窗 `[26, 85)` 为什么包含 26 和 84，不包含 25 和 85；
4. 把窗口平移到周期末尾后，`green_at` 是否仍按半开区间判断。

输出里的 `stage_windows`、`green_seconds_counted` 和 `wrapped_green` 分别对应上面四项检查。改周期、阶段纯绿或偏移，再观察窗口起点和跨界判断如何变化。

## E.3 数据质量实验：experiment_quality

对应第 5、6 章。实验对一段检测序列做时间异常和物理异常检查：

```bash
python3 -m examples.experiment_quality
```

当前合成序列中：

- 第 4 点流量 500 veh/h，被标记为时间异常；
- 第 6 点流量 2 veh/h、排队 30 辆，被标记为物理矛盾；
- 其余点没有异常标记。

修改 `span`、`sigma` 或异常点数值，比较检测灵敏度。需要回答：时间异常和物理异常分别依赖什么参照；为什么“低流量、高排队”不是单点阈值能完全解释的。

## E.4 周期实验：experiment_cycle

对应第 10、11 章。实验比较分段线性周期模型、Webster 周期和整数绿时分配：

```bash
python3 -m examples.experiment_cycle
```

当前输入下输出五组需求：

```text
demand  model_cycle  webster_cycle  green_seconds
0.30    70           59             18,15,13
0.45    82           75             24,18,16
0.60    95           102            31,22,18
0.75    122          164            44,30,24
0.90    150          180            58,39,29
```

重点观察：

1. 关键流量比增大时，两个周期模型为什么不是同速增长；
2. 周期达到模型上界后如何限幅；
3. 三个阶段绿灯如何重新分配；
4. 哪个阶段最先触发最小绿约束。

把分段线性模型的标定点改成现场数据，再运行一次；不要只比较最后一个周期值，要同时看绿灯分配和最小绿修复。

## E.5 排队实验：queue_lab

对应第 1、7 章。实验固定周期为 90 秒、有效绿为 27 秒、饱和流率为 1800 veh/h。每周期服务能力为：

\[
D=\frac{1800\times27}{3600}=13.5\text{ veh}
\]

运行：

```bash
python3 -m examples.queue_lab
```

900 veh/h 的需求每周期到达 22.5 辆，因此每个周期净增加 9 辆排队。运行前先预测连续六个周期的队列，再运行程序。当前输出中：

- 固定方案末周期排队为 35.5 辆；
- 加 20 辆存储上限后，本地排队封顶在 20 辆；
- 累计溢出为 15.5 辆。

需要说明为什么“本地排队”和“上游溢出”需要分别记录。把存储容量改为 10 辆或 40 辆，观察溢出如何变化。

## E.6 协调实验：experiment_coordination

对应第 15 至 18 章。实验比较四组偏移下的正向带宽：

```bash
python3 -m examples.experiment_coordination
```

当前输出：

```text
aligned:          offsets=(0, 0),  band=30 s
travel matched:   offsets=(0, 10), band=40 s
early downstream: offsets=(0, 5),  band=35 s
late downstream:  offsets=(0, 25), band=25 s
```

需要解释：为什么“行程匹配”得到最大带宽；为什么早到和晚到都不是最优；扫描值和解析值是否一致。

改变路段行程时间、周期或绿窗，重新比较四组偏移。不要把带宽最大直接当成延误最小；带宽只说明绿窗的几何重合。

## E.7 走廊实验：corridor_case

对应第 24 章。实验直接运行 S1～S4 四路口走廊：

```bash
python3 -m examples.corridor_case
```

当前输出中的关键值：

```text
public_cycle_s = 150
cumulative_travel_times_s = [0, 26, 58, 76]
forward_band_s = 53
bad_s2_offset_band_s = 29
batch_status = partial
```

需要检查：

1. 公共周期 150 秒是否压低了某个路口的自然周期；
2. 累计行程时间 26、58、76 秒如何得到；
3. 把 S2 的偏移改错后，正向带宽为什么从 53 秒降到 29 秒；
4. 批次状态为什么是 `partial`，而不是 `observed`。

把 S2 的东直需求、路段长度或协调速度改掉，重新计算公共周期、偏移和带宽。走廊实验把前六部分的周期、偏移、带宽和命令状态放在同一个案例里。

## E.8 端到端实验：end_to_end_demo

对应第 1.7、19、21、24.9 节。实验从车道观测走到需求、周期、绿灯和命令状态：

```bash
python3 -m examples.end_to_end_demo
```

当前输出：

```text
cycle = 150
stage_flow_ratios = {A: 0.5, B: 0.3125, C: 0.1517}
stage_green_s = {A: 59, B: 41, C: 26}
common_cycle = 150
downstream_offset_s = 24
command_status = observed
```

需要按顺序复算：车道流量如何合成流向需求，阶段流量比如何得到，周期如何取整，绿灯如何分配，偏移如何计算，命令状态如何从 `accepted` 走到 `observed`。

把东直流量从 600 改为 360，保持饱和流率不变，再运行一次；观察流量比、周期、绿灯和命令状态哪些变了、哪些没有变。

## E.9 恢复能力实验：resilience_lab

对应第 14、21 章。实验构造 S1～S4 批次下发中的失败、重复和部分成功：

```bash
python3 -m examples.resilience_lab
```

当前输出：

```text
batch_status = partial
S1 = observed
S2 = observed
S3 = failed
S4 = dispatched
duplicate_was_inserted = false
duplicate_resolved_version = S1-v42
```

需要回答：

1. 批次为什么是 `partial`，而不是 `failed` 或 `observed`；
2. 重复提交同一 `command_id` 为什么不生成新命令；
3. 为什么设备接受、发送完成、运行确认是三个不同状态；
4. 部分失败后为什么可能选择回滚、把失败路口拆出协调组或保持等待。

把失败点从 S3 改到 S4，或让 S4 在超时后才上报，重新观察批次状态和重复命令处理。

## E.10 实验记录格式

每个实验都应保留一份可复核记录：

具体见表 E-1。
表 E-1 实验记录格式
| 字段 | 内容 |
|---|---|
| 预测 | 运行前根据公式或时间图写出的数值和状态 |
| 输入 | 参数、单位、版本和随机种子（若有） |
| 观测 | 程序输出、日志和失败原因 |
| 不变量 | 周期闭合、车辆守恒、状态顺序或时间覆盖 |
| 解释 | 预测与观测一致或偏离的原因 |
| 修正 | 下一轮实验准备改变的唯一变量 |

只记录最后一个输出，无法判断模型、程序和解释哪一处出现偏差。

## E.11 实验与正文对应

八个可运行实验与章节的对应关系如表 E-2 所示。

表 E-2 八个可运行实验
| 实验 | 模块 | 对应章节 |
|---|---|---|
| 时间轴 | `examples/timeline_lab.py` | 第 8、16、18 章 |
| 数据质量 | `examples/experiment_quality.py` | 第 5、6 章 |
| 周期 | `examples/experiment_cycle.py` | 第 10、11 章 |
| 排队 | `examples/queue_lab.py` | 第 1、7 章 |
| 协调 | `examples/experiment_coordination.py` | 第 15～18 章 |
| 走廊 | `examples/corridor_case.py` | 第 24 章 |
| 端到端 | `examples/end_to_end_demo.py` | 第 1.7、19、21、24.9 节 |
| 恢复能力 | `examples/resilience_lab.py` | 第 14、21 章 |

## E.12 建议的实验顺序

如表 E-3 所示。

表 E-3 建议的实验顺序
| 顺序 | 实验 | 先掌握什么 |
|---|---|---|
| 1 | 时间轴 | 半开区间、阶段覆盖和偏移归一化 |
| 2 | 数据质量 | 异常、缺失和置信度 |
| 3 | 周期 | 周期模型、限幅和绿灯分配 |
| 4 | 排队 | 服务能力、排队增长和溢出 |
| 5 | 协调 | 公共周期、行程时间和带宽 |
| 6 | 走廊 | 四个路口的偏移和带宽 |
| 7 | 端到端 | 从检测到命令的完整链路 |
| 8 | 恢复能力 | 部分失败、幂等和回滚 |

## E.13 扩展原则

新增实验需要做到：

1. 使用合成数据；
2. 明确单位；
3. 对非法输入抛出明确异常；
4. 为核心安全约束增加测试；
5. 同时记录预测、观测和失败原因；
6. 在表 E-2 中登记对应章节和运行命令。
