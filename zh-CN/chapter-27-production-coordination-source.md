---
layout: default
title: "第 27 章 生产区域协调：子区、MaxBand 与时空图"
nav_order: 271
parent: "第七部分 生产源码精读"
---

# 第 27 章 生产区域协调：子区、MaxBand 与时空图

第 26 章把单个路口的周期和阶段时长算完；这一章把镜头拉到路口之间。前面第 15 至 18 章把协调拆成子区、公共周期、相位差、带宽和时空图。生产实现把这些概念放进同一份 DataFrame 契约：

```text
link_list
  -> 静态路段表
subregion_stage_plan_table
  -> 每个时段的单点 StagePlan
maxband_input_table
  -> 占比空间的窗口、速度、相序和清空参数
maxband_output_table
  -> Cycle、offset_abs、b、b_bar、sol_v、sol_v_bar
```

一个字段丢失，后续模型都可能继续输出“看起来正常”的零带宽或旧方案。本章直接阅读 `SubAreaOptNew`、`MaxbandBLPDC` 和 `GreenWaveBand`。

## 27.1 子区优化的完整入口

`lightflow/service/subregion_opt.py` 的 `SubAreaOptNew` 是当前子区方案库主要入口。完整函数如下：

```python
def SubAreaOptNew(
    raw_data,
    visualization: bool = False,
    segment_level: int = 2,
    non_coordination_sacrifice: int = 2,
    key_cross_id: Dict[str, str] = {-1: None},
    coordination_direction: Dict[str, int] = {-1: 3},
    coordination_type: Dict[str, int] = {-1: 1},
):
    logger.add(
        f'./debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        level="DEBUG",
    )
    if any([coordination_type[k] != 1 for k in coordination_type]):
        logger.warning(
            f"For now, only support coordinate_type == 1 "
            f"(greenwave), got {coordination_type}"
        )
    logger.info(f"starting sub area optimization")

    raw_data, translator = translate_area_raw_data(raw_data)
    processed_data = prepare_subregion_opt_input(raw_data)
    link_list = processed_data["link_list"]
    coordinate_mov_table = pd.DataFrame(
        {
            "CrossID": [
                cross["CrossID"] for cross in processed_data["crosslist"]
            ],
            "coordinate_dir_mov": [
                cross["coordinate_dir_mov"]
                for cross in processed_data["crosslist"]
            ],
        }
    )
    flow_table = pd.concat(
        [
            pd.DataFrame(cross_data["DirectionFlow"])
            for cross_data in processed_data["crosslist"]
        ],
        ignore_index=True,
    )
    flow_table = pd.merge(
        flow_table,
        coordinate_mov_table,
        on="CrossID",
    )
    plan_table = pd.DataFrame(
        [
            plan[0]
            for plan in pd.DataFrame(processed_data["crosslist"])["Plan"]
        ]
    )
    sat_flow_table_input = {
        cross["CrossID"]: cross.get("sat_flow_table", None)
        for cross in processed_data["crosslist"]
    }
    pwl_gmin = {
        cross["CrossID"]: cross.get("pwl_gmin", None)
        for cross in processed_data["crosslist"]
    }

    mapping_opt = MappingOpt(
        flow_table,
        plan_table,
        sat_flow_table_input=sat_flow_table_input,
        pwl_gmin=pwl_gmin,
        non_coordination_sacrifice=non_coordination_sacrifice,
    )
    green_table = mapping_opt.green_table
    cycle_table = mapping_opt.cycle_table
    Cycle_table = mapping_opt.cycle_pivot_table

    CF_input_table = CoordinatabilityFactor.prepare_CF_input_table(
        link_list,
        flow_table,
        cycle_table,
    )
    CF_table = CoordinatabilityFactor(CF_input_table).CF_table

    logger.info("Starting time segmentation")
    subregion_time_table = SubregionTimeSegment(
        Cycle_table,
        CF_table,
        CF_threshold=CF_THR_MAPPER.get(segment_level, 50),
    ).run()
    subregion_stage_plan_table = (
        Maxband.prepare_subregion_stage_plan_table(
            subregion_time_table,
            green_table,
            plan_table,
        )
    )

    subregion_stage_plan_table["st_group_id"] = (
        subregion_stage_plan_table.apply(
            lambda x: gen_group_uid(
                [
                    x["StartTime"][-8:],
                    x["EndTime"][-8:],
                    x["cross_group"],
                ]
            ),
            axis=1,
        )
    )
    numbering_df = (
        subregion_stage_plan_table.groupby("st_group_id")["CrossID"]
        .unique()
        .reset_index()
    )
    numbering_df["CrossID"] = numbering_df["CrossID"].apply(
        lambda x: "_".join(
            [i[:8] for i in sorted(x)]
        )
    )
    numbering_df["group_id"] = pd.factorize(
        numbering_df["CrossID"]
    )[0]
    numbering_dic = {
        d["st_group_id"]: d["group_id"]
        for d in numbering_df[
            ["st_group_id", "group_id"]
        ].to_dict(orient="records")
    }
    subregion_stage_plan_table["st_group_id"] = (
        subregion_stage_plan_table["st_group_id"].map(
            lambda x: f"{x[:-2]}{numbering_dic[x]:02d}"
        )
    )
    logger.info(
        "Finished time segmentation, number of "
        f"space-time group: "
        f"{len(subregion_stage_plan_table['st_group_id'].unique())}"
    )

    get_fn = (
        lambda arg, x, v: arg.get(x, v)
        if -1 not in arg
        else arg[-1]
    )
    subregion_stage_plan_table["key_cross_id"] = (
        subregion_stage_plan_table["st_group_id"].map(
            lambda x: get_fn(key_cross_id, x, None)
        )
    )
    subregion_stage_plan_table["coordination_direction"] = (
        subregion_stage_plan_table["st_group_id"].map(
            lambda x: get_fn(coordination_direction, x, 3)
        )
    )
    subregion_stage_plan_table = pd.merge(
        subregion_stage_plan_table,
        coordinate_mov_table,
        on="CrossID",
    )

    logger.info("Starting compute offset via Maxband")
    maxband_input_table = Maxband.prepare_maxband_input_table(
        link_list,
        subregion_stage_plan_table,
    )
    maxband = Maxband(
        maxband_input_table,
        band_weight_mapper=BAND_WEIGHT_MAPPER,
    )
    maxband_output_table = maxband.run()
    logger.info("Finished sub area optimization")

    if visualization:
        maxband.visualization()

    plan_output = fmt_subregion_output(
        maxband_output_table,
        CF_table,
        raw_data["RegionID"],
    )
    return translate_area_result(plan_output, translator)
```

