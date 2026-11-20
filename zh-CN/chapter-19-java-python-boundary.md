---
layout: default
title: "第 19 章 Java 控制服务与 Python 算法服务"
nav_order: 191
parent: "第五部分 平台工程"
---

# 第 19 章 Java 控制服务与 Python 算法服务

第 18 章的验收单为 S2 的协调方案签下 40 秒带宽之后，这份方案在现场系统里停在“可下发候选”状态——从候选到真正进入路口，中间还隔着平台的整条执行链。大型信控平台经常同时使用 Java 和 Python：Java 擅长业务组织、权限、持久化和设备服务集成；Python 擅长数据处理、优化和科研算法。语言边界本身不是架构，架构是职责边界。

本章以 WaySense 的 AI 辅助控制链路为例，说明一个算法请求如何从业务服务到达算法服务，再变成可审核的控制方案。这正是第五部分阅读路径的第一站：第 19 章说明 Java 服务组织与 Python 算法边界。

考虑 S2 的单点推荐请求。Java 拿到某一天的流量、当前方案和候选池后调用 Python；Python 用当前代码的流量比和周期模型算出阶段绿时；Java 再把结果包装成页面 DTO。若页面显示的阶段时间与 Python 结果少了一个清空字段，算法可能没错，业务对象转换却已经改变了交通含义。

跨语言边界的质量取决于三件事：双方对对象语义的理解是否一致，异常和超时是否可区分，结果是否绑定可追溯的输入版本。语言只是传输介质。

## 19.1 Java 侧职责

Java 侧负责：

- 校验日期、路口、子区和时段
- 检查方案和调度是否存在
- 组织拓扑、流量和候选方案输入
- 调用 Python 算法
- 转换输出对象
- 缓存推荐结果
- 生成报表和导出文件

这些职责不是算法的附属代码。没有它们，Python 服务无法获得完整业务上下文，也无法把结果放回方案库。

### 19.1.1 状态所有权

平台中的权威状态需要有明确归属：

状态归属如表 19-1 所示。

<!-- pagebreak -->
表 19-1 状态所有权
| 状态 | 建议权威来源 | Java 侧可否修改 |
|---|---|---:|
| 已发布方案库 | 业务数据库与发布流程 | 是，但需要走版本和审核 |
| 候选算法结果 | 推荐记录 | 可以保存，不应覆盖已发布方案 |
| 设备运行状态 | 设备适配器与实时链路 | 不能由 Java 业务服务伪造 |
| 命令执行状态 | 命令服务 | 可以由 Java 组织，但需幂等 |
| 控制评价结果 | 评价服务或只读数据平台 | 可以展示，不应反写实时状态 |

算法服务不应直接修改“当前运行方案”。它可以生成候选，Java 校验并保存审核状态，设备命令服务负责执行。这样即使 Python 超时、重试或返回重复结果，也不会直接改变现场。

### 19.1.2 转换层需要保留语义

一个常见的 DTO 转换问题，是把算法返回的“阶段总时长”写入业务字段 `greenTime`，页面随后又把它和纯绿相加。转换层应显式映射：

```text
algorithm.stage_green_s
  -> business.stage.green_s

algorithm.stage_clearance_s
  -> business.stage.green_flash_s + yellow_s + all_red_s

algorithm.cycle_s
  -> business.plan.cycle_s
```

如果算法只返回比例，Java 不能凭空生成秒数；如果算法返回完整方案，Java 仍应重新执行周期闭合和最小绿校验。转换不是复制字段，而应当是经过单元测试的语义适配。

## 19.2 Python 侧职责

Python 侧负责：

- 流量比和时段划分
- 候选相序筛选
- 周期与绿信比优化
- 自适应调整
- 子区协调
- MaxBand 和相位差
- 带宽计算

Python 返回的是算法结果，不是已生效控制。Java 仍需要转换、校验和保存。

### 19.2.1 算法服务不应该知道页面

Python 可以返回阶段、关键流量比、警告和输入版本，但不应返回“推荐按钮颜色”或“当前用户是否能下发”。权限属于 Java 业务层，命令状态属于设备命令服务。

