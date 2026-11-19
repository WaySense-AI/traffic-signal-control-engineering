---
layout: default
title: "附录 H 参考资料"
nav_order: 361
parent: "附录"
---

# 附录 H 参考资料

文献按 GB/T 7714—2015 顺序编码制著录，文内用方括号序号引用。

## H.1 经典配时理论

**[1] WEBSTER F V. Traffic signal settings: Road Research Technical Paper No. 39[R]. London: HMSO, 1958.**

第一次把孤立路口的周期、绿信比与流量比、损失时间联系起来，给出后来被称为 Webster 公式的经验模型。

解决的问题：在欠饱和、随机到达的条件下，如何用流量比和损失时间估计“较优周期”。

假设与失效：假设需求稳定、路口孤立、饱和流率已知。过饱和时公式发散，需要限幅或改用排队模型；协调路口不能各自取“最优”。

**[2] WEBSTER F V, COBBE B M. Traffic signals: Road Research Technical Paper No. 56[R]. London: HMSO, 1966.**

在 1958 年模型基础上补充延误公式、现场验证和工程取值。

解决的问题：把“算周期”扩展为“评价周期好坏”，延误成为可比指标。

假设与失效：延误公式基于稳态排队，接近饱和时误差增大；不适用于严重过饱和和溢出。

**[3] AKCELIK R. Traffic signals: capacity and timing analysis: Research Report ARR No. 123[R]. Australian Road Research Board, 1981.**

系统整理通行能力、延误、排队和定时信号配时，给出适合工程使用的计算流程。

解决的问题：把理论公式落成可操作的容量与配时计算方法。

假设与失效：参数依赖本地标定；不同国家的饱和流率、损失时间取值不能直接互换。

## H.2 协调与网络优化

**[4] LITTLE J D C. The synchronization of traffic signals by mixed-integer linear programming[J]. Operations Research, 1966, 14(4): 568-594.**

把干线信号协调写成混合整数线性规划，用整数变量表达周期环绕和相位关系。

解决的问题：把“试偏移”变成可证明最优的数学问题。

假设与失效：假设行程时间已知、速度固定、需求稳定。速度波动或排队溢出时，模型最优不等于现场最优。

**[5] ROBERTSON D I. TRANSYT: a traffic network study tool: RRL Report LR 253[R]. Crowthorne: Road Research Laboratory, 1969.**

用交通模型模拟车队在路网中的离散与传播，以延误和停车次数的加权和为目标，爬山搜索周期、绿信比和相位差。

解决的问题：从单条干线扩展到路网，并第一次把“停车次数”纳入目标。

假设与失效：需求被视为已知常量，优化的是固定配时；对实时需求变化不响应。

**[6] LITTLE J D C, KELSON M D, GARTNER N H. MAXBAND: a program for setting signals on arteries and triangular networks[J]. Transportation Research Record, 1981(795): 40-46.**

在 Little 1966 的整数规划框架上实现双向带宽最大化，引入周期、速度和相序变量。

解决的问题：把“绿波带宽”变成可计算的优化目标。

假设与失效：带宽是几何量，不等于延误或停车改善；清空时间、排队溢出和非协调方向牺牲必须另行约束。

**[7] GARTNER N H, ASSMAN S F, LASAGA F, et al. A multi-band approach to arterial traffic signal optimization[J]. Transportation Research Part B, 1991, 25(1): 55-74.**

把单一带宽推广为分段多带宽，允许不同路段使用不同带宽。

解决的问题：长干线上各路段需求不均时，单带宽模型会牺牲局部。

假设与失效：变量和约束显著增加，需要可靠的分段需求和权重；参数标定不好时，结果对输入极敏感。

## H.3 自适应控制

**[8] SIMS A G, DOBINSON K W. The Sydney coordinated adaptive traffic system[C]//Proceedings of the International Conference on Road Traffic Signalling. London: IEE, 1980.**

提出分层自适应：战略层选周期和绿信比，战术层做相位差和局部调整。

