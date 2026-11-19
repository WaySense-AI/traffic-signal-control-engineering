"""Cycle-model and green-allocation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Mapping

from .model import InvariantViolation, SignalPlan, SignalStage, validate_plan


@dataclass(frozen=True)
class PiecewiseLinearCycleModel:
    """A transparent cycle model fitted to selected demand/cycle labels."""

    labels: tuple[tuple[float, int], ...]

    def __post_init__(self) -> None:
        if len(self.labels) < 2:
            raise InvariantViolation("cycle model requires at least two labels")
        ordered = sorted(self.labels)
        if len({x for x, _ in ordered}) != len(ordered):
            raise InvariantViolation("cycle label demand values must be unique")
        if any(x < 0 for x, _ in ordered):
            raise InvariantViolation("cycle label demand must be non-negative")
        if any(y <= 0 for _, y in ordered):
            raise InvariantViolation("cycle label duration must be positive")
        object.__setattr__(self, "labels", tuple(ordered))

    def predict(self, critical_ratio_sum: float) -> int:
        if critical_ratio_sum < 0:
            raise InvariantViolation("critical ratio sum must be non-negative")
        x_values = [x for x, _ in self.labels]
        y_values = [y for _, y in self.labels]
        if critical_ratio_sum <= x_values[0]:
            return y_values[0]
        if critical_ratio_sum >= x_values[-1]:
            return y_values[-1]

        for index in range(len(self.labels) - 1):
            x0, y0 = self.labels[index]
            x1, y1 = self.labels[index + 1]
            if x0 <= critical_ratio_sum <= x1:
                ratio = (critical_ratio_sum - x0) / (x1 - x0)
                return round(y0 + ratio * (y1 - y0))
        raise AssertionError("unreachable cycle interpolation branch")


def allocate_green_by_ratio(
    stages: tuple[SignalStage, ...],
    stage_ratios: Mapping[str, float],
    cycle: int,
) -> SignalPlan:
    """Allocate available green by critical flow ratio.

    Clearance intervals are fixed. Every stage first receives its minimum
    green. Remaining green is allocated with the largest-remainder method so
    the integer stage durations always sum to the available green.
    """

    if cycle <= 0:
        raise InvariantViolation("cycle must be positive")
    unknown = set(stage_ratios) - {stage.stage_id for stage in stages}
    if unknown:
        raise InvariantViolation(f"ratios reference unknown stages: {sorted(unknown)}")
    if any(value < 0 for value in stage_ratios.values()):
        raise InvariantViolation("stage flow ratios must be non-negative")

    clearance = sum(
        stage.green_flash + stage.yellow + stage.all_red for stage in stages
    )
    available_green = cycle - clearance
    minimum_total = sum(stage.min_green for stage in stages)
    if available_green < minimum_total:
        raise InvariantViolation(
            f"cycle {cycle}s leaves {available_green}s for green, "
            f"but minimum green requires {minimum_total}s"
        )

    extra = available_green - minimum_total
    weights = {
        stage.stage_id: stage_ratios.get(stage.stage_id, 0.0) for stage in stages
    }
    total_weight = sum(weights.values())
    if total_weight == 0:
        weights = {stage.stage_id: 1.0 for stage in stages}
        total_weight = float(len(stages))

    raw_extra = {
        stage_id: extra * weight / total_weight
        for stage_id, weight in weights.items()
    }
    allocated = {
        stage_id: floor(value) for stage_id, value in raw_extra.items()
    }
    remaining = extra - sum(allocated.values())
    ranked = sorted(
        raw_extra,
        key=lambda stage_id: (
            -(raw_extra[stage_id] - allocated[stage_id]),
            stage_id,
        ),
    )
    for stage_id in ranked[:remaining]:
        allocated[stage_id] += 1

    result = SignalPlan(
        site_id="allocation-input",
        cycle=cycle,
        stages=tuple(
            stage.with_green(stage.min_green + allocated[stage.stage_id])
            for stage in stages
        ),
    )
    validate_plan(result)
    return result