该入口先做单点映射，再计算可协调性，再做时空分段，最后把每个时空组送入 MaxBand。`segment_level` 通过 `CF_THR_MAPPER` 转成阈值：

```python
CF_THR_MAPPER = {
    0: 0,
    1: 25,
    2: 50,
    3: 100,
}
```

所以界面上的“分组数量 0/1/2/3”不是直接聚类数，而是协调因子阈值。修改该等级会改变子区边界和 MaxBand 的输入组数。

`get_fn` 的实现使用 `if -1 not in arg` 判断是否采用全局默认。这个判断只有在字典的键能进行成员测试时才成立。对于实际传入的组 ID 映射可能包含字符串和整数混用，调用方需要保证键类型一致。

## 27.2 MaxBand 输入如何从方案构造

`MaxbandLP2.prepare_maxband_input_table_dynamic` 的完整实现如下：

```python
@classmethod
def prepare_maxband_input_table_dynamic(
    cls,
    maxband_input_table_static: pd.DataFrame,
    subregion_stage_plan_table: pd.DataFrame,
) -> pd.DataFrame:
    maxband_input_table = maxband_input_table_static.merge(
        subregion_stage_plan_table.reset_index().rename(
            columns={"CrossID": "FromCrossID"}
        ),
        on="FromCrossID",
    )

    maxband_input_table["delta_bar"] = maxband_input_table.apply(
        lambda row: 1
        if (row["FromDirection"], 11)
        in row["StagePlan"].stage_phases[0]
        else 0,
        axis=1,
    )

    maxband_input_table["delta"] = maxband_input_table.apply(
        lambda row: 1 - row["delta_bar"]
        if all(
            dir == row["FromDirection"]
            for (dir, mov) in row["StagePlan"].stage_phases[0]
        )
        else row["delta_bar"],
        axis=1,
    )

    maxband_input_table["r"] = maxband_input_table.apply(
        lambda row: 1
        - row["StagePlan"].dir_mov_green.get(
            (row["FromDirection"], 11)
        )
        / row["StagePlan"].cycle,
        axis=1,
    )

    maxband_input_table["r_bar"] = maxband_input_table.apply(
        lambda row: 1
        - row["StagePlan"].dir_mov_green.get(
            (
                direction_reverse_helper(row["FromDirection"]),
                11,
            )
        )
        / row["StagePlan"].cycle,
        axis=1,
    )

    maxband_input_table["l"] = maxband_input_table.apply(
        lambda row: row["StagePlan"].dir_mov_green.get(
            (row["FromDirection"], 12)
        )
        / row["StagePlan"].cycle,
        axis=1,
    )

    maxband_input_table["l_bar"] = maxband_input_table.apply(
        lambda row: row["StagePlan"].dir_mov_green.get(
            (
                direction_reverse_helper(row["FromDirection"]),
                12,
            )
        )
        / row["StagePlan"].cycle,
        axis=1,
    )
    (
        maxband_input_table["tau"],
        maxband_input_table["tau_bar"],
    ) = cls.prepare_maxband_input_table_tau()

    return reorder_dataframe(maxband_input_table)
```

