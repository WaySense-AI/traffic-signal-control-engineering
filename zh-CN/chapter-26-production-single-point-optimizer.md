---
layout: default
title: "第 26 章 生产单点优化器：从周期到阶段时长"
nav_order: 261
parent: "第七部分 生产源码精读"
---

# 第 26 章 生产单点优化器：从周期到阶段时长

> 本章代码为生产源码摘录，省略 import、依赖注入、日志和其他方法；不能单独运行。

第 25 章把流量一路送到算法入口；这一章看入口之后，周期和阶段时长到底怎么算出来。生产单点优化不存在一条唯一的“标准调用”。同一套实现里至少有 `SingleNodeOpt`、`SingleNodeOptModel`、`SingleNodeOptNaive`、`MinuteSingleNodeAdaptive` 和 `SingleAdaptive` 五条路径。它们共享部分概念，却使用不同的周期模型、候选方案和修复规则。把这些路径统称为“AI 配时”会让代码阅读失去意义。

本章选择两个当前最关键的 Python 实现：离线方案库生成的 model 路径，以及分钟/周期自适应使用的 `SingleAdaptive`。先读 Webster 的数值计算，再读外层调度和数据转换。

## 26.1 入口与调用链

方案库中的 Java Feign 路由到达：

```text
IAiCommputeClient.aiComputeSitePlans
  -> GET /get_site_pattern_lib
  -> pretreatment.apiserver.get_site_pattern_lib
  -> pretreatment.task_optimization.SinglePointOptimization
  -> SingleNodeOptNew
  -> SingleNodeOptModel
  -> optimize_plan_wrapper
  -> signal_model_optimize
```

SDK 自适应路由则到达：

```text
POST /lightflow/cycleadptive
  -> SingleAdaptive.adaptive_single
```

两条路径对“周期”的定义不同。前者对 96 个 15 分钟窗口做单点模型优化，再划分时段；后者读取已有方案池，在同一相序方案中调整周期和绿信比。

同一个 `SingleNodeOptNew` 还会在入口处分派（`single_opt.py`）：

```python
if pwl_gmin is None:
    return SingleNodeOptModel(...)
else:
    min_cycle_time = min(flow_cycle_labels.values())
    max_cycle_time = max(flow_cycle_labels.values())
    return SingleNodeOptNaive(...)
```

也就是说，“走模型优化还是走梯度绿灯”由这个路口有没有配置 `pwl_gmin` 决定，不由请求参数决定。两条路径的周期上下限来源也不同：后者直接用 `flow_cycle_labels` 的最小值和最大值。

默认参数还制造了一个平台与 SDK 的差异：平台路径不传 `num_cluster`，落到函数默认值 5；SDK 路由 `/lightflow/singlenodeopt` 的默认值是 3。同一个路口，从平台点和从 SDK 调，时段划分可能不同。

## 26.2 Webster 适配层的完整实现

`flowinfra/algorithms/webster.py` 的 `Webster.get_cycle` 如下：

```python
@staticmethod
def get_cycle(
    key_movements: List[Tuple[Direction, Movement]],
    green_loss: Dict[Tuple[Direction, Movement], Num],
    y: Dict[Tuple[Direction, Movement], Num],
    x_p=0.9,
    gamma=1.5,
    delta=5,
):
    if not isinstance(x_p, Mapping):
        x_p = {mov: x_p for mov in key_movements}
    L_ = sum(green_loss[mov] for mov in key_movements)
    Y = sum(y.get(mov, mean(y.values())) / x_p[mov] for mov in key_movements)
    if Y >= 0.97:
        Y = 0.97
    C_0 = (gamma * L_ + delta) / (1 - Y)
    return C_0
```

这段代码和许多教材中的 Webster 公式有一个关键差异：生产实现把关键流量比 `Y` 限幅到 `0.97`，而不是在 `Y>=1` 时直接报不可行。`0.97` 使分母最小为 `0.03`，从而避免除零和无有限值。

这个限幅是数值保护，不是容量证明。`Y=1.10` 和 `Y=0.97` 在这里会得到同一个分母，随后仍由外部周期上下限和饱和度评价处理过饱和。阅读结果时如果只看到周期，不看原始 `Y`，会误以为严重过饱和已经被算法解决。

`Webster.solve` 完整方法如下：

