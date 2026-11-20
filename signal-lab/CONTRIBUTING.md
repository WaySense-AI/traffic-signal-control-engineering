# Contributing

## 环境

- Python 3.9 或更高版本
- 只使用标准库，不引入第三方运行时依赖
- 不需要 `pip install`，也不需要网络

## 运行位置

书稿仓库中先进入 `signal-lab/` 目录；克隆独立仓库时，根目录即该目录。

```bash
cd signal-lab      # 书稿仓库中
python3 run_all.py
```

## 提交前

要求 57 个测试和 8 个实验全部通过，最后一行是：

```text
SignalLab: 57 tests, 8 examples passed
```

## 修改原则

- 新机制先加测试，再改实现；
- 不修改测试来掩盖实现问题；
- 教学案例使用合成数据，不提交生产凭据、客户信息或内部系统名；
- 公开示例保持可重复运行，输出具有确定性；
- 若环境会写入字节码缓存，使用 `PYTHONDONTWRITEBYTECODE=1`。