同样，Python 不应为了省字段而查询任意业务表。它依赖的输入应该由 Java 在请求中组织，或通过明确声明的算法数据接口获取。否则同一个请求在不同时间可能读到不同数据库快照，无法复现。

算法内部可以有 DataFrame、字典和第三方模型，但跨边界的对象应稳定、可序列化、有单位。内部库升级不应改变 `stageFlowRatios` 的结构含义。

## 19.3 接口链路

现有链路可以概括为：

```text
AiComputeController
  -> IAiComputeService
  -> AiComputeServiceImpl
  -> IAiCommputeClient
  -> /get_site_pattern_lib
     /get_region_pattern_lib
     /gettimespace
```

阅读源码时以接口定义中的实际名称为准；本书正文统一使用正确英文。

### 19.3.1 四条实际调用路径

当前 Java 接口可以对应到以下算法用途：

具体见表 19-2。
表 19-2 四条实际调用路径
| Java Feign 方法 | Python 路由 | 用途 | 主要风险 |
|---|---|---|---|
| `aiComputeSitePlans` | `GET /get_site_pattern_lib` | 单点方案库推荐 | 查询参数中的时间和一天范围 |
| `aiComputeSubRegionPlans` | `POST /get_region_pattern_lib` | 子区方案推荐 | 分组参数、协调方向与关键路口 |
| `searchSubRegionTimeSpace` | `POST /gettimespace` | 时空图 | `Plan` 内阶段和路段映射 |
| `siteAdaptive` / `siteCycleAdaptive` | `/singleadaptive` / `/cycleadaptive` | 单点与周期自适应 | 时间尺度、置信度和下发门控 |

控制器 `AiComputeController` 负责日期、参数和权限入口。`AiComputeServiceImpl` 负责获取业务数据、调用 Feign、转换结果和保存推荐。`IAiCommputeClient` 只声明 HTTP 契约；`apiserver.py` 读取参数并进入 Python 算法。遇到“页面没有结果”时，按这条链逐层确认，而不是只在算法函数里猜测。

当前完整源码还显示两个边界。第一，`fetchAiComputeSiteResult` 在 Feign 返回 `null` 时仍进入错误分支并调用 `planContentListData.getStatus()`，会产生空指针。第二，子区重算用 Java 的 `!=` 比较 `startTime` 和 `endTime` 字符串，比较的是引用而不是内容，可能重复加入不应重算的时段组。第 28 章保留完整方法并给出修复不变量。

单点接口当前是 GET，请求参数包括站点和时间戳；子区和时空图是 POST，携带结构化请求体。数据结构差异本身不是问题，关键是时间单位、时区和版本字段需要明确。生产代码中的 URL 由部署配置提供，书中不复制内部地址。

### 19.3.2 三种调用组织

同一条 Java→Python 边界，可以组织成三种方式：

具体见表 19-3。
表 19-3 三种调用组织
| 方式 | 调用形态 | 优点 | 失效条件 |
|---|---|---|---|
| 同步 HTTP | Feign 直接调用，等结果 | 简单、链路短、结果立即返回 | 算法耗时超过超时；超时后不知道对方是否算完 |
| 异步任务 | 提交任务 + 轮询/回调 | 适合长计算，可重试、可排队 | 要额外维护任务状态和结果表 |
| 消息队列 | 发请求消息，等响应消息 | 解耦、削峰、可回放 | 延迟不确定，需要 correlation id 和超时处理 |

本系统三种都用：单点和子区查询走 Feign 同步 HTTP；定时优化走 Celery 任务；实时事件走 Kafka。同一个算法函数甚至同时被装饰成任务和暴露成路由，所以“它是同步还是异步”取决于调用方，而不是函数本身。

选择标准是**这次计算要等多久、失败了谁负责**。秒级返回的查询用同步最简单；几分钟的批量优化用异步；跨系统的事件流用消息。用同步 HTTP 包一个十分钟的任务，超时和重试会立刻变成一致性问题。

