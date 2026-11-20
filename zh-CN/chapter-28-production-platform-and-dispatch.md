---
layout: default
title: "第 28 章 生产平台链路：Java 服务组织、实时作业、下发与前端"
nav_order: 281
parent: "第七部分 生产源码精读"
---

# 第 28 章 生产平台链路：Java 服务组织、实时作业、下发与前端

> 本章代码为生产源码摘录，省略 import、依赖注入、日志和其他方法；不能单独运行。

第 27 章把区域协调的生产链路走完；这一章看平台如何把算法结果送进真实系统。算法正确不等于系统可执行。Java 控制服务决定输入从哪里来、结果如何转换；Flink 决定实时指标何时产生；下发服务决定方案如何进入设备；前端决定用户看到的是目标、命令还是运行事实。

本章沿一条真实请求和一条真实下发读取完整代码。

## 28.1 Java 单点请求的完整实现

`AiComputeServiceImpl.fetchAiComputeSiteResult` 完整方法如下：

```java
@Override
public InterResult<List<AiRecomandSitePlanDto>>
fetchAiComputeSiteResult(
    String siteId,
    String date,
    String endDate
) {
    if (
        !DateUtil.isValid(date, DateUtil.DATE_FORMAT)
        || !DateUtil.isValid(endDate, DateUtil.DATE_FORMAT)
    ) {
        return InterResult.errorResult(
            ResultEnum.PARAMS_ERROR.getValue(),
            "时间格式不正确"
        );
    }
    if (StringUtils.isBlank(siteId)) {
        return InterResult.errorResult(
            ResultEnum.PARAMS_ERROR.getValue(),
            "路口ID不得为空"
        );
    }
    List<SiteControlPlan> siteControlPlans =
        siteControlPlanServiceHelper.siteControlPlansQuery(
            InnerSiteControlPlansQueryDto.builder()
                .siteId(siteId)
                .controlLevel(ControlLevelEnum.SITE.getValue())
                .build()
        );
    if (CollectionUtils.isEmpty(siteControlPlans)) {
        return InterResult.errorResult(
            ResultEnum.PARAMS_ERROR.getValue(),
            "路口方案不存在"
        );
    }
    List<SchedulePlanInfo> schedulePlanInfoList =
        scheduledPlanServiceHelper.getSchedulePlans(
            InnerSchedulePlanQueryDto.builder()
                .entityId(siteId)
                .type(ControlLevelEnum.SITE.getValue())
                .build()
        );
    if (CollectionUtils.isEmpty(schedulePlanInfoList)) {
        return InterResult.errorResult(
            ResultEnum.PARAMS_ERROR.getValue(),
            "路口关联的调度方案不存在"
        );
    }

    Date dateObj = DateUtil.parse(
        date + " 00:00:00",
        DateUtil.DATETIME_FORMAT
    );
    Date endDateObj = DateUtil.parse(
        endDate + " 23:59:59",
        DateUtil.DATETIME_FORMAT
    );
    Long timestamp = dateObj.getTime() / 1000;
    Long endTimestamp = endDateObj.getTime() / 1000;
    log.info(
        "查询参数site_id={}&timstamp={}&endTimestamp={}",
        siteId,
        timestamp,
        endTimestamp
    );
    FeignAiCompBaseDto<List<FeignAiCompSitePlanContentDto>>
        planContentListData =
            iAiCommputeClient.aiComputeSitePlans(
                siteId,
                timestamp,
                endTimestamp
            );
    if (
        null == planContentListData
        || !Objects.equals(
            planContentListData.getStatus(),
            FeignAiCompBaseDto.STATUS_SUC
        )
    ) {
        log.info(
            "计算异常：{}",
            JsonUtil.toJson(planContentListData)
        );
        if (
            Objects.equals(
                planContentListData.getStatus(),
                "BadRequest"
            )
        ) {
            return InterResult.errorResult(
                ResultEnum.PARAMS_ERROR.getValue(),
                "计算错误:"
                + (
                    null == planContentListData
                        ? ""
                        : planContentListData.getMessage()
                )
            );
        } else {
            return InterResult.errorResult(
                ResultEnum.PARAMS_ERROR.getValue(),
                "计算错误"
            );
        }
    }
    planContentListData.getData().forEach(item -> {
        String id = item.getSiteId();
        if (null == id || StringUtils.isEmpty(id)) {
            item.setSiteId(siteId);
        }
    });
    List<AiRecomandSitePlanDto> res =
        aiComputeHelper.convertAiComputeSiteControlPlanDtos(
            planContentListData.getData(),
            null,
            null
        );
    return new InterResult().defaultSuccess(res);
}
```