这里 `11` 表示直行，`12` 表示左转。右转不进入当前 MaxBand 协调窗口。`delta` 和 `delta_bar` 由第一阶段是否包含直行或左转来推导，后续固定相序时作为布尔约束。

`tau` 当前没有标定实现：

```python
@classmethod
def prepare_maxband_input_table_tau(cls):
    return TAU_DEFAULT, TAU_DEFAULT
```

源码注释明确写着“排队清空时间计算逻辑并没有完成，后续需要补充完善”。使用当前 MaxBand 默认路径得到偏移时，需要把 `tau` 视为待标定参数。带宽非零不能证明清空时间正确。

静态路段表还有硬编码速度范围：

```python
df["e"] = 35 / 3.6
df["f"] = 45 / 3.6
df["e_bar"] = 35 / 3.6
df["f_bar"] = 45 / 3.6
```

注释说明这是调试临时修复。调用者传入的 `ForwardConcertSpeed` 和 `ReverseConcertSpeed` 在这个版本里没有进入优化速度边界。阅读现场方案时必须确认部署版本是否仍保留这段代码。

## 27.3 双周期 MaxBand 的完整求解主体

`MaxbandBLPDC.optimization` 完整方法如下：

```python
def optimization(
    self,
    seg_maxband_input_table: pd.DataFrame,
    cycle_down: int = -5,
    cycle_up: int = 20,
    C_min: int = 80,
    C_max: int = 220,
    b_min: float = 0.1,
) -> pd.DataFrame:
    seg_maxband_input_table = reorder_dataframe(
        seg_maxband_input_table
    )

    priors = {}
    attributes = [
        "r",
        "r_bar",
        "tau",
        "tau_bar",
        "Delta",
        "v",
        "v_bar",
        "d",
        "d_bar",
        "e",
        "e_bar",
        "f",
        "f_bar",
    ]
    for attr in attributes:
        priors[attr] = (
            seg_maxband_input_table[attr].values.tolist()
        )

    k = seg_maxband_input_table["k"].iloc[0]
    if "Cycle" in seg_maxband_input_table.columns:
        if (
            seg_maxband_input_table["key_cross_id"].iloc[0]
            is None
        ):
            critical_cycle = max(
                seg_maxband_input_table["Cycle"]
            )
            seg_maxband_input_table["key_cross_id"] = (
                seg_maxband_input_table.loc[
                    seg_maxband_input_table["Cycle"].idxmax(),
                    "FromCrossID",
                ]
            )
        else:
            critical_cross_id = seg_maxband_input_table[
                "key_cross_id"
            ].iloc[0]
            critical_cycle = max(
                seg_maxband_input_table.loc[
                    seg_maxband_input_table["FromCrossID"]
                    == critical_cross_id,
                    "Cycle",
                ]
            )
            logger.debug(
                f"Got passed key cross id: {critical_cross_id}"
            )
        seg_maxband_input_table["double_cycling"] = (
            seg_maxband_input_table["Cycle"].map(
                lambda x: abs(2 * x - critical_cycle)
                < abs(x - critical_cycle)
            )
        )
        if (
            len(seg_maxband_input_table["double_cycling"]) > 2
            and int(
                seg_maxband_input_table[
                    "double_cycling"
                ].sum()
            )
            > 1
        ):
            k = 10
        C_min = max(C_min, critical_cycle + cycle_down)
        C_max = min(C_max, critical_cycle + cycle_up)

    logger.debug(
        f"priors input to maxband: {json.dumps(priors, indent=4)}"
    )
    logger.debug(
        f"critical_cycle: {critical_cycle}, "
        f"C_min:{C_min}, C_max:{C_max}"
    )

    if int(seg_maxband_input_table["double_cycling"].sum()) == 0:
        coord_dir = int(
            seg_maxband_input_table[
                "coordination_direction"
            ].iloc[0]
        )
        results = super().opt(
            seg_maxband_input_table,
            k,
            C_min,
            C_max,
            b_min=b_min,
        )
        (
            seg_maxband_output_table,
            coord_dir_new,
        ) = super().post_opt_update_info(
            seg_maxband_input_table,
            results,
        )
        if coord_dir_new != coord_dir:
            k_new = self.band_weight_mapper.get(coord_dir_new)
            logger.warning(
                "The desired coordination direction: "
                f"{coord_dir} differs from the achieved: "
                f"{coord_dir_new}."
            )
            results = super().opt(
                seg_maxband_input_table,
                k_new,
                C_min,
                C_max,
                b_min=b_min,
            )
            (
                seg_maxband_output_table,
                _,
            ) = super().post_opt_update_info(
                seg_maxband_input_table,
                results,
            )
        seg_maxband_output_table = super().post_opt_process(
            seg_maxband_output_table
        )
    else:
        coord_dir = int(
            seg_maxband_input_table[
                "coordination_direction"
            ].iloc[0]
        )
        results = self.opt(
            seg_maxband_input_table,
            k,
            C_min,
            C_max,
            b_min=b_min,
        )
        (
            seg_maxband_output_table,
            coord_dir_new,
        ) = self.post_opt_update_info(
            seg_maxband_input_table,
            results,
        )
        if coord_dir_new != coord_dir:
            k_new = self.band_weight_mapper.get(coord_dir_new)
            logger.warning(
                "The desired coordination direction: "
                f"{coord_dir} differs from the achieved: "
                f"{coord_dir_new}."
            )
            results = self.opt(
                seg_maxband_input_table,
                k_new,
                C_min,
                C_max,
                b_min=b_min,
            )
            (
                seg_maxband_output_table,
                _,
            ) = self.post_opt_update_info(
                seg_maxband_input_table,
                results,
            )
        seg_maxband_output_table = self.post_opt_process(
            seg_maxband_output_table
        )
    return seg_maxband_output_table
```