## 19.4 请求契约

一个可靠请求至少需要包含：

- 任务类型和请求 ID
- 路口或子区标识
- 时间窗口与时区
- 当前方案和候选方案
- 流量、饱和流率和拓扑
- 周期模型与上下限
- 最小绿与清空配置
- 协调方向和关键路口
- 数据版本与算法版本

缺少版本字段会让结果无法复算。例如同一路口方案在请求后被人编辑，算法返回的结果可能对应旧候选池。

以下是一个概念请求，不是生产接口的完整 DTO：

```json
{
  "requestId": "req-001",
  "taskType": "site_optimization",
  "siteId": "site-001",
  "timeRange": {
    "start": "2026-11-10T07:00:00+08:00",
    "end": "2026-11-10T07:30:00+08:00"
  },
  "inputVersion": "offline-dw-20261110-0730",
  "algorithmVersion": "book-lab-1",
  "cycleModel": "linear",
  "cycleLimits": {"min": 45, "max": 180}
}
```

真实请求还需要拓扑、方案池、流量和饱和流率。示例用于强调两个字段：请求需要可识别，输入需要可追溯。

### 19.4.1 为 S2 构造一个可复核请求

下面的对象使用合成 ID 和相对时间，不包含生产凭据：

```json
{
  "requestId": "req-s2-20261110-1700",
  "taskType": "single_site_optimization",
  "siteId": "site-S2",
  "window": {
    "start": "2026-11-10T16:45:00+08:00",
    "end": "2026-11-10T17:00:00+08:00",
    "timezone": "Asia/Shanghai"
  },
  "inputVersions": {
    "traffic": "flow-S2-20261110T1700",
    "topology": "network-v12",
    "planPool": "site-S2-pool-v8"
  },
  "currentPlanVersion": "site-S2-plan-v41",
  "limits": {
    "minCycleSeconds": 60,
    "maxCycleSeconds": 180
  },
  "cycleModelVersion": "curve-2026a"
}
```

如果 `window.end` 是本地时间而 Python 内部使用 UTC 秒，Java 适配层需要完成转换并保留原始时区。若 `timestamp` 和 `endTimestamp` 来自不同时间定义，Python 可能读取到多一天或少一天的数据。

请求还可以包含 `requestedBy`、`correlationId` 和 `traceId`，但不能用访问令牌、内网地址或用户隐私字段填充这些标识。日志中的追踪信息应能关联请求，而不暴露凭据。

## 19.5 响应契约

响应不仅需要阶段秒数，还应包括：

- 对应请求 ID
- 输入版本
- 原方案标识
- 推荐方案标识
- 每个阶段的完整时间
- 关键阶段与关键流量比
- 可行性状态
- 警告和降级原因

错误需要分类：

```text
invalid_request
missing_business_data
algorithm_timeout
infeasible_constraints
internal_error
```

把错误统一返回为空方案，会让调用方误以为算法正常完成。

响应应同时携带结果和失败语义：

```json
{
  "requestId": "req-001",
  "status": "infeasible",
  "warnings": ["critical flow ratio exceeds capacity"],
  "sourcePlanId": "plan-v3",
  "recommendedPlan": null,
  "algorithmVersion": "book-lab-1"
}
```

这里返回 `null` 比返回全零阶段更安全。调用方需要能够区分“算法没有结果”和“算法输出了零周期”。

### 19.5.1 结果验证的前置条件

Java 收到推荐结果后，至少执行：

```text
response.request_id == request.request_id
response.input_versions == request.input_versions
response.source_plan_version == request.current_plan_version
response.status in allow_set
validate_plan(response.plan)
```

如果请求期间人工编辑了当前方案，响应中的 `source_plan_version` 会与最新版本不一致。Java 应把结果标记为过期候选，而不是直接覆盖。这个检查不能只依赖 HTTP 成功。

对于每个阶段，还要对比原方案和推荐的阶段 ID。新增、删除或重排阶段属于结构变化，不能被当作普通秒数修改自动提交。