```python
@staticmethod
def solve(
    phase_info: Dict[Any, Set[Tuple[Direction, Movement]]],
    movement_traffic_volume_ratio: Dict[Tuple[Direction, Movement], Num],
    *,
    skip_right_phase=True,
):
    solver = pywraplp.Solver(
        "Webster",
        pywraplp.Solver.GLOP_LINEAR_PROGRAMMING,
    )
    objective = solver.Objective()
    objective.SetMinimization()

    stages = dict()
    for stage_no in phase_info:
        stage = solver.NumVar(0, solver.infinity(), str(stage_no))
        stages[stage_no] = stage
        objective.SetCoefficient(stage, 1)

    constraint = dict()
    for stage_no, movements in phase_info.items():
        for mov in movements:
            if skip_right_phase and mov[1] is Movement.right:
                continue
            if mov not in constraint:
                constraint[mov] = solver.Constraint(
                    movement_traffic_volume_ratio.get(
                        mov,
                        mean(movement_traffic_volume_ratio.values()),
                    ),
                    solver.infinity(),
                )
            constraint[mov].SetCoefficient(stages[stage_no], 1)

    solver.Solve()
    Y = objective.Value()
    basic_solution = {
        stage_no: stage.solution_value()
        for stage_no, stage in stages.items()
    }

    results = list()
    stage_list = list(stages.values())
    for stage_post, stage_pre in zip(
        stage_list,
        stage_list[1:] + [stage_list[0]],
    ):
        objective.SetCoefficient(stage_post, 1)
        objective.SetCoefficient(stage_pre, 1 + 1e-6)
        solver.Solve()
        results.append(
            {
                stage_no: stage.solution_value()
                for stage_no, stage in stages.items()
            }
        )

    results = uniq(results, *phase_info)
    result = dict_map(
        lambda x: x / len(results),
        reduce(
            lambda x, y: reduce_dicts(x, y, operator.add),
            results,
        ),
    )
    if not abs(Y - sum(result.values())) < 1e-6:
        warnings.warn(
            f"Solution error with basic solution: {basic_solution} "
            f"and results: {results}"
        )
        result = basic_solution
    return result
```

该实现先建立覆盖 LP，再依次给相邻阶段施加 `1e-6` 的微小偏置并重复求解，最后去重、平均。目的是减少多个等价最优解之间的任意性。每个阶段变量表示有效绿色比例，约束要求每个流向的需求被一个或多个阶段覆盖。

右转默认可跳过。代码认为右转常与直行连续或受较少控制，具体安全规则仍应来自相位和通道配置。阅读结果时需要知道 `skip_right_phase=True`，否则会用错误的覆盖约束解释阶段比例。

`Webster.optimize` 再把比例转成秒：

```python
@staticmethod
def optimize(
    q,
    S,
    phase_info,
    green_loss,
    x_p=0.9,
    cycle_lim=[40, 180],
):
    y = reduce_dicts(q, S, operator.truediv)
    green_splits_ratio = Webster.solve(
        phase_info,
        y,
        skip_right_phase=True,
    )
    key_route = max(
        (
            i
            for i in Webster.get_routes(phase_info)
            if not any([j[1] is Movement.right for j in i])
        ),
        key=lambda route: Webster.get_cycle(
            route,
            green_loss,
            y,
            x_p=x_p,
        ),
    )
    key_cycle = Webster.get_cycle(
        key_route,
        green_loss,
        y,
        x_p=x_p,
    )
    loss_time = sum(green_loss[mov] for mov in key_route)
    green = {
        stage_no: (
            clip(key_cycle, cycle_lim) - loss_time
        )
        * splits
        / sum(green_splits_ratio.values())
        for stage_no, splits in green_splits_ratio.items()
    }
    return green
```

`cycle_lim` 使用可变列表默认参数。`WebsterAdapter.optimize` 又会执行：

```python
cycle_lim[0] = max(cycle_lim[0], 15 * len(plan.duration))
```

如果调用者没有传入新列表，修改会保留到下一次调用。Python 默认参数只创建一次，这是实际的可重入风险。工程代码应使用 `None` 然后创建新列表，或明确复制。

Adapter 的最小绿修复为：