这段代码决定是否使用双周期：当某路口周期明显接近关键周期的一半时，`double_cycling=True`。条件是**多于两个路口**（`len(...) > 2`）且**至少两个路口**采用双周期（`double_cycling.sum() > 1`）；满足后方向权重 `k` 被改为 `10`。这不是普通交通权重，而是进入双周期模型的控制分支，不能按 17.6.1 的“反向优先”去解释。

求解本身位于 `MaxbandBLPDC.opt`。完整函数如下：

```python
@staticmethod
def opt(seg_maxband_input_table, k, C_min, C_max, b_min):
    num_intersection = len(seg_maxband_input_table)
    r = np.array(seg_maxband_input_table["r"])
    r_bar = np.array(seg_maxband_input_table["r_bar"])
    tau = np.array(seg_maxband_input_table["tau"])
    tau_bar = np.array(seg_maxband_input_table["tau_bar"])
    d = np.array(seg_maxband_input_table["d"])
    d_bar = np.array(seg_maxband_input_table["d_bar"])
    e = np.array(seg_maxband_input_table["e"])
    e_bar = np.array(seg_maxband_input_table["e_bar"])
    f = np.array(seg_maxband_input_table["f"])
    f_bar = np.array(seg_maxband_input_table["f_bar"])
    Delta = np.array(seg_maxband_input_table["Delta"])
    dc = np.array(seg_maxband_input_table["double_cycling"])

    b = cp.Variable(name="b", nonneg=True)
    b_bar = cp.Variable(name="b_bar", nonneg=True)
    b_prime = cp.Variable(name="b_prime")
    b_bar_prime = cp.Variable(name="b_bar_prime")
    u = cp.Variable(boolean=True, name="u")
    u_bar = cp.Variable(boolean=True, name="u_bar")
    w = cp.Variable(num_intersection, nonneg=True, name="w")
    w_bar = cp.Variable(
        num_intersection, nonneg=True, name="w_bar"
    )
    w_next = cp.Variable(
        num_intersection - 1, nonneg=True, name="w_next"
    )
    w_bar_next = cp.Variable(
        num_intersection - 1,
        nonneg=True,
        name="w_bar_next",
    )
    m = cp.Variable(
        num_intersection - 1, integer=True, name="m"
    )
    t = cp.Variable(
        num_intersection - 1, nonneg=True, name="t"
    )
    t_bar = cp.Variable(
        num_intersection - 1, nonneg=True, name="t_bar"
    )
    z = cp.Variable(name="z", nonneg=True)

    constraints = [
        b_prime >= -1,
        b_prime <= 1,
        b_bar_prime >= -1,
        b_bar_prime <= 1,
        b_prime - b_min >= -1e6 * (1 - u),
        b_prime - b_min <= 1e6 * u,
        b_bar_prime - b_min >= -1e6 * (1 - u_bar),
        b_bar_prime - b_min <= 1e6 * u_bar,
        b >= -u,
        b <= u,
        b <= b_prime + (1 - u),
        b >= b_prime - (1 - u),
        b_bar >= -u_bar,
        b_bar <= u_bar,
        b_bar <= b_bar_prime + (1 - u_bar),
        b_bar >= b_bar_prime - (1 - u_bar),
        z >= 1 / C_max,
        z <= 1 / C_min,
    ]

    if k == 1:
        g_avg = 1 - np.mean(r)
        g_bar_avg = 1 - np.mean(r_bar)
        k = g_avg / g_bar_avg
        if k == 1:
            k += 1e-2
        constraints.append(
            (1 - k) * b_bar >= (1 - k) * k * b
        )
    elif k == 10:
        constraints.append(b_bar == 0)
    elif k == 0.1:
        constraints.append(b == 0)

    for i in range(num_intersection):
        constraints.append(w[i] + b_prime <= 1 - r[i])
        constraints.append(
            w_bar[i] + b_bar_prime <= 1 - r_bar[i]
        )

    for i in range(num_intersection - 1):
        constraints.append(
            w_next[i] + b_prime <= 1 - r[i + 1]
        )
        constraints.append(
            w_bar_next[i] + b_bar_prime <= 1 - r_bar[i]
        )

    for i in range(num_intersection - 1):
        lhs = (
            (w[i] + w_bar_next[i])
            - (w_next[i] + w_bar[i + 1])
            + (t[i] + t_bar[i])
            + Delta[i]
            - Delta[i + 1]
        )
        rhs_part1 = (
            -0.5 * (r[i] + r_bar[i])
            + 0.5 * (r[i + 1] + r_bar[i + 1])
        )
        rhs_part2 = tau_bar[i] + tau[i + 1]
        if dc[i] == dc[i + 1]:
            rhs_part3 = m[i]
        elif dc[i + 1]:
            rhs_part3 = (m[i] + 2) * 0.5
        elif dc[i]:
            rhs_part3 = 2 * m[i] + 1
        else:
            rhs_part3 = m[i]
        constraints.append(
            lhs == rhs_part1 + rhs_part2 + rhs_part3
        )

    for i in range(num_intersection - 1):
        constraints.append(z * d[i] / f[i] <= t[i])
        constraints.append(z * d[i] / e[i] >= t[i])
        constraints.append(
            z * d_bar[i] / f_bar[i] <= t_bar[i]
        )
        constraints.append(
            z * d_bar[i] / e_bar[i] >= t_bar[i]
        )

    if k == 10 or k == 0.1:
        objective = cp.Maximize(b + b_bar)
    else:
        objective = cp.Maximize(b + k * b_bar)

    problem = cp.Problem(objective, constraints)
    problem.solve(cp.CBC)

    return {
        "status": problem.status,
        "b": b.value,
        "b_bar": b_bar.value,
        "b_prime": b_prime.value,
        "b_bar_prime": b_bar_prime.value,
        "u": u.value,
        "u_bar": u_bar.value,
        "w": w.value,
        "w_bar": w_bar.value,
        "m": m.value,
        "t": t.value,
        "t_bar": t_bar.value,
        "z": z.value,
    }
```