这里有一个可以直接指出的空指针边界。条件允许 `planContentListData == null` 进入错误分支，随后却调用：

```java
planContentListData.getStatus()
```

若 Feign 返回 `null`，错误处理本身会抛出 `NullPointerException`。正确的逻辑应在判断 `BadRequest` 前再次判断非空，或者先规范化成明确的传输错误对象。

还有一个需要注意的事实：入口要求“已存在路口方案”和“已存在调度方案”。这不是算法前置条件，而是业务运营条件。一个拓扑和流量都完整、但尚未建立方案库或调度计划的路口，不能通过此入口生成推荐。

## 28.2 子区请求验证的完整实现

`AiComputeServiceImpl.checkAiRequest` 完整方法如下：

```java
private FeignComputerSubRegionDTO checkAiRequest(
    String subRegionId,
    String startDate,
    String endDate,
    Integer segmentLevel,
    Integer nonCoordinationSacrifice,
    List<GroupParams> paramsList
) throws AIAuxiliaryException {
    if (
        !DateUtil.isValid(startDate, DateUtil.DATE_FORMAT)
        || !DateUtil.isValid(endDate, DateUtil.DATE_FORMAT)
    ) {
        throw new AIAuxiliaryException(
            ResultEnum.TIME_fORMAT_IS_INVALID
        );
    }
    if (StringUtils.isBlank(subRegionId)) {
        throw new AIAuxiliaryException(
            ResultEnum.SUB_REGION_IS_EMPTY
        );
    }

    Long startDateObj = DateUtil.parse(
        startDate,
        DateUtil.DATE_FORMAT
    ).getTime() / 1000;
    Long endDateObj = DateUtil.parse(
        endDate,
        DateUtil.DATE_FORMAT
    ).getTime() / 1000;

    AiComputerRequest aiComputerRequest =
        new AiComputerRequest();
    aiComputerRequest.setRegionId(subRegionId);
    aiComputerRequest.setTimestamp(startDateObj);
    aiComputerRequest.setEndTimestamp(endDateObj);
    aiComputerRequest.setSegmentLevel(segmentLevel);
    aiComputerRequest.setGroupParams(paramsList);
    aiComputerRequest.setNonCoordinationSacrifice(
        nonCoordinationSacrifice
    );
    FeignAiCompBaseDto<FeignComputerSubRegionDTO>
        compSubRegionDTO =
            iAiCommputeClient.aiComputeSubRegionPlans(
                aiComputerRequest
            );

    log.info(
        "子区AI智能计算结果：{}",
        JSON.toJSONString(compSubRegionDTO)
    );

    if (null == compSubRegionDTO) {
        throw new AIAuxiliaryException(
            ResultEnum.PARAMS_ERROR.getValue(),
            "数据异常，数据为空"
        );
    }
    if (
        !Objects.equals(
            compSubRegionDTO.getStatus(),
            FeignAiCompBaseDto.STATUS_SUC
        )
    ) {
        log.error(
            "计算异常：{}",
            JsonUtil.toJson(compSubRegionDTO)
        );
        if (
            Objects.equals(
                compSubRegionDTO.getStatus(),
                "BadRequest"
            )
        ) {
            throw new AIAuxiliaryException(
                ResultEnum.PARAMS_ERROR.getValue(),
                "数据异常，计算失败:"
                + compSubRegionDTO.getMessage()
            );
        } else {
            throw new AIAuxiliaryException(
                ResultEnum.PARAMS_ERROR.getValue(),
                "数据异常，计算失败"
            );
        }
    }
    FeignComputerSubRegionDTO computeRes =
        compSubRegionDTO.getData();
    if (
        null == computeRes
        || CollectionUtils.isEmpty(
            computeRes.getGroupList()
        )
    ) {
        throw new AIAuxiliaryException(
            ResultEnum.PARAMS_ERROR.getValue(),
            "算法不推荐子区协调控制"
        );
    }
    return computeRes;
}
```

