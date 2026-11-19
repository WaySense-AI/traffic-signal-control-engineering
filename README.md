---
layout: default
title: "交通信号控制工程：数据、配时与执行"
nav_exclude: true
permalink: /
---

# 交通信号控制工程

**数据、配时与执行**

交通信号控制不只是配时公式和优化算法。它从一条车道检测记录开始，经过数据质量、需求计算、周期与绿信比、协调优化、命令下发、设备确认和效果评价，最后回到下一次控制。本书沿着这条链，把交通工程、软件系统和现场执行放进同一个工程框架。

## 这本书讲什么

- 路口、相位、阶段、环、屏障和方案的对象模型；
- 检测、补全、车道映射、容量、饱和流率和实时状态；
- Webster、约束优化、单点自适应、公共周期、相位差和 MaxBand；
- Kafka/Flink 数据链路、Java/Python 服务边界、方案下发、确认与回滚；
- 控制效果评价、四路口端到端案例和生产源码走读；
- 一套可运行的 SignalLab 教学系统，用合成数据和固定算例验证书中结论。

## 结构

全书 7 个部分、28 章、12 个附录：

1. 从路口到系统
2. 从交通到控制输入
3. 单点信号控制
4. 区域协调控制
5. 平台工程
6. 评价与综合实践
7. 生产源码精读

书稿当前版本为 **v3.19**（2026-11-19）。仓库正在整理书稿、插图和 SignalLab 代码；正式版本以 Release 为准。

## 仓库内容

```text
zh-CN/          书稿 Markdown 源文件（Jekyll 页面）
figures/        正式插图与部分题图
signal-lab/     可运行的 SignalLab 教学代码
release/        发布元数据；PDF/DOCX 将作为 Release 附件
```

本仓库已包含书稿、插图、SignalLab 代码和公开构建工具；正文仍在校对，正式版本以 Release 为准。

## 许可

- **书稿正文、插图与合成数据**：CC BY-NC-SA 4.0，见 [LICENSE-CONTENT](LICENSE-CONTENT)。
- **SignalLab 代码**：MIT，见 [LICENSE-CODE](LICENSE-CODE)。
- **排版字体**：Noto Sans SC / Noto Sans Mono CJK SC，SIL OFL 1.1；见 [NOTICE](NOTICE) 和 [licenses/OFL-1.1.txt](licenses/OFL-1.1.txt)。
- **第三方工具和材料**：见 [NOTICE](NOTICE)。

本书不允许将正文或插图用于商业目的；引用、转载或改编需署名，并以相同方式共享。代码与正文分许可，使用代码时适用 MIT。

书中的生产代码片段由作者及原生产系统权利人授权，用于工程分析与教学引用；不构成独立代码许可，也不构成生产部署许可。

## 引用

如果本书或 SignalLab 对你的研究或工程工作有帮助，请按 [CITATION.cff](CITATION.cff) 引用。

## 参与

Issue 和 Pull Request 用于报告书稿错误、复现实验问题或改进 SignalLab。涉及生产系统、客户数据或未公开接口的内容，请不要提交到公开仓库。
