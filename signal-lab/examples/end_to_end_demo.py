"""Run a small end-to-end timing and coordination example."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import (
    CommandEvent,
    ControlCommand,
    CorridorSegment,
    LaneObservation,
    MovementDemand,
    PiecewiseLinearCycleModel,
    SignalStage,
    allocate_green_by_ratio,
    aggregate_lane_movements,
    common_cycle_s,
    downstream_offset_s,
    stage_flow_ratios,
    validate_plan,
)


def build_demo_result() -> dict:
    lane_flows = aggregate_lane_movements(
        [
            LaneObservation("E1", "east", "straight", 600),
            LaneObservation("E2", "east", "straight_left", 400),
            LaneObservation("W1", "west", "straight", 500),
            LaneObservation("N1", "north", "left", 220),
        ]
    )

    demands = {
        "east-through": MovementDemand("east-through", lane_flows[("east", "straight")].volume_vph, 1600),
        "east-left": MovementDemand("east-left", lane_flows[("east", "left")].volume_vph, 1450),
        "west-through": MovementDemand("west-through", lane_flows[("west", "straight")].volume_vph, 1600),
        "north-left": MovementDemand("north-left", lane_flows[("north", "left")].volume_vph, 1450),
    }
    ratios = stage_flow_ratios(
        {
            "A": ("east-through", "east-left"),
            "B": ("west-through",),
            "C": ("north-left",),
        },
        demands,
    )

    cycle_model = PiecewiseLinearCycleModel(((0.3, 70), (0.6, 95), (0.9, 150)))
    cycle = cycle_model.predict(sum(ratios.values()))
    stages = tuple(
        SignalStage(
            stage_id=stage_id,
            green=12,
            green_flash=3,
            yellow=3,
            all_red=2,
            min_green=12,
            phase_ids=(f"phase-{stage_id}",),
        )
        for stage_id in ("A", "B", "C")
    )
    plan = allocate_green_by_ratio(stages, ratios, cycle)
    validate_plan(plan)

    common_cycle = common_cycle_s((cycle, cycle), even=True)
    segment = CorridorSegment("S1", "S2", length_m=240, speed_kmh=36)
    offset_s2 = downstream_offset_s(0, segment, common_cycle)

    command = ControlCommand(
        command_id="demo-command",
        batch_id="demo-batch",
        site_id="S1",
        plan_version="demo-v1",
        requested_at_s=0,
    )
    command = command.apply(CommandEvent.ACCEPT)
    command = command.apply(CommandEvent.DISPATCH)
    command = command.apply(CommandEvent.OBSERVE)

    return {
        "cycle": cycle,
        "stage_flow_ratios": ratios,
        "stage_green_s": {
            item.stage_id: item.green for item in plan.stages
        },
        "common_cycle": common_cycle,
        "downstream_offset_s": offset_s2,
        "command_status": command.status.value,
    }


def main() -> None:
    print(
        json.dumps(
            build_demo_result(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