把“空结果”解释成“算法不推荐子区协调控制”是一个业务判断。它可能来自模型确实没有可行分组，也可能来自 Python 转换错误、数据为空或响应结构变化。代码没有携带可区分的 `status` 和 `reason`，调用者只能看到同一句业务错误。

这里和 28.1 的日期转换不一致：28.1 的接口把 `endDate` 拼成 `" 23:59:59"`，28.2 的接口用 `DateUtil.DATE_FORMAT` 只解析到当天 `00:00:00`。同样叫 `endDate`，一个包含当天，一个不包含当天最后一秒。跨接口传参时，如果调用方按 28.1 的语义传 `endDate`，28.2 会少算最后一天；反过来会多算一天。需要在接口契约里明确“结束日期是闭区间还是开区间”，并在转换层统一，而不是让每个接口各自解释。

## 28.3 重算时的分组筛选

`fetchAiComputeSubRegionPlanWithGroup` 有一段重要但容易遗漏的实现：

```java
for (SubRegionGroup subRegionGroup :
        aiComputeSubRegionPlanResponse.getGroupList()) {
    for (
        SubRegionGroupDetail detail :
        subRegionGroup.getSubRegionGroupDetailList()
    ) {
        if (detail.getSitePlanList().size() < 2) {
            continue;
        }
        if (
            detail.getStartTime() != startTime
            && detail.getEndTime() != endTime
        ) {
            GroupParams groupParams =
                GroupParams.builder()
                    .groupId(subRegionGroup.getGroupId())
                    .startTime(detail.getStartTime() + ":00")
                    .coordinationDirection(
                        detail.getCoordinationDirection()
                    )
                    .coordinationType(
                        detail.getCoordinationType()
                    )
                    .keyCrossId(detail.getKeySiteId())
                    .build();
            groupParams.setEndTime(
                detail.getEndTime().endsWith("59")
                    ? detail.getEndTime() + ":59"
                    : detail.getEndTime() + ":00"
            );
            paramsList.add(groupParams);
        }
    }
}
```

`!=` 对 Java 字符串比较的是引用，不是内容。来自缓存的 `detail.getStartTime()` 与请求参数 `startTime` 通常是不同对象，即使字符串内容相同，条件也经常为真。实际效果是原缓存中的很多时段组会再次加入重算参数，而不只是排除请求组。

应改为 `!Objects.equals(...)`。修正后还要定义业务规则：只重算目标组，还是保留其他组的原始人工配置。仅修 Java 运算符不能自动回答这个问题。

还有一个布尔逻辑问题。原条件是：

```java
if (detail.getStartTime() != startTime
    && detail.getEndTime() != endTime) {
```

即使把 `!=` 换成 `!Objects.equals(...)`，`&&` 仍然不是“排除起止都相同的组”。它表达的是“起点不同**并且**终点不同”，因此起点相同、终点不同的组也会被排除；而真正要排除的是“起止都相同”，应写成：

```java
if (!(Objects.equals(detail.getStartTime(), startTime)
      && Objects.equals(detail.getEndTime(), endTime))) {
```

等价于两个 `!equals` 之间用 `||`。只修字符串比较、不修布尔连接词，筛选结果仍然不对。

