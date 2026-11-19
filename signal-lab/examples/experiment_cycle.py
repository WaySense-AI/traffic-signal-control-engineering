"""Compare cycle models and green allocation for a demand sweep."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import (
    PiecewiseLinearCycleModel,
    SignalStage,
    allocate_green_by_ratio,
    webster_cycle,
)


def main() -> None:
    model = PiecewiseLinearCycleModel(((0.3, 70), (0.6, 95), (0.9, 150)))
    stages = tuple(
        SignalStage(
            stage_id=stage_id,
            green=10,
            green_flash=3,
            yellow=3,
            all_red=2,
            min_green=10,
            phase_ids=(f"phase-{stage_id}",),
        )
        for stage_id in ("A", "B", "C")
    )

    print("demand  model_cycle  webster_cycle  green_seconds")
    for demand in (0.3, 0.45, 0.6, 0.75, 0.9):
        ratios = {"A": demand * 0.5, "B": demand * 0.3, "C": demand * 0.2}
        cycle = model.predict(demand)
        webster = webster_cycle(ratios, lost_time_s=24)
        plan = allocate_green_by_ratio(stages, ratios, cycle)
        greens = ",".join(str(stage.green) for stage in plan.stages)
        print(f"{demand:>6.2f}  {cycle:>11d}  {webster.bounded_cycle_s:>13d}  {greens}")


if __name__ == "__main__":
    main()