`m` 是整数周期环绕变量，`dc` 是双周期布尔向量。`lhs` 包含窗口位置、正反向旅行时间、左转相位差；`rhs` 包含红窗中心和清空比例。这些字段可以逐项对应第 17 章的理论模型，`Maxband` 因此不是黑盒。

## 27.4 时空图扫描的完整函数

`pretreatment/service/green_wave_band.py` 的双向扫描完整方法如下：

```python
@staticmethod
def calc_green_wave_band_two_way(
    cross_list: List[CrossInfoTwoway],
    reverse=False,
):
    for cross in cross_list:
        if cross.type in (1, 2):
            break
    else:
        return []

    one_green_band: List[int] = []
    all_green_band: List[List[int]] = []
    start_timepoint = 0
    for cross in cross_list:
        if cross.distance is not None:
            if not reverse and cross.forward_speed is not None:
                start_timepoint -= (
                    cross.distance / cross.forward_speed
                )
            elif (
                reverse
                and cross.backward_speed is not None
            ):
                start_timepoint += (
                    cross.distance / cross.backward_speed
                )

        if cross.offset is not None:
            start_timepoint += cross.offset
            break

    max_cycle = max(
        i.cycle for i in cross_list if i.cycle is not None
    )
    while start_timepoint < 0:
        start_timepoint += max_cycle
    start_timepoint = math.ceil(start_timepoint)

    for timepoint in range(
        start_timepoint,
        start_timepoint + max_cycle,
    ):
        cross_timepoint = timepoint
        all_in_green = True
        for cross in cross_list:
            if cross.distance is not None:
                if (
                    not reverse
                    and cross.forward_speed is not None
                ):
                    cross_timepoint += (
                        cross.distance / cross.forward_speed
                    )
                elif (
                    reverse
                    and cross.backward_speed is not None
                ):
                    cross_timepoint -= (
                        cross.distance / cross.backward_speed
                    )

            if not cross.is_timepoint_in_green(
                cross_timepoint
            ):
                all_in_green = False
                break

        if all_in_green:
            if (
                len(one_green_band) == 0
                or one_green_band[-1] == timepoint - 1
            ):
                one_green_band.append(timepoint)
            else:
                all_green_band.append(
                    [one_green_band[0], one_green_band[-1]]
                )
                one_green_band = [timepoint]

    if one_green_band:
        all_green_band.append(
            [one_green_band[0], one_green_band[-1]]
        )
    return all_green_band
```