## 28.4 1 分钟车道 Flink 作业

`Automobile2Lane1MinJob.run` 的核心完整方法如下，省略的只有已注释掉的旧广播连接代码：

```java
@Override
public void run(
    StreamExecutionEnvironment env,
    Map<String, BroadcastStream> broadcastStreamMap
) {
    DataStream<Automobile> automobileDataStream =
        env.fromSource(
            createOfflineDwKafkaSource(
                getOfflineDwKC().getDwdParameterAutomobileRtTopic(),
                Automobile.class
            ),
            WatermarkStrategy
                .<Automobile>forBoundedOutOfOrderness(
                    Duration.ofSeconds(
                        offlineDwJobConfig.getAutomobileWatermarkDelay()
                    )
                )
                .withTimestampAssigner(
                    (automobile, timestamp) ->
                        DateTimeUtils.getDateTimeMillSec(
                            automobile.getExit_time(),
                            DateTimeUtils.DATETIME_MILL_PATTERN
                        )
                )
                .withIdleness(
                    Duration.ofSeconds(
                        offlineDwJobConfig.getKafkaIdleTimeout()
                    )
                ),
            "automobile2lane1min"
        )
        .setParallelism(
            customOperatorParallelismConfig
                .getAutomobile2LaneConsumer()
        )
        .filter(automobileToLaneFilterFun)
        .map(new MapFunction<Automobile, Automobile>() {
            @Override
            public Automobile map(Automobile value)
                    throws Exception {
                value.setAutomobile_feature(null);
                return value;
            }
        })
        .setParallelism(
            customOperatorParallelismConfig
                .getAutomobile2LaneConsumer()
        );

    SingleOutputStreamOperator<Lane1MinParameter> laneMinDS =
        automobileDataStream
            .keyBy(
                new KeySelector<
                    Automobile,
                    Tuple3<String, String, String>
                >() {
                    @Override
                    public Tuple3<
                        String,
                        String,
                        String
                    > getKey(Automobile automobile)
                            throws Exception {
                        return new Tuple3<>(
                            automobile.getBind_id(),
                            automobile.getLane_id(),
                            automobile.getCamera_serial()
                        );
                    }
                }
            )
            .window(
                TumblingEventTimeWindows.of(
                    Time.seconds(
                        offlineDwJobConfig.getAutomobileWidowSize()
                    )
                )
            )
            .aggregate(
                automobileAggregationFunction,
                automobileLaneProcessWindowFunction
            )
            .setParallelism(
                customOperatorParallelismConfig
                    .getAutomobile2LaneConsumer()
            );

    DataStream<Lane1MinParameter> lane1MinWithDimDS =
        laneMinDS
            .map(lane1MinSupplyRoadDimMapFun)
            .setParallelism(
                customOperatorParallelismConfig
                    .getAutomobile2LaneConsumer()
            )
            .filter(
                new FilterFunction<Lane1MinParameter>() {
                    @Override
                    public boolean filter(
                        Lane1MinParameter value
                    ) throws Exception {
                        return value != null;
                    }
                }
            )
            .setParallelism(
                customOperatorParallelismConfig
                    .getAutomobile2LaneConsumer()
            );

    lane1MinWithDimDS.sinkTo(
        createOfflineDwKafkaSink(
            getOfflineDwKC().getDwsParameterLaneFlow1MinTopic(),
            LaneSecondsParameter.class
        )
    );
    lane1MinWithDimDS.sinkTo(
        DorisSinkUtils.createDorisSinkFromObj(
            "dws_mgr_tp_automobile_lane_1mi",
            "offline_dw",
            dorisConnectorConfig,
            CommonConstant.DORIS_INSERT
        ).build()
    );
}
```

`run` 没有设置 `allowedLateness`，1 分钟车道窗口在规定水位线关闭后即输出。下游 5 分钟路口作业设置了自己的 `allowedLateness`。两条作业的迟到边界不同，上游已经关闭的事件不会因为下游等待更久而重新进入 1 分钟表。

