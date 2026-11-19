"""Right-of-way and conflict validation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Mapping

from .model import InvariantViolation
from .model import SignalPlan


MovementKey = tuple[str, str]


@dataclass(frozen=True)
class PhaseRightOfWay:
    phase_id: str
    movements: frozenset[MovementKey]

    def __post_init__(self) -> None:
        if not self.phase_id:
            raise InvariantViolation("phase_id must not be empty")
        if not self.movements:
            raise InvariantViolation(f"{self.phase_id}: movements must not be empty")


@dataclass(frozen=True)
class ConflictMatrix:
    conflicts: frozenset[frozenset[MovementKey]]

    @classmethod
    def from_pairs(
        cls, pairs: Iterable[tuple[MovementKey, MovementKey]]
    ) -> "ConflictMatrix":
        normalized: set[frozenset[MovementKey]] = set()
        for first, second in pairs:
            if first == second:
                raise InvariantViolation("a movement cannot conflict with itself")
            normalized.add(frozenset((first, second)))
        return cls(frozenset(normalized))

    def are_conflicting(self, first: MovementKey, second: MovementKey) -> bool:
        return frozenset((first, second)) in self.conflicts

    def validate_movement_set(self, movements: Iterable[MovementKey]) -> None:
        movement_set = frozenset(movements)
        for first, second in combinations(sorted(movement_set), 2):
            if self.are_conflicting(first, second):
                raise InvariantViolation(
                    f"conflicting movements share green: {first} and {second}"
                )


def validate_stage_phases(
    stage_id: str,
    phase_ids: Iterable[str],
    phases: Mapping[str, PhaseRightOfWay],
    conflicts: ConflictMatrix,
) -> None:
    movements: set[MovementKey] = set()
    for phase_id in phase_ids:
        if phase_id not in phases:
            raise InvariantViolation(f"{stage_id}: unknown phase {phase_id}")
        phase = phases[phase_id]
        conflicts.validate_movement_set(phase.movements)
        movements.update(phase.movements)
    conflicts.validate_movement_set(movements)


def same_stage_sequence(first: SignalPlan, second: SignalPlan) -> bool:
    """Return whether two plans use the same ordered stage identifiers."""

    return tuple(stage.stage_id for stage in first.stages) == tuple(
        stage.stage_id for stage in second.stages
    )