每个出发时刻从第一个路口开始，按路段距离/速度累计旅行时间，再检查每个路口是否处于绿灯。实现扫描一个最大周期，并把连续通过时刻压缩为区间。

这个压缩没有处理**首尾环绕**：如果一段连续绿波从周期末端延续到周期起点，扫描会在末尾得到一段、在开头得到另一段，返回两个区间，而不是合并成一个跨零点的区间。验收时如果只把区间长度相加，带宽会被低估；如果直接拿区间端点做偏移，跨周期车队会被拆开。修复方式是在扫描结束后检查首段起点是否为 `start_timepoint`、末段终点是否为 `start_timepoint + max_cycle - 1`，满足则合并并标注环绕。

`CrossInfoTwoway.is_timepoint_in_green` 判断为：

```python
def is_timepoint_in_green(self, timepoint: int):
    if self._type not in (1, 2):
        return True
    timepoint = (timepoint - self._offset) % self._cycle
    return timepoint <= self._green_light_time
```

这里使用 `<=`。若绿灯时长为 40 秒，局部时刻 40 也返回真，实际得到 41 个整秒的边界。区间输出又是闭区间 `[first,last]`，如果消费者把端点解释为包含端点，带宽会多算。这是当前源码需要验证并修正的离散时间边界。

`/gettimespace` 的入口还有一个风险：读取 `request.json["Plan"]` 的 `try` 发生异常时，代码不会仅返回参数错误，而会构造一份内置的三路口示例 Plan 继续扫描。请求格式错误可能得到一张合法时空图，运维人员无法区分真实方案和演示数据。