分区键是 `(bind_id, lane_id, camera_serial)`，目的是避免同一绑定和车道上的多个视频源被重复累计，也为后续按探头均值准备数据。分区键不是业务事件唯一键，窗口内是否重复计数仍由 `real_flag` 和上游去重决定。

## 28.5 批量方案下发的完整事务边界

`integration-data/ControlServiceImpl.downloadPlanTask` 完整方法如下：

```java
@Override
@Transactional
public IntegResult<Void> downloadPlanTask(
    List<DownloadPlanTaskVO> downloadPlanTaskVOList
) {
    IntegResult<Void> result = new IntegResult<>();
    if (null == downloadPlanTaskVOList) {
        return result.errorResult(
            IntegResultEnum.PARAMS_IS_NULL
        );
    }
    List<DownloadPlanVO> downloadPlanVOList =
        new ArrayList<>();
    List<DownloadOffsetPlanVO> downloadOffsetPlanVOList =
        new ArrayList<>();

    for (
        DownloadPlanTaskVO downloadPlanTaskVO :
        downloadPlanTaskVOList
    ) {
        DownloadPlanVO downloadPlanVO =
            downloadPlanTaskVO.getDownloadPlanVO();
        DownloadOffsetPlanVO downloadOffsetPlanVO =
            downloadPlanTaskVO.getDownloadOffsetPlanVO();
        if (
            null == downloadPlanVO
            || StringUtils.isEmpty(
                downloadPlanVO.getSiteId()
            )
        ) {
            return result.errorResult(
                IntegResultEnum.PARAMS_IS_NULL
            );
        }

        if (
            ControlPlanMode.AI.getValue()
            == downloadPlanVO.getMode()
        ) {
            Date tmpEndTime = DateUtil.getDateAfter(
                downloadPlanVO.getEndTime(),
                2,
                0
            );
            if (
                DateUtil.getStartOfDay(tmpEndTime).getTime()
                == DateUtil.getStartOfDay(
                    downloadPlanVO.getEndTime()
                ).getTime()
            ) {
                downloadPlanVO.setEndTime(tmpEndTime);
            }
            if (
                null != downloadOffsetPlanVO
                && null != downloadOffsetPlanVO.getSiteId()
            ) {
                Date tmpOffsetEndTime =
                    DateUtil.getDateAfter(
                        downloadPlanVO.getEndTime(),
                        2,
                        0
                    );
                if (
                    DateUtil.getStartOfDay(
                        tmpOffsetEndTime
                    ).getTime()
                    == DateUtil.getStartOfDay(
                        downloadPlanVO.getEndTime()
                    ).getTime()
                ) {
                    downloadOffsetPlanVO.setEndTime(
                        tmpOffsetEndTime
                    );
                }
            }
        }
        downloadPlanVOList.add(downloadPlanVO);
        if (
            downloadOffsetPlanVO != null
            && null != downloadOffsetPlanVO.getSiteId()
        ) {
            downloadOffsetPlanVOList.add(
                downloadOffsetPlanVO
            );
        }
    }

    if (
        downloadOffsetPlanVOList.size() > 0
        && (
            downloadOffsetPlanVOList.size()
            != downloadPlanVOList.size()
        )
    ) {
        return result.errorResult(
            IntegResultEnum.PARAMS_IS_NULL
        );
    }

    IntegResult<Void> splitResult =
        splitPlanTaskService.batchAddTask(
            downloadPlanVOList
        );
    if (!splitResult.isSuccess()) {
        return splitResult;
    }

    if (
        !CollectionUtils.isEmpty(
            downloadOffsetPlanVOList
        )
    ) {
        IntegResult<Void> offsetResult =
            offsetPlanTaskService.batchAddTask(
                downloadOffsetPlanVOList,
                downloadPlanVOList
            );
        if (!offsetResult.isSuccess()) {
            return offsetResult;
        }
    }
    return result.defaultSuccess();
}
```