```python
@staticmethod
def fix_min_green(plan: StagePlan, min_green=14):
    movement_green: defaultdict = defaultdict(int)
    movement_stage = defaultdict(set)
    for stage_no, movements in plan.phase_info.items():
        for mov in movements:
            movement_green[mov] += plan._data["StageList"][stage_no][
                "Green"
            ]
            movement_stage[mov].add(stage_no)
    for mov, green in movement_green.items():
        if green < min_green:
            delta = (min_green - green) / len(movement_stage[mov])
            for stage_no in movement_stage[mov]:
                plan._data["StageList"][stage_no]["Green"] += delta
                for inner_mov in plan.phase_info[stage_no]:
                    movement_green[inner_mov] += delta
    plan._update_cycle()
```

它只增加低绿阶段，没有从其他阶段扣除等量时间。`_update_cycle()` 随后按全部灯色重新求和周期。因此这里的“修复”会把周期增大，而不是在不变量 `cycle == 原目标周期` 下修复。上层如果仍使用原周期去做设备校验，就会发生不一致。

### Webster 未进入调用链：唯一调用点参数错位

`WebsterAdapter.optimize` 的签名是 `optimize(plan, volume, saturated_flow_rate, cycle_lim=[45,180], x_p=0.9)`（`webster.py`）。全仓唯一调用点在 `rosea_songjiang/modules/evaluator/diff.py`：

```python
webster_plan = WebsterAdapter.optimize(
    segment, data[0]['DirectionFlow'], self._lane, orig_plan)
```

四个实参里，第一个 `segment` 不是 `StagePlan`，第四个 `orig_plan` 落到了 `cycle_lim` 上。函数第一行 `cycle_lim[0] = max(...)` 就会对 `BasePlan` 取下标。

因此这套 Webster 实现尚未进入生产调用链：线上单点的周期来自 `SingleNodeOptModel` 的分段周期模型和 `signal_robust_optimize`，不是 Webster。第 11 章把它当作参考模型讲解，这里给出它没有进入生产链的证据。

### `solve` 没有覆盖检查

`Webster.solve` 的约束是按 `phase_info` 里的阶段-流向表建的（`webster.py`），只为出现过的流向建约束。关键流向如果没有被任何阶段服务，它不会进入约束，LP 也不会报不可行；若所有阶段都为空，阶段变量全为 0，后续 `optimize` 里的 `sum(green_splits_ratio.values())` 还会除以 0。

第 11.7 节给出的三步检查（覆盖集合、预算检查、归一化回代）在这里同样适用。这三步在现有实现里还没有实现，所以“LP 求解成功”不能证明关键流向都拿到了绿。

## 26.3 离线单点模型的完整主循环

`SingleNodeOptModel` 是当前方案库 model 路径的主体。完整函数如下：