解决的问题：让区域协调随需求变化，而不是每天执行固定方案。

假设与失效：依赖稳定的检测器覆盖和通信；检测缺失时，自适应会放大噪声。

**[9] HUNT P B, ROBERTSON D I, BRETHERTON R D, et al. The SCOOT on-line traffic signal optimisation technique[J]. Traffic Engineering & Control, 1982, 23(4): 190-192.**

用实时流量剖面在线微调周期、绿信比和相位差，而不是周期性地重算整套方案。

解决的问题：把“在线优化”做成可运行的闭环，并给出与定时方案的对比结果。

假设与失效：需要连续、可信的检测数据；模型对饱和与溢出的处理有限，过饱和时仍要依赖人工策略。

**[10] PAPAGEORGIOU M, DIAKAKI C, DINOPOULOU V, et al. Review of road traffic control strategies[J]. Proceedings of the IEEE, 2003, 91(12): 2043-2067.**

系统梳理定时、感应、自适应、模型预测和分层控制的谱系。

解决的问题：给出“什么场景该用什么控制”的分类框架。

假设与失效：综述不提供具体参数；把某一类方法直接搬到另一类场景，仍会失效。

## H.4 组件语义

**[16] Apache Software Foundation. Apache Kafka documentation[EB/OL]. [2026-11-15]. https://kafka.apache.org/documentation/.**

事件顺序、消费者组、幂等与事务语义。

**[17] Apache Software Foundation. Apache Flink documentation[EB/OL]. [2026-11-15]. https://nightlies.apache.org/flink/flink-docs-stable/.**

事件时间、水位线、窗口、状态与广播状态。

## H.5 规范与手册

**[11] TRANSPORTATION RESEARCH BOARD. Highway capacity manual[M]. 7th ed. Washington, DC: National Academies Press, 2022.**

通行能力、饱和流率、延误和服务水平的权威口径。

解决的问题：给“容量”和“服务水平”提供统一语言。

假设与失效：参数按地区和研究条件给出，现场必须标定；版本更新会改变部分取值。

**[12] FEDERAL HIGHWAY ADMINISTRATION. Manual on uniform traffic control devices for streets and highways[M]. 11th ed. Washington, DC: FHWA, 2023.**

交通控制设施的设计、安装和运行规则。

解决的问题：信号灯、标志、标线的法定语义。

假设与失效：美国规范，不能直接替代中国规范；引用的条款必须按现行版本核对。

**[13] 中华人民共和国住房和城乡建设部. 城市道路交叉口设计规程: CJJ 152—2010[S]. 北京: 中国建筑工业出版社, 2010.**

城市道路交叉口设计的行业规程，涉及交叉口几何、交通组织、行人过街和信号控制相关条款。

解决的问题：给国内交叉口设计提供可审查的底线。

假设与失效：它是交叉口设计规程，不是专门的信号配时规范；书中引用它时必须给出具体条款，不能把“代码注释提到它”当成规范依据。出版前还要确认现行有效版本、地方规定和项目审批要求。

**[14] FEDERAL HIGHWAY ADMINISTRATION. Traffic signal timing manual: FHWA-HOP-08-024[R]. Washington, DC: FHWA, 2008.**

从数据采集到配时、协调、运行维护的完整工程流程。

解决的问题：把“配时”放回运营流程，而不是只看公式。

假设与失效：流程可借鉴，参数和法规环境需本地化。

**[15] AASHTO, ITE, NEMA. NTCIP 1202: object definitions for actuated signal controllers[S]. Washington, DC: AASHTO, 2019.**

信号机对象字典和通信接口的标准定义。

解决的问题：不同厂商设备可以有共同的字段语义。

假设与失效：标准定义的是对象和编码，不保证厂商实现完全一致；版本差异需要现场核对。

**[18] 国家市场监督管理总局, 国家标准化管理委员会. 道路交通信号控制系统术语: GB/T 31418—2025[S]. 北京: 中国标准出版社, 2025.**

道路交通信号控制系统的基础术语，覆盖控制方式、系统结构、设备与接口。

