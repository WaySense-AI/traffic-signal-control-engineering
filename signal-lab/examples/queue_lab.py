"""Trace queue growth, service, and spillback one cycle at a time."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import queue_clearance_cycles, simulate_queue


def run_lab() -> dict[str, object]:
    fixed_plan = simulate_queue(
        [600, 750, 900, 900, 750, 600],
        cycle_s=90,
        effective_green_s=27,
        saturation_vph=1800,
        initial_queue_veh=4,
    )
    bounded = simulate_queue(
        [600, 750, 900, 900, 750, 600],
        cycle_s=90,
        effective_green_s=27,
        saturation_vph=1800,
        initial_queue_veh=4,
        storage_capacity_veh=20,
    )
    return {
        "service_veh_per_cycle": fixed_plan[0].service_veh,
        "capacity_vph": fixed_plan[0].capacity_vph,
        "fixed_plan": [
            {
                "cycle": step.cycle_index,
                "demand_vph": step.demand_vph,
                "arrivals_veh": round(step.arrivals_veh, 2),
                "start_queue_veh": round(step.start_queue_veh, 2),
                "served_veh": round(step.served_veh, 2),
                "end_queue_veh": round(step.end_queue_veh, 2),
                "degree_of_saturation": round(step.degree_of_saturation, 3),
            }
            for step in fixed_plan
        ],
        "fixed_plan_clearance_cycles": queue_clearance_cycles(fixed_plan),
        "storage_capacity_veh": 20,
        "bounded_end_queue_veh": round(bounded[-1].end_queue_veh, 2),
        "cumulative_spillback_veh": round(
            sum(step.overflow_veh for step in bounded),
            2,
        ),
    }


def main() -> None:
    print(json.dumps(run_lab(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