```python
@timer
def SingleNodeOptModel(
    raw_data,
    sat_flow_table_input: Dict[str, Dict[str, float]],
    obj_weight: int,
    num_cluster: int = 5,
    dist_limit: float = 3,
    cycle_step: int = 4,
    flow_cycle_labels: dict = None,
    flow_cycle_model_type="linear",
    visualization: bool = False,
):
    logger.add(
        f'./debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        level="DEBUG",
    )
    logger.info(f"starting single node optimization")

    opt_plan = []
    raw_data, translator = translate_single_raw_data(raw_data)
    sat_flow_table_input = raw_data.get("AlgoConfig").get(
        "sat_flow_table_input",
        None,
    )
    data = prepare_offline_single_node_opt_input(raw_data)
    saturated_flow_table = prepare_saturated_flow_table_input(
        sat_flow_table_input
    )

    cycle_model = init_cycle_model(
        flow_cycle_labels,
        flow_cycle_model_type,
    )
    plan_data = {
        plan["PlanID"]: plan for plan in data["PlanPool"]
    }
    lane_data = {
        lane["LaneID"]: (
            lane["Direction"],
            lane["Movement"],
        )
        for lane in data["Lane"]
    }
    (
        candidate_plans,
        candidate_stage_seq,
        candidate_dual_ring_plan,
    ) = prepare_candidate_plans(plan_data=plan_data)
    flow_table, flow_ratio_table = get_flow_ratio_table_new(
        volume_data=data["DirectionFlow"],
        saturated_flow_table=saturated_flow_table,
    )
    params = {
        "candidate_plans": candidate_plans,
        "candidate_dual_ring_plan": candidate_dual_ring_plan,
        "saturated_flow_table": saturated_flow_table,
        "cycle_model": cycle_model,
        "cycle_step": cycle_step,
        "obj_weight": obj_weight,
        "lane_data": lane_data,
        "usage": "cycle_only",
    }

    fs, fratios = [], []
    for i in range(96):
        s_hr, s_mi = divmod(i * 15, 60)
        (e_hr, e_mi), e_sec = divmod((i + 1) * 15, 60), 0
        if e_hr == 24:
            e_hr, e_mi, e_sec = 23, 59, 59
        flow_trange = (
            datetime.time(s_hr, s_mi),
            datetime.time(e_hr, e_mi, e_sec),
        )
        if flow_trange not in flow_table.index:
            logger.warning(
                f"Time period {flow_trange} data missing"
            )
            fs.append(None)
            fratios.append(None)
            continue
        fs.append(flow_table.loc[flow_trange].to_frame().T)
        fratios.append(
            flow_ratio_table.loc[flow_trange].to_frame().T
        )

    segm_data = [
        optimize_plan_wrapper(fs[i], fratios[i], params)
        for i in range(96)
    ]
    logger.info(f"get segment plan data:{segm_data}")

    logger.info(f"starting single node time segment")
    segm_plan_green_list = prepocess_seg_data(
        segm_data,
        candidate_stage_seq,
    )
    logger.info(
        "get standard segment plan green list:{}".format(
            [
                [
                    (s.strftime("%H:%M"), e.strftime("%H:%M")),
                    g,
                ]
                for (s, e), g in segm_plan_green_list
            ]
        )
    )

    list_segm = segment_day_time_ordinal(
        flow_table,
        [p[0].cycle for p in segm_data],
        visualization=visualization,
    )
    logger.info(f"get segment time plan:{list_segm}")
    logger.info(
        f"number of segment plan data:{len(list_segm)}"
    )

    params["usage"] = "plan"
    for segm in list_segm:
        logger.info(
            "Starting:: {}-{} ".format(
                segm["StartTime"],
                segm["EndTime"],
            )
        )
        (
            segm_direction_flow,
            segm_direction_flow_ratio,
        ) = get_segm_flows(
            flow_table,
            flow_ratio_table,
            segm,
        )
        chosen_plan = optimize_plan_wrapper(
            segm_direction_flow,
            segm_direction_flow_ratio,
            params,
        )[0]
        logger.info(
            "Cycle: {} Duration: {}".format(
                chosen_plan.cycle,
                chosen_plan.stage_lights,
            )
        )

        plan_adj = chosen_plan.to_output(rm_greenflash=True)
        opt_plan.append(
            {
                "CrossID": raw_data["Topology"]["lane_list"][0][
                    "CrossID"
                ],
                "StartTime": segm["StartTime"],
                "EndTime": segm["EndTime"],
                "Cycle": plan_adj["Cycle"],
                "Stages": plan_adj["Stages"],
                "PlanID": plan_adj["PlanID"],
            }
        )

    return translate_single_result(opt_plan, translator)
```

主循环的执行顺序是：

1. 转换输入，建立饱和流率表。
2. 建立候选方案、阶段序列和对偶环结构。
3. 将方向流量转换成结构化的 `flow_table` 和 `flow_ratio_table`。
4. 对 96 个 15 分钟窗口分别生成周期级方案。
5. 根据各窗口方案划分时段。
6. 对每个时段求代表流量，再生成完整阶段方案。

`segm_data` 中每个元素来自 `optimize_plan_wrapper`，后者在 `direction_flow is None` 时返回空列表。随后 `segment_day_time_ordinal` 访问 `p[0].cycle`。如果 96 个窗口中有缺失窗口，这里可能对空列表取索引。该边界需要在真实输入测试中验证，不能仅凭主流程顺畅就认为缺失数据已处理。

这个函数还有一个参数被覆盖的问题。`sat_flow_table_input` 是入参（26.3 开头签名），但函数体又执行：

```python
sat_flow_table_input = raw_data.get("AlgoConfig").get(
    "sat_flow_table_input",
    None,
)
```

调用方传入的表被直接丢弃；如果 `raw_data` 没有 `AlgoConfig`，`raw_data.get("AlgoConfig")` 返回 `None`，再调用 `.get` 会抛 `AttributeError`。参数到底以哪一份为准，代码没有说明，也没有合并策略。这会让“配置了饱和流率”和“实际使用默认值”在日志里看起来一样。

## 26.4 自适应入口的完整周期函数

`althms/adaptive_single.py` 的周期函数如下：