`@Transactional` 包住两次本地任务插入，却没有包住设备执行。该方法只负责创建下发任务。设备发送由 `processDownloadTask()` 和 `processOffsetTask()` 后续轮询或调度。

AI 模式会把方案结束时间向后延 2 分钟，注释原因是避免 AI 算法尚未下发时推荐回滚。这个行为修改了用户请求的实际结束时间，API 响应却仍只是 `Void`。可审计接口至少要返回最终任务窗口和调整原因。

批量策略要求相位差方案数量为 0 或与绿信比方案完全相同。它保证成组关系，但没有检查每个站点 ID 是否一一对应、是否存在重复站点或目标版本是否不同。

### 28.5.1 下发是一条三级流水线

上面的 `downloadPlanTask` 只负责“建任务”。真正把方案送到设备要经过三级：

1. ai-auxiliary 每分钟第 15 秒组装任务（`DownloadPlanTask.java`）；
2. integration-data 的 ElasticJob 每分钟取待下发任务推设备（`DownloadPlanTaskJob.java`）；
3. 设备侧单向往 TCP 写，Redis 关联 ACK，窗口 8 秒（`VendorAControlServiceImpl.java`）。

三级之间没有分布式事务。`downloadPlanTask` 上的 `@Transactional` 只覆盖本地两次插入；Feign 建任务成功而本地回滚、或本地成功而任务未建，都可能留下不一致。

三处已知缺陷直接影响这条流水线：

- `downloadLock` 的返回值被丢弃（`VendorASplitPlanTaskHandleService.java`），并发锁实际不生效；
- 同一批次所有路口按第一个路口的厂商处理，混装厂商时协议错误；
- ai-auxiliary 侧回滚失败无上限重试，阻塞调度线程。

第 21.1.3 节给出了完整时间轴。阅读这一段代码时，先数清楚“一次下发”跨了几个进程、几个定时器和几个超时，再谈事务边界。

## 28.6 批次状态查询的代码边界

`checkDownload` 遇到子区相位差任务为空时执行：

```java
if (CollectionUtils.isEmpty(offsetTaskList)) {
    result.errorResult(IntegResultEnum.RESULT_NUM_IS_ZERO);
}

for (
    DownloadOffsetPlanTask downloadOffsetPlanTask :
    offsetTaskList
) {
    if (
        DownloadStatusEnum.SUCCESS.getValue()
            .equals(downloadOffsetPlanTask.getStatus())
        || !offsetPlanTaskMap.containsKey(
            downloadOffsetPlanTask.getSiteId()
        )
    ) {
        offsetPlanTaskMap.put(
            downloadOffsetPlanTask.getSiteId(),
            downloadOffsetPlanTask
        );
    }
}
```

`errorResult` 的结果没有立即返回。空列表不会进入循环，后续站点检查会把缺失相位差解释为单站点失败，最终再用新的 `defaultSuccess` 包装批次结果。调用者可能同时得到错误码和一个带 `success=false` 的成功响应模型。

这类不变量应通过一个明确状态类型表达：

```text
batch_complete(observed)
batch_partial(site_results)
batch_unknown(missing_tasks, retry_after)
batch_invalid(request_error)
```

返回对象不能同时声称“查询成功”和“批次字段失败”而不说明层级。

## 28.7 前端刷新和异步竞态

路口自动控制页面使用 120 秒公共刷新周期：

```javascript
export const REFRESH_INTERVAL = 120000;
```

完整创建钩子如下：

```javascript
created() {
  this.timer = setInterval(async () => {
    console.info("[AI控制路口详情timer]: 准备刷新");
    this.refresh({ page: "site" });
    await this.getDetailInfo();
  }, REFRESH_INTERVAL);
}
```

`this.refresh` 没有 `await`。如果它是异步 action，下一轮计时器触发时，上一轮详情查询和全局刷新可能仍未完成。页面不会自动取消旧请求，也没有看到以选中站点 ID 和请求序号拒绝迟到响应的逻辑。