### 19.5.2 接口结果要能区分成功、拒绝和未知

跨语言接口最容易犯错的设计，是用一个“成功响应结构”表达所有结果。算法不可行、输入缺失、超时、参数错误和系统异常都返回空方案，调用者只能猜测空值意味着什么。

概念上，响应应属于可区分的结果类型：

\[
\begin{aligned}
\mathrm{Response}
= \mathrm{Success}(\mathrm{plan},\mathrm{evidence})
\mid\mathrm{Rejected}(\mathrm{code},\mathrm{details})\\
\quad \mid\mathrm{Unknown}(\mathrm{request\ id},\mathrm{retry\ after})
\end{aligned}
\]

`Success` 携带完整方案和证据，`Rejected` 表示请求被明确判定为不可执行，`Unknown` 表示调用方暂时无法知道服务端是否完成。HTTP 状态码只是传输层分类，不能单独承载这三种业务语义。例如超时可能得到客户端 `504`，但服务端任务仍会完成；空数组 `200` 也可能隐藏一个不可行模型。

请求身份也可以形式化。一个推荐结果只对特定输入快照有效：

\[
\mathrm{request\ identity}=
(\mathrm{request\ id},\mathrm{input\ version},\mathrm{algorithm\ version})
\]

缓存命中需要同时比较输入版本和算法版本。仅用 `site_id + date` 作为缓存键，会在流量修订、拓扑变更或算法升级后返回旧结果。人工编辑当前方案后，旧缓存仍可能看似合法，但已经失去父版本。

Java 收到成功结果后还要验证：

\[
\begin{aligned}
\mathrm{accept}
= (\mathrm{request\ id\ matches})
\land(\mathrm{input\ versions\ match})\\
\quad \land(\mathrm{plan\ valid})
\land(\mathrm{source\ plan\ still\ current})
\end{aligned}
\]

四个谓词分别防止串请求、混合输入、非法方案和版本竞争。有一项失败，就应保存为过期或拒绝的推荐记录，不能直接把方案写入可调度状态。

## 19.6 超时与重试

Python 优化可能包含线性规划、聚类和多场景计算。Java 调用需要设置合理超时，并区分：

- 请求未到达
- 算法已执行但传输失败
- 算法超时但可能仍在后台运行
- 结果成功但保存失败

重试需要使用同一请求 ID 或幂等键，避免重复生成多个推荐结果。

### 19.6.1 超时、取消和残留任务

设 Java 客户端超时为 15 秒，Python 求解器最长运行 30 秒。Java 在 15 秒收到超时，Python 仍可能在后台完成并保存结果。系统需要定义：

```text
client_timeout
solver_deadline
request_status = expired | running | completed | abandoned
result_visible_after_client_timeout
```

如果客户端超时后立即重试，而旧请求仍在运行，两个任务可能使用同一输入但写入两个推荐记录。推荐服务应使用请求 ID 幂等保存；若输入版本相同，返回同一个结果或取代关系。

取消也要区分“客户端停止等待”和“服务端停止计算”。客户端超时不会自动终止 Python 进程。若算法占用大量资源，需要服务端截止时间和取消机制，并把取消原因写入任务状态。

保存失败是第三种失败。算法可能成功，传输也成功，业务数据库写入却失败。Java 不应向页面报告“推荐成功”而没有可查询的推荐 ID；重试保存也应使用相同结果版本，避免生成重复推荐。

### 19.6.2 错误分类与处理责任

如表 19-4 所示。
表 19-4 错误分类与处理责任
| 错误码 | 责任层 | 典型处理 |
|---|---|---|
| `INVALID_REQUEST` | Java 入口/Python 参数校验 | 修正字段，不重试同一请求 |
| `MISSING_BUSINESS_DATA` | Java 数据组织 | 补数据或保持原方案 |
| `INFEASIBLE_CONSTRAINTS` | 算法/业务约束 | 修改约束或人工审核，不盲目重试 |
| `ALGORITHM_TIMEOUT` | Python/资源 | 记录输入，允许有限重试或降级 |
| `DOWNSTREAM_UNAVAILABLE` | 网络/部署 | 退避重试，保持原方案 |
| `RESULT_PERSIST_FAILED` | Java 持久化 | 保存结果到临时区，重试持久化 |
| `STALE_INPUT_VERSION` | Java 版本检查 | 拒绝覆盖，重新获取当前状态 |