```python
@staticmethod
def cycle_opt(settings: dict, ds: float = None):
    c_min_cycle = settings["c_min_cycle"]
    step_cycle_one = settings["step_cycle_one"]
    step_cycle_two = settings["step_cycle_two"]
    c_main_cycle = settings["c_main_cycle"]
    c_max_cycle = settings["c_max_cycle"]

    min_saturation = settings["min_saturation"]
    step_saturation_one = settings["step_saturation_one"]
    step_saturation_two = settings["step_saturation_two"]
    main_saturation = settings["main_saturation"]
    max_saturation = settings["max_saturation"]

    if ds <= min_saturation:
        cycle = c_min_cycle
    elif ds <= step_saturation_one:
        cycle = step_cycle_one
    elif ds <= step_saturation_two:
        cycle = step_cycle_two
    elif ds <= main_saturation:
        cycle = (
            (ds - step_saturation_two)
            / (main_saturation - step_saturation_two)
        ) * (c_main_cycle - step_cycle_two) + step_cycle_two
    elif ds <= max_saturation:
        cycle = (
            (ds - main_saturation)
            / (max_saturation - main_saturation)
        ) * (c_max_cycle - c_main_cycle) + c_main_cycle
    else:
        cycle = c_max_cycle

    return round(cycle)
```

此函数没有检查 `main_saturation == step_saturation_two` 或 `max_saturation == main_saturation`。如果配置阈值相等，插值区间会除零。参数来自数据库或配置时，需要有启动校验，而不能只依赖 Python 抛异常。

`pattern_selected` 的完整过滤器如下：

```python
@staticmethod
def pattern_selected(plan_pool: list, OriginalPlan: dict):
    total_plan = list()
    str1 = ""
    stage_list = OriginalPlan["Stages"]
    for stage in stage_list:
        str1 += stage["PhasestageNo"]

    for plan in plan_pool:
        str2 = ""
        stlist = plan["Stages"]
        for st in stlist:
            str2 += st["PhasestageNo"]

        if str1 == str2:
            total_plan.append(plan)

    return total_plan
```

过滤条件是阶段编号字符串拼接相等。`["A", "BC"]` 与 `["AB", "C"]` 会产生相同的 `"ABC"`，当前代码没有分隔符，也没有比较阶段内容或配置版本。阶段编号通常是单字符，但这是隐式约束，需要在数据校验中明确。

## 26.5 阶段流量映射的完整实现

`flow_switch` 完整方法如下：

```python
@staticmethod
def flow_switch(dir_flow_list: list, OriginalPlan: dict):
    dir_flow_dict = dict()
    dir_ds_dict = dict()

    for dir in dir_flow_list:
        key = str(dir["Direction"]) + str(dir["Movement"])
        value_flow = dir["Volume"]
        value_ds = dir["Occupancy"]
        dir_flow_dict.update({key: value_flow})
        dir_ds_dict.update({key: value_ds})

    overlapping_phase_dict = SingleAdaptive.overlapping_phase(
        OriginalPlan
    )
    StageList = OriginalPlan["Stages"]
    stage_flow_dict = dict()
    stage_ds_dict = dict()

    for st in StageList:
        PhasestageNo = st["PhasestageNo"]
        PhaseList = st["Phase"]
        stage_time = st["PhasestageTime"]
        flow_stage = 0
        ds_stage = 0.00
        for ph in PhaseList:
            phase_id = ph["PhaseID"]
            dir = ph["Direction"]
            mov = ph["Movement"]
            tem = str(dir) + str(mov)
            mingreen = ph["MinGreenTime"]

            if tem not in dir_flow_dict.keys():
                continue

            if phase_id in overlapping_phase_dict.keys():
                dir_flow_dict[tem] = math.ceil(
                    dir_flow_dict[tem]
                    * stage_time
                    / overlapping_phase_dict[phase_id]
                )

            if flow_stage < dir_flow_dict[tem]:
                flow_stage = dir_flow_dict[tem]
            if ds_stage < dir_ds_dict[tem]:
                ds_stage = dir_ds_dict[tem]

        stage_flow_dict.update({PhasestageNo: flow_stage})
        stage_ds_dict.update({PhasestageNo: ds_stage})

    flow = round(np.max(list(stage_flow_dict.values())))
    return flow, stage_ds_dict, stage_flow_dict
```

