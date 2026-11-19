"""Teaching metrics for control-plan evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from .demand import degree_of_saturation, lane_capacity_vph
from .model import InvariantViolation


@dataclass(frozen=True)
class MovementEvaluation:
    movement_id: str
    demand_vph: float
    saturation_vph: float
    effective_green_s: float
    cycle_s: int

    @property
    def capacity_vph(self) -> float:
        return lane_capacity_vph(
            self.saturation_vph,
            self.effective_green_s,
            self.cycle_s,
        )

    @property
    def degree_of_saturation(self) -> float:
        return degree_of_saturation(self.demand_vph, self.capacity_vph)


@dataclass(frozen=True)
class SiteEvaluation:
    movements: tuple[MovementEvaluation, ...]

    def validate(self) -> None:
        if not self.movements:
            raise InvariantViolation("evaluation requires at least one movement")

    @property
    def max_degree_of_saturation(self) -> float:
        self.validate()
        return max(item.degree_of_saturation for item in self.movements)

    @property
    def over_capacity_movements(self) -> tuple[str, ...]:
        self.validate()
        return tuple(
            item.movement_id
            for item in self.movements
            if item.degree_of_saturation > 1.0
        )


def flow_weighted_speed(samples: tuple[tuple[float, float], ...]) -> float:
    """Return speed weighted by vehicle flow.

    Each sample is `(flow, speed)`. Flow must be positive enough to carry
    weight; zero-flow detector points do not affect the result.
    """

    if not samples:
        raise InvariantViolation("speed samples must not be empty")
    if any(flow < 0 or speed < 0 for flow, speed in samples):
        raise InvariantViolation("flow and speed must be non-negative")
    total_flow = sum(flow for flow, _ in samples)
    if total_flow <= 0:
        raise InvariantViolation("at least one sample must have positive flow")
    return sum(flow * speed for flow, speed in samples) / total_flow


def difference_in_differences(
    *,
    treatment_before: float,
    treatment_after: float,
    control_before: float,
    control_after: float,
) -> float:
    """Estimate a treatment effect under the parallel-trends assumption."""

    return (treatment_after - treatment_before) - (
        control_after - control_before
    )