错误码需要稳定，页面可以根据它显示不同操作。把异常统一映射为 `500` 会让运营人员无法判断是改参数、等待还是保持原方案。

## 19.7 数据定义

跨语言 JSON 不会自动解决单位问题。接口需要明确：

- 流量单位是 veh/h 还是窗口车辆数
- 时间单位是秒还是毫秒
- 速度单位是 km/h 还是 m/s
- 周期和有效绿的定义
- 方向编码和转向编码

SignalLab 要求速度单位写入字段名，例如 `speed_kmh`，避免只写 `speed`。

### 19.7.1 JSON 兼容性

跨语言接口的兼容性不仅是字段名不变。应明确：

- 可选字段缺失与 `null` 是否等价；
- 浮点数精度和整数取整规则；
- 日期时间是否带偏移；
- 比率使用 0 至 1 还是百分数；
- 流向和阶段编码是否在不同版本中稳定；
- 新增枚举值能否被旧消费者安全忽略。

一个 Python 返回 `flow_ratio: 0.5`，Java 页面若乘以 100 显示 `50%`，这是同一语义。若 Java 又保存为 `0.5%`，下一次读取就会缩小 100 倍。接口文档应提供最小合法样例和单位测试。

### 19.7.2 可观测性字段

每个请求和响应都应有：

```text
request_id
trace_id
algorithm_version
config_version
input_versions
started_at
finished_at
solver_status
warnings
```

这些字段用于复算和排障。只记录 Java 日志中的耗时，无法知道 Python 使用了哪个模型、哪一版拓扑或哪一批流量。只记录响应但不在日志中关联请求，无法在用户报告错误时定位是哪一次计算。

## 19.8 本章实验

1. 为一个单点优化请求设计完整 JSON Schema。
2. 增加 `inputVersion` 和 `algorithmVersion`，说明如何检测过期结果。
3. 模拟算法超时，定义 Java 返回状态。
4. 将响应中的阶段时间重新转换回完整方案并执行校验。
5. 模拟 Python 已完成但 Java 接收超时，设计结果查询和重复请求处理。
6. 让请求期间人工修改当前方案，验证 Java 拒绝旧输入版本的结果。
7. 把阶段纯绿和阶段总时长制成两个 DTO 字段，设计往返转换测试。
8. 为 `INFEASIBLE_CONSTRAINTS` 设计页面提示和允许的下一步操作。

## 19.9 小结

Java 与 Python 的边界是业务组织与算法计算的边界，不是“谁负责页面、谁负责数学”的简单分界。双方通过完整请求、响应、版本和错误语义共同保证结果可追踪。第 18 章验收通过的方案在本章走完了第一条完整链路：请求绑定输入版本进入 Python，结果带四项谓词校验回到 Java，幂等键挡住重试产生的重复推荐，错误码把失败原因交还给页面。

服务边界就此立起：第 21 章的下发状态机、第 22 章的前端操作都架在这条边界之上。19.3.2 还留下一个衔接点——实时事件走 Kafka 之后，事件的时间顺序如何解释、迟到数据如何处理，是第 20 章 Kafka、Flink 与实时数据链路的话题。

## 练习

1. 为什么算法服务不应直接修改业务数据库中的当前方案？
2. 请求 ID 和幂等键如何避免重复推荐？
3. 设计一个错误码表，区分输入错误和算法不可行。
4. 说明数据版本缺失如何导致无法复算。
5. 为什么算法服务不能直接修改设备当前方案？
6. 请求 ID、幂等键和推荐 ID 分别解决什么问题？
7. 设计一个跨语言单位测试，覆盖流量、速度、时间和比例。
8. 说明超时后为什么要区分“客户端停止等待”和“服务端取消”。