解决的问题：统一“方案、阶段、相位、协调、自适应”等词的口径。

假设与失效：2025-12-31 发布、2026-07-01 实施；引用时以现行版本为准，旧版术语可能仍出现在地方文件和设备手册里。

**[19] 国家市场监督管理总局, 国家标准化管理委员会. 道路交通信号控制系统通用技术要求: GB/T 39900—2021[S]. 北京: 中国标准出版社, 2021.**

信号控制系统的总体技术要求，覆盖系统功能、性能与接口边界。

解决的问题：把“系统应该具备什么”与“某个厂商怎么实现”分开。

假设与失效：通用要求不等于项目验收条款，具体工程仍需引用设计文件和设备协议。

**[20] 国家质量监督检验检疫总局, 中国国家标准化管理委员会. 道路交通信号控制机: GB 25280—2016[S]. 北京: 中国标准出版社, 2016.**

信号机的产品标准，涉及控制方式、灯组驱动、故障降级和通信接口。

解决的问题：给“设备能做什么、不能做什么”提供产品级边界。

假设与失效：产品标准不规定配时算法；不同厂商对同一功能的实现仍有差异。

**[21] 国家质量监督检验检疫总局, 中国国家标准化管理委员会. 交通信号控制机与上位机间的数据通信协议: GB/T 20999—2017[S]. 北京: 中国标准出版社, 2017.**

信号机与中心系统之间的数据通信协议。

解决的问题：统一命令、状态、方案和时钟字段的语义。

假设与失效：协议规定字段，不保证厂商扩展字段一致；版本和私有位需要现场核对。

**[22] 国家市场监督管理总局, 国家标准化管理委员会. 交通信号控制机与车辆检测器间通信协议: GB/T 43229—2023[S]. 北京: 中国标准出版社, 2023.**

信号机与检测器之间的通信协议。

解决的问题：把检测数据的时间、计数和状态语义落到接口层。

假设与失效：协议不解决检测器安装、遮挡和标定问题；数据质量仍要单独评价。

**[23] 国家质量监督检验检疫总局, 中国国家标准化管理委员会. 道路交通信号灯设置与安装规范: GB 14886—2016[S]. 北京: 中国标准出版社, 2016.**

信号灯设置、安装与视认性要求。

解决的问题：给“灯该不该设、装在哪、怎么被看见”提供规范依据。

假设与失效：它管设置与安装，不直接规定配时；与信号配时的关系要在设计和验收文件里写清。

## H.6 技术脉络

如表 H-1 所示。
表 H-1 技术脉络
| 年代 | 方法 | 解决的问题 | 主要假设与失效 |
|---|---|---|---|
| 1958 | Webster 周期与延误 | 孤立路口配时 | 欠饱和、稳定需求 |
| 1966 | 混合整数协调 | 干线偏移优化 | 行程时间已知、速度固定 |
| 1969 | TRANSYT | 路网固定配时 | 需求视为常量 |
| 1980 | SCATS | 区域自适应 | 检测与通信可靠 |
| 1981 | MAXBAND | 双向带宽 | 带宽≠效益 |
| 1982 | SCOOT | 在线微调 | 连续可信流量 |
| 1991 | MULTIBAND | 分段带宽 | 需求权重可靠 |
| 2003 | 控制策略综述 | 方法分类 | 不提供参数 |

这张表的用法不是背年代，而是回答：**当前系统采用的机制，继承了什么假设，又在哪一步绕过了它。** 例如本书的 MaxBand 实现把清空时间置零（17.10），就等价于默认“排队瞬时消散”，这正是原始模型假设最容易被现场推翻的地方。

## 引用规则

1. 公式用于解释时，优先引用原始理论或现行规范。
2. 生产行为以当前源码和接口为准。
3. 代码注释中的文献链接不能直接视为已经核验。
4. 现场效果必须有可追溯数据，不能只引用算法输出。
5. 规范版本、地方规定和设备手册在出版前再次核对。
