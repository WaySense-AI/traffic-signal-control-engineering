"""Core time model used throughout the book labs.

All durations are integer seconds. A stage duration includes green, green
flash, yellow, and all-red. The model deliberately keeps those components
visible so later optimization code cannot silently discard clearance time.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable


class InvariantViolation(ValueError):
    """Raised when a signal plan violates a hard correctness constraint."""


@dataclass(frozen=True)
class SignalStage:
    stage_id: str
    green: int
    green_flash: int
    yellow: int
    all_red: int
    min_green: int
    phase_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.stage_id:
            raise InvariantViolation("stage_id must not be empty")
        if not self.phase_ids:
            raise InvariantViolation(f"{self.stage_id}: at least one phase is required")
        for name in ("green", "green_flash", "yellow", "all_red", "min_green"):
            value = getattr(self, name)
            if value < 0:
                raise InvariantViolation(f"{self.stage_id}: {name} must be non-negative")

    @property
    def duration(self) -> int:
        return self.green + self.green_flash + self.yellow + self.all_red

    def validate_min_green(self) -> None:
        if self.green < self.min_green:
            raise InvariantViolation(
                f"{self.stage_id}: green {self.green}s is below minimum {self.min_green}s"
            )

    def with_green(self, green: int) -> "SignalStage":
        if green < 0:
            raise InvariantViolation("green must be non-negative")
        return replace(self, green=green)


@dataclass(frozen=True)
class SignalPlan:
    site_id: str
    cycle: int
    stages: tuple[SignalStage, ...]

    def __post_init__(self) -> None:
        if not self.site_id:
            raise InvariantViolation("site_id must not be empty")
        if self.cycle <= 0:
            raise InvariantViolation("cycle must be positive")
        if not self.stages:
            raise InvariantViolation("a plan requires at least one stage")
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise InvariantViolation("stage_id values must be unique within a plan")


def validate_plan(plan: SignalPlan) -> None:
    """Validate cycle consistency and all stage-level hard constraints."""

    for stage in plan.stages:
        stage.validate_min_green()
    total = sum(stage.duration for stage in plan.stages)
    if total != plan.cycle:
        raise InvariantViolation(
            f"stage durations sum to {total}s, but cycle is {plan.cycle}s"
        )


def repair_min_green(plan: SignalPlan) -> SignalPlan:
    """Raise deficient stages and remove the added time from donor stages.

    The repair is deterministic. Deficits are funded proportionally from the
    green time above minimum in stages that have spare green. Clearance
    intervals are never changed.
    """

    deficits = {
        index: max(0, stage.min_green - stage.green)
        for index, stage in enumerate(plan.stages)
    }
    total_deficit = sum(deficits.values())
    if total_deficit == 0:
        return plan

    spare = {
        index: stage.green - stage.min_green
        for index, stage in enumerate(plan.stages)
        if stage.green > stage.min_green
    }
    total_spare = sum(spare.values())
    if total_spare < total_deficit:
        raise InvariantViolation(
            f"cannot repair minimum green: deficit={total_deficit}s, spare={total_spare}s"
        )

    greens = {index: stage.green for index, stage in enumerate(plan.stages)}
    for index, deficit in deficits.items():
        greens[index] += deficit

    remaining = total_deficit
    donors = sorted(spare)
    for offset, index in enumerate(donors):
        if offset == len(donors) - 1:
            reduction = remaining
        else:
            reduction = total_deficit * spare[index] // total_spare
            reduction = min(reduction, spare[index], remaining)
        greens[index] -= reduction
        remaining -= reduction

    if remaining:
        raise InvariantViolation("minimum green repair failed to allocate deficit")

    repaired = replace(
        plan,
        stages=tuple(
            stage.with_green(greens[index])
            for index, stage in enumerate(plan.stages)
        ),
    )
    validate_plan(repaired)
    return repaired


def total_green(plan: SignalPlan) -> int:
    return sum(stage.green for stage in plan.stages)


def total_clearance(plan: SignalPlan) -> int:
    return sum(
        stage.green_flash + stage.yellow + stage.all_red
        for stage in plan.stages
    )


def plan_from_stages(site_id: str, cycle: int, stages: Iterable[SignalStage]) -> SignalPlan:
    return SignalPlan(site_id=site_id, cycle=cycle, stages=tuple(stages))