对于搭接相位，`dir_flow_dict[tem]` 会在每个阶段被就地改写。第二遍读取时使用的是上一轮缩放后的值，而不是原始方向流量。因此结果依赖阶段顺序和搭接阶段个数。

设方向流量 900，搭接出现在两个各占一半的阶段。第一遍变为 `ceil(450)`，第二遍又在此基础上变为 `ceil(225)`，不是两个阶段都得到 450。若意图是“每个阶段按持续时间占比分配且总和不变”，应先保存原始流量，再用局部变量计算，不能修改输入字典。

## 26.6 阶段时长分配与最小绿

`split_assign` 是当前自适应实现的核心。完整方法如下：

```python
@staticmethod
def split_assign(
    planpool: list,
    cycle: int,
    PlanNo: int,
    stage_flow_dict: dict,
):
    pattern_selected = dict()
    pattern_opt = dict()

    for plan in planpool:
        if plan["PlanNo"] == PlanNo:
            pattern_selected = plan
            pattern_opt = plan
            break

    stage_percent_org = dict()
    stagelist = pattern_selected["Stages"]
    for sl in stagelist:
        key_stage = sl["PhasestageNo"]
        pv = sl["PhasestageTime"]
        stage_percent_org.update({key_stage: pv})

    stage_percent = dict()
    for item in stage_percent_org.items():
        key = item[0]
        if sum(stage_flow_dict.values()) != 0:
            value = int(
                0.7 * item[1]
                + 0.3
                * stage_flow_dict[key]
                * sum(stage_percent_org.values())
                / sum(stage_flow_dict.values())
            )
        else:
            value = item[1]
        stage_percent.update({key: value})
    logging.debug(
        f"Optional stage_percent: {stage_percent}"
    )

    stageoptlist = list()
    count = 0
    stage_sum = 0
    to_increase_time = 0

    for sol in stagelist:
        added_time = 0
        key_stage = sol["PhasestageNo"]
        sol["PhasestageSign"] = 2

        if sol["Joint"]:
            min_green_time = 10
        else:
            min_green_time = max(
                i["MinGreenTime"] for i in sol["Phase"]
            )

        if count < (len(stagelist) - 1):
            sol["PhasestageTime"] = int(
                cycle
                * stage_percent[key_stage]
                / sum(stage_percent.values())
            )
            stage_sum += sol["PhasestageTime"]
        else:
            sol["PhasestageTime"] = cycle - stage_sum

        sol["Light"]["Green"] = (
            sol["PhasestageTime"]
            - sol["Light"]["GreenFlash"]
            - sol["Light"]["Yellow"]
            - sol["Light"]["Red"]
        )

        if sol["Light"]["Green"] < min_green_time:
            added_time = min_green_time - sol["Light"]["Green"]
            sol["Light"]["Green"] += added_time
            sol["PhasestageTime"] += added_time
            to_increase_time += added_time

        stageoptlist.append(sol)
        count += 1

    logging.debug(f"Optional cycle: {cycle}")
    cycle += to_increase_time
    logging.info(f"Final cycle is {cycle}")

    pattern_opt.update({"Cycle": cycle})
    pattern_opt.update({"Stages": stageoptlist})
    return pattern_opt
```

这段代码有一个明确的周期关系：

```text
目标周期 cycle
  -> 按整数比例先分给前 n-1 个阶段
  -> 最后一个阶段吸收舍入余量
  -> 每个阶段反推纯绿
  -> 低于最小绿时增加纯绿和阶段总时长
  -> 最终周期 += 所有补绿量
```

因此返回的 `Cycle` 不是 `cycle_opt` 的目标周期。上层需要把返回周期当成新方案事实，不能继续用原来周期做下发或协调。若设备目标时间是 90 秒，而算法返回 94 秒，需要明确这是算法主动改变周期，还是应拒绝并重新求解。

还有一处对象别名问题。`split_assign` 里先执行 `pattern_opt = plan`，随后 `pattern_opt.update({"Cycle": ...})` 和 `pattern_opt.update({"Stages": ...})`。`pattern_opt` 与 `planpool` 里的 `plan` 是同一个字典，这两次更新会**原地修改方案池中的原方案**。如果同一方案池被多个窗口、多次调用复用，后一次计算会看到前一次被改过的 `Cycle` 和 `Stages`，结果依赖调用顺序。正确做法是先 `copy.deepcopy(plan)` 或构造新字典，再写结果。

