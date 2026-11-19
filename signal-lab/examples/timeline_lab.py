"""Inspect half-open stages, cyclic green windows, and offset semantics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import (
    CircularInterval,
    SignalPlan,
    SignalStage,
    green_at,
    iter_stage_seconds,
    stage_windows,
)


def s2_plan() -> SignalPlan:
    return SignalPlan(
        site_id="S2",
        cycle=150,
        stages=(
            SignalStage("A", 59, 3, 3, 2, 12, ("phase-A",)),
            SignalStage("B", 41, 3, 3, 2, 12, ("phase-B",)),
            SignalStage("C", 26, 3, 3, 2, 12, ("phase-C",)),
        ),
    )


def run_lab() -> dict[str, object]:
    plan = s2_plan()
    windows = stage_windows(plan)
    green = CircularInterval(26, 59, plan.cycle)
    return {
        "stage_windows": [
            {
                "stage": item.stage_id,
                "start_s": item.start_s,
                "duration_s": item.duration_s,
                "green_s": item.green_s,
                "clearance_s": item.clearance_s,
            }
            for item in windows
        ],
        "green_seconds_counted": sum(
            green_at(plan, second) for second, _ in iter_stage_seconds(plan)
        ),
        "wrapped_green": {
            "start_s": green.start_s,
            "duration_s": green.duration_s,
            "end_s": green.end_s,
            "contains_26": green.contains(26),
            "contains_84": green.contains(84),
            "contains_85": green.contains(85),
            "contains_25": green.contains(25),
        },
    }


def main() -> None:
    print(json.dumps(run_lab(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
