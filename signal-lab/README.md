# SignalLab

SignalLab 是《交通信号控制工程：数据、配时与执行》的配套教学系统。它从最小领域模型开始，把检测窗口、需求换算、周期与绿信比、协调控制、命令状态和效果评价做成可以直接运行、修改和验证的 Python 代码。

- Python 3.9 及以上
- 只使用标准库，不需要安装第三方依赖
- 57 个单元测试，8 个可运行实验
- 案例数据全部为合成数据，不需要网络或外部服务

书稿仓库中的目录名是 `signal-lab/`；独立仓库的根目录就是该目录。

## 快速开始

进入 `signal-lab/` 目录（若克隆的是书稿仓库，先 `cd signal-lab`；若是独立仓库，根目录即该目录）后执行：

```bash
python3 run_all.py
```

它会依次运行 57 个测试和 8 个实验；全部通过时最后一行是：

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
python3 -m examples.end_to_end_demo
```

## 安装为包（可选）

不安装也能运行。若希望在其他脚本中 `import signal_lab`：

```bash
python3 -m pip install -e .
```

```python
from signal_lab import SignalStage, validate_plan
```

本项目不发布运行时依赖。

## 实验

| 模块 | 主题 | 书稿位置 |
|---|---|---|
| `examples.end_to_end_demo` | 从车道观测到方案、命令和评价的完整链路 | 第 1.7、19、21、24.9 节 |
| `examples.corridor_case` | S1～S4 四路口走廊的周期、偏移和带宽 | 第 24.9 节 |
| `examples.experiment_cycle` | Webster、分段线性和整数绿时分配 | 第 10.12、11.14 节 |
| `examples.experiment_quality` | 缺失、异常、置信度和补全 | 第 5.10、6.9 节；附录 E.3 |
| `examples.experiment_coordination` | 公共周期、累计行程时间和带宽扫描 | 第 17.13、18.7 节 |
| `examples.queue_lab` | 周期级排队递推、存储容量和溢出 | 第 1.7、7.7 节 |
| `examples.timeline_lab` | 循环时间轴、半开区间和偏移归一化 | 第 8.8、16.8、18.7 节 |
| `examples.resilience_lab` | 部分失败、幂等、回滚和批次状态 | 第 21.7、24.9 节 |

每个实验都建议按同一顺序记录：

1. 输入和假设；
2. 运行前的预测；
3. 实际输出；
4. 哪条不变量被满足或被破坏；
5. 预测与结果的差异，以及差异来自模型、数据还是实现。

更完整的实验地图见 [docs/experiments.md](docs/experiments.md)。

## 目录

```text
signal-lab/
├── signal_lab/        # 领域模型、算法和状态机
├── examples/          # 8 个可运行实验
├── tests/             # 57 个单元测试
├── docs/              # 实验地图
├── run_all.py         # 一条命令跑测试和实验
├── pyproject.toml     # 可选的包安装配置
└── LICENSE            # MIT
```

持续集成在书稿仓库根的 `.github/workflows/ci.yml`：从 `signal-lab/` 目录跑测试与实验，覆盖 Python 3.9–3.12。

## 范围与边界

SignalLab 是教学系统，不是生产控制器。它用于解释交通信号控制中的时间、需求、约束、执行和评价机制，不能未经审查直接用于控制真实信号机。

## 许可

代码采用 MIT 许可证，见 [LICENSE](LICENSE)。