## 26.7 自适应主入口的完整实现

完整入口如下：

```python
@staticmethod
def adaptive_single(data: dict, settings: dict):
    dir_flow_list = data["TrafficVolume"]["DirectionFlow"]
    OriginalPlan = data["OriginalPlan"]

    original_plan = StagePlan(
        OriginalPlan,
        custom_min_cycle=settings["c_min_cycle"],
        custom_max_cycle=settings["c_max_cycle"],
    )
    indicator = TrafficIndicator(
        plan=original_plan,
        direction_flow=dir_flow_list,
        saturated_flow_straight=None,
        saturated_flow_left=None,
        saturated_flow_right=None,
    )
    ds = indicator.sum_flow_ratio

    logging.info(
        "SUM FLOW RATIO: {} ".format(
            indicator.sum_flow_ratio
        )
    )

    flow, stage_ds_org, stage_flow_dict = (
        SingleAdaptive.flow_switch(
            dir_flow_list,
            OriginalPlan,
        )
    )
    cycle_org = SingleAdaptive.cycle_opt(settings, ds)
    plan_pool = SingleAdaptive.pattern_selected(
        data["PlanPool"],
        OriginalPlan,
    )
    PlanNo = SingleAdaptive.split_opt_saturation(
        planpool,
        OriginalPlan,
        stage_ds_org,
    )
    pattern_opt = SingleAdaptive.split_assign(
        pool,
        cycle_org,
        PlanNo,
        stage_flow_dict,
    )
    return pattern_opt, PlanNo, cycle_org
```

这段实现包含三个命名问题：

- 过滤结果赋给 `plan_pool`，调用 `split_opt_saturation` 时却使用未定义的 `planpool`。
- 同一过滤结果再次传入 `split_assign` 时使用未定义的 `pool`。
- 返回的第三个值仍是初始 `cycle_org`，而 `pattern_opt` 可能因最小绿修复具有更大周期。

因此该入口到达此函数时会触发 `NameError`。即使把变量名统一，返回周期也需要改为实际 `pattern_opt["Cycle"]`，否则调用者会记录一个与方案阶段总时长不一致的目标周期。

## 26.8 本章源码结论

生产单点优化包含三种不同语义：

具体见表 26-1。
表 26-1 本章源码结论
| 层 | 产物 | 典型周期处理 |
|---|---|---|
| Webster LP | 有效绿比例 | 理论周期后再限幅和设备分配 |
| 离线模型优化 | 96 个窗口方案和时段方案 | 周期模型生成，时段动态规划 |
| 自适应方案池 | 同相序方案和阶段时长 | 分段周期、min-max 饱和度、加权分配 |

不能用一条“Webster 公式”概括它们。代码中的边界、候选过滤、整数化、最小绿和命令前校验分别属于不同层。

## 26.9 小结

生产单点优化没有唯一标准调用，至少五条路径、三种周期语义并存：Webster LP 给有效绿比例，离线模型给 96 个窗口方案和时段方案，自适应方案池给同相序方案和阶段时长。读源码时先确认“这是哪条路径、周期由谁产生、修复后谁重新读取”，再看具体公式；否则很容易把某一层的限幅当成整个系统的算法。

单点优化器解决了“一个路口怎么算”，第 27 章把镜头拉到路口之间：子区、公共周期、MaxBand 和时空图在生产代码里如何串成一条区域协调链路。

## 练习

以下问题同时作为源码实验。

1. 用 `Y=0.95`、`0.97`、`1.10` 分别调用 `Webster.get_cycle`，解释限幅后的周期。
2. 构造多个等价覆盖 LP 解，观察相邻阶段微扰和 `uniq` 如何改变结果。
3. 为 `fix_min_green` 写测试，证明周期会增长，并检查上层是否重新读取。
4. 用 96 个窗口中的一个缺失输入运行 `SingleNodeOptModel`，定位空列表边界。
5. 构造 `["A","BC"]` 和 `["AB","C"]`，验证 `pattern_selected` 的字符串碰撞。
6. 用同一搭接方向流量运行正序和反序阶段，比较 `flow_switch` 输出。
7. 构造目标周期 90 秒、三阶段最小绿冲突的输入，手算 `split_assign` 的新周期。
8. 用静态变量分析或最小输入复现 `adaptive_single` 的 `NameError`，给出最小修复和不变量测试。