前端的“实时”由三层延迟叠加：

```text
设备上报周期
  + Flink 水位线与窗口等待
  + 页面 120 秒轮询
```

页面需要在每个字段旁显示 `observedAt`，在整页显示 `refreshedAt`。仅显示一个绿色在线图标无法表达几分钟前的运行状态。

## 28.8 平台链路需要保留的记录

一个生产推荐需要至少跨过：

具体见表 28-1。
表 28-1 平台链路需要保留的记录
| 层 | 实际代码 | 记录 |
|---|---|---|
| Kafka | `Automobile2Lane1MinJob` | event time、watermark、partition key |
| Flink 指标 | `CrossIndexProcessFunction` | 窗口、质量、容量、流向拆分 |
| Java 服务组织 | `AiComputeServiceImpl` | 业务前置条件、Feign 结果 |
| Java 转换 | `AiComputeHelper` | Stage、时长模式和显示结构 |
| 方案下发 | `ControlServiceImpl` | 批次、相位差、任务 |
| 前端 | `AutoControlSite` | 刷新、实体和状态展示 |

一层记录只证明自己，不足以证明控制成功。验收时要从代码中找出各层的输入、输出、时间和失败状态。

## 28.9 小结

这一章沿一条真实请求和一条真实下发，把平台链路拆成六层记录：Kafka 的事件时间与分区键、Flink 的窗口与质量、Java 的组织与转换、下发服务的批次与任务、前端的刷新与状态展示。各层都能证明自己做了什么，但没有一层能单独证明“控制成功”；只有把目标、命令、观测和评价放进同一条时间线，才能判断方案是否真正生效、效果是否真的改善。

全书正文到这里结束。附录提供符号、公式速查、数据字典、接口映射、实验环境、源码路线、使用边界与安全、参考资料、故障图谱、课程设计、练习思路和参数来源；后记回到写这本书的出发点。如果全书只留下一句话，希望是全书反复追问的三件事：时间以谁为准，状态存在哪里，依据是什么。

## 第七部分评点：源码是战场，不是附录

很多技术书把生产代码放在最后，像附录一样，表示“我们也看过真实系统”。

这一部分不是这个意思。第 25～28 章回到 WaySense 的源码，是为了看前面建立的模型在真实系统里怎样变形、哪里丢失、哪里靠人工补位。字段名、事务边界、批量下发、前端刷新，这些细节不是“实现”，它们决定了控制方案能不能活着到达路口。

读源码时，不要只看主路径。主路径通常写得最整齐；失败分支、默认值、异常捕获和兼容代码，才是系统真正的性格。一个 `Confidence=1` 的默认值，可能比一整段优化算法更能解释现场为什么失真。

这一部分也不打算把生产代码写成教材。它保留真实函数名和字段名，省略依赖和上下文；读者要看的是判断，不是照抄。

读这一部分，不妨把源码当成案发现场，而不是标准答案。它的价值不在于证明系统正确，而在于指出系统在哪里假装正确。

## 练习

以下问题同时作为源码实验。

1. 给 `fetchAiComputeSiteResult` 注入 Feign 返回 null，复现空指针并设计正确错误响应。
2. 构造两个内容相同的不同 Java String，验证重算分支的 `!=` 问题。
3. 用同一路口 ID 的两条计划检查 `downloadPlanTask` 是否允许多任务。
4. 让绿信比任务成功、相位差任务失败，画出本地事务和设备副作用的时间线。
5. 让批次没有相位差任务，观察 `checkDownload` 的最终返回字段。
6. 用事件时间超出 watermark 的样本构造 1 分钟窗口，确认迟到边界。
7. 将前端刷新改成单飞请求，要求同一时刻只有一个详情请求，并能拒绝上一实体的迟到响应。
8. 用图表列出目标、命令、观测和评价四个时间戳，解释它们为何不能合并。

