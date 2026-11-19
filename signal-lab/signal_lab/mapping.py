"""Lane observation mapping and provenance-aware aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable, Mapping

from .model import InvariantViolation
from .safety import MovementKey


STANDARD_MOVEMENT_SHARES: Mapping[str, tuple[tuple[str, float], ...]] = {
    "straight": (("straight", 1.0),),
    "left": (("left", 1.0),),
    "right": (("right", 1.0),),
    "straight_left": (("straight", 0.5), ("left", 0.5)),
    "straight_right": (("straight", 0.5), ("right", 0.5)),
    "left_right": (("left", 0.5), ("right", 0.5)),
    "left_straight_right": (
        ("straight", 1.0 / 3.0),
        ("left", 1.0 / 3.0),
        ("right", 1.0 / 3.0),
    ),
}


@dataclass(frozen=True)
class LaneObservation:
    lane_id: str
    direction: str
    movement: str
    volume_vph: int | None
    estimated: bool = False
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.lane_id:
            raise InvariantViolation("lane_id must not be empty")
        if self.movement not in STANDARD_MOVEMENT_SHARES:
            raise InvariantViolation(f"unsupported lane movement: {self.movement}")
        if self.volume_vph is not None and self.volume_vph < 0:
            raise InvariantViolation("traffic volume must be non-negative or None")
        if not 0.0 <= self.confidence <= 1.0:
            raise InvariantViolation("confidence must be between 0 and 1")
        if self.volume_vph is None and self.confidence != 0.0:
            raise InvariantViolation("missing volume must have zero confidence")


@dataclass(frozen=True)
class FlowAggregate:
    volume_vph: float | None
    estimated: bool
    confidence: float
    missing_inputs: int


def aggregate_lane_movements(
    observations: Iterable[LaneObservation],
) -> dict[MovementKey, FlowAggregate]:
    """Split shared-lane volume equally among its allowed movements.

    Production code applies additional lane-count scaling. This lab keeps the
    mapping primitive explicit and leaves topology-based scaling to the flow
    completion chapter.
    """

    totals: defaultdict[MovementKey, float] = defaultdict(float)
    missing: defaultdict[MovementKey, int] = defaultdict(int)
    estimated: defaultdict[MovementKey, bool] = defaultdict(bool)
    confidence: defaultdict[MovementKey, float] = defaultdict(lambda: 1.0)

    seen_lanes: set[str] = set()
    for observation in observations:
        if observation.lane_id in seen_lanes:
            raise InvariantViolation(f"duplicate lane observation: {observation.lane_id}")
        seen_lanes.add(observation.lane_id)
        for movement, share in STANDARD_MOVEMENT_SHARES[observation.movement]:
            key = (observation.direction, movement)
            estimated[key] = estimated[key] or observation.estimated
            confidence[key] = min(confidence[key], observation.confidence)
            if observation.volume_vph is None:
                missing[key] += 1
            else:
                totals[key] += observation.volume_vph * share

    keys = set(totals) | set(missing)
    result: dict[MovementKey, FlowAggregate] = {}
    for key in sorted(keys):
        missing_count = missing[key]
        result[key] = FlowAggregate(
            volume_vph=totals[key] if missing_count == 0 else None,
            estimated=estimated[key],
            confidence=confidence[key] if missing_count == 0 else 0.0,
            missing_inputs=missing_count,
        )
    return result

