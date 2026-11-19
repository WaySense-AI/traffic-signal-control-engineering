"""Traffic demand measures used by the signal timing labs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .model import InvariantViolation


@dataclass(frozen=True)
class MovementDemand:
    movement_id: str
    volume_vph: float
    saturation_vph: float

    @property
    def flow_ratio(self) -> float:
        if self.saturation_vph <= 0:
            raise InvariantViolation(
                f"{self.movement_id}: saturation flow must be positive"
            )
        if self.volume_vph < 0:
            raise InvariantViolation(
                f"{self.movement_id}: traffic volume must be non-negative"
            )
        return self.volume_vph / self.saturation_vph


def critical_flow_ratio(movements: Iterable[MovementDemand]) -> float:
    ratios = [movement.flow_ratio for movement in movements]
    return max(ratios, default=0.0)


def stage_flow_ratios(
    stage_movements: Mapping[str, Iterable[str]],
    movement_demands: Mapping[str, MovementDemand],
) -> dict[str, float]:
    """Return the maximum flow ratio for each stage.

    A stage can serve several compatible movements. Its time requirement is
    governed by the most demanding critical movement in the stage.
    """

    result: dict[str, float] = {}
    for stage_id, movement_ids in stage_movements.items():
        movements = []
        for movement_id in movement_ids:
            if movement_id not in movement_demands:
                raise InvariantViolation(
                    f"{stage_id}: missing demand for movement {movement_id}"
                )
            movements.append(movement_demands[movement_id])
        result[stage_id] = critical_flow_ratio(movements)
    return result


def lane_capacity_vph(
    saturation_vph: float,
    effective_green_s: float,
    cycle_s: int,
) -> float:
    """Return average capacity over a complete cycle."""

    if saturation_vph <= 0:
        raise InvariantViolation("saturation flow must be positive")
    if effective_green_s < 0:
        raise InvariantViolation("effective green must be non-negative")
    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    if effective_green_s > cycle_s:
        raise InvariantViolation("effective green cannot exceed cycle")
    return saturation_vph * effective_green_s / cycle_s


def degree_of_saturation(demand_vph: float, capacity_vph: float) -> float:
    if demand_vph < 0:
        raise InvariantViolation("demand must be non-negative")
    if capacity_vph <= 0:
        raise InvariantViolation("capacity must be positive")
    return demand_vph / capacity_vph