## 27.5 子区优化中的证据链

生产输出中的关键字段关系如下：

具体见表 27-1。
表 27-1 子区优化中的证据链
| 阶段 | 代码对象 | 下游证明 |
|---|---|---|
| 有向拓扑 | `link_list` 的 `FromCrossID/ToCrossID/Length` | 旅行时间能否复算 |
| 单点方案 | `StagePlan` | 周期、阶段、绿窗是否闭合 |
| 可协调性 | `CF_table` | 哪些路口应该成组 |
| 时段组 | `st_group_id/cross_group` | 时段与空间边界 |
| MaxBand 解 | `status/Cycle/offset_abs/b/b_bar` | 求解状态和相位差 |
| 时空复核 | `BandUp/BandDown` | 模型结果是否可实现 |

只保存 `offset_abs` 不足以证明方案。没有 `status`，无法区分最优、可行未证明和不可行；没有 `tau` 和速度上下限，无法解释偏移来源；没有 `BandUp/BandDown`，无法证明扫描覆盖。

## 27.6 小结

这一章把教学协调链条落到生产 DataFrame：`link_list` 提供有向拓扑，`subregion_stage_plan_table` 提供每个时段的单点方案，`maxband_input_table` 提供占比空间的窗口和速度，`maxband_output_table` 交出周期、绝对偏移和带宽。证据链的关键不是某一个字段，而是字段之间能不能互相解释——拓扑能不能复算行程时间，单点方案能不能闭合，MaxBand 的状态能不能区分最优与不可行，时空扫描能不能证明结果可实现。

区域协调的生产链路到此走完。第 28 章把镜头转向平台：Java 如何编排一次请求、Flink 如何产出实时指标、下发服务如何把方案送进设备、前端如何把目标、命令和运行事实分开呈现。

## 练习

以下问题同时作为源码实验。

1. 从 `SubAreaOptNew` 的输入构造一个三路口时段，列出生成的每一张 DataFrame 和主键。
2. 修改 `segment_level` 0 至 3，观察协调阈值和时空组数量。
3. 将 `tau` 从默认值改为人工标定值，比较 `offset_abs`。
4. 用给定周期、速度和绿窗手算 MaxBand 输入中的 `r`、`l`、`t` 区间。
5. 构造 `double_cycling` 为真的两路口，解释 `k=10` 和整数环绕约束。
6. 对 `is_timepoint_in_green` 测试 `timepoint=0`、`timepoint=green` 和 `timepoint=cycle-1`。
7. 发送缺少 `Plan` 的 `/gettimespace` 请求，证明当前代码会返回内置示例，并设计正确错误响应。
8. 比较 MaxBand 的 `status` 为 `optimal`、`infeasible` 和空解时的差异，写出验收状态表。

