"""Cyclic time arithmetic shared by state, coordination, and review labs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from .model import InvariantViolation, SignalPlan, SignalStage, validate_plan


def normalize_second(second_s: int | float, cycle_s: int) -> int:
    """Map an integer second onto ``[0, cycle_s)``.

    The manuscript uses integer-second scans for reproducible examples. The
    function rejects fractional seconds rather than rounding without the
    caller's knowledge.
    """

    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    if int(second_s) != second_s:
        raise InvariantViolation("second must be an integer")
    return int(second_s) % cycle_s


@dataclass(frozen=True)
class CircularInterval:
    """A half-open green interval that may wrap across the cycle boundary."""

    start_s: int
    duration_s: int
    cycle_s: int

    def __post_init__(self) -> None:
        if self.cycle_s <= 0:
            raise InvariantViolation("cycle must be positive")
        if not 0 <= self.start_s < self.cycle_s:
            raise InvariantViolation("interval start must be in the cycle")
        if not 0 <= self.duration_s <= self.cycle_s:
            raise InvariantViolation("interval duration must be within the cycle")

    @property
    def end_s(self) -> int:
        return normalize_second(self.start_s + self.duration_s, self.cycle_s)

    @property
    def wraps(self) -> bool:
        return self.start_s + self.duration_s > self.cycle_s

    def contains(self, second_s: int | float) -> bool:
        point = normalize_second(second_s, self.cycle_s)
        if self.duration_s == self.cycle_s:
            return True
        if not self.wraps:
            return self.start_s <= point < self.start_s + self.duration_s
        return point >= self.start_s or point < self.end_s

    def intersection(self, other: "CircularInterval") -> int:
        """Return the number of seconds in the circular intersection."""

        if self.cycle_s != other.cycle_s:
            raise InvariantViolation("intervals must use the same cycle")
        return sum(
            self.contains(second) and other.contains(second)
            for second in range(self.cycle_s)
        )

    def complement_duration_s(self) -> int:
        return self.cycle_s - self.duration_s


@dataclass(frozen=True)
class StageWindow:
    stage_id: str
    start_s: int
    duration_s: int
    green_s: int
    clearance_s: int

    def __post_init__(self) -> None:
        if not self.stage_id:
            raise InvariantViolation("stage_id must not be empty")
        if self.start_s < 0 or self.duration_s <= 0:
            raise InvariantViolation("stage window has invalid time bounds")
        if not 0 <= self.green_s <= self.duration_s:
            raise InvariantViolation("green must be within stage duration")
        if self.clearance_s != self.duration_s - self.green_s:
            raise InvariantViolation("clearance must equal stage duration minus green")


def stage_windows(plan: SignalPlan) -> tuple[StageWindow, ...]:
    """Return cumulative stage windows starting at cycle time zero."""

    validate_plan(plan)
    result: list[StageWindow] = []
    start = 0
    for stage in plan.stages:
        result.append(
            StageWindow(
                stage_id=stage.stage_id,
                start_s=start,
                duration_s=stage.duration,
                green_s=stage.green,
                clearance_s=stage.green_flash + stage.yellow + stage.all_red,
            )
        )
        start += stage.duration
    return tuple(result)


def stage_at(plan: SignalPlan, elapsed_s: int | float) -> StageWindow:
    """Return the stage present at a local cycle second."""

    point = normalize_second(elapsed_s, plan.cycle)
    for window in stage_windows(plan):
        if window.start_s <= point < window.start_s + window.duration_s:
            return window
    raise AssertionError("validated plan left a hole in its cycle")


def green_at(
    plan: SignalPlan,
    elapsed_s: int | float,
    *,
    offset_s: int = 0,
) -> bool:
    """Return whether the displayed green portion is active at a time."""

    local_second = normalize_second(elapsed_s - offset_s, plan.cycle)
    window = stage_at(plan, local_second)
    return local_second < window.start_s + window.green_s


def iter_stage_seconds(plan: SignalPlan) -> Iterator[tuple[int, StageWindow]]:
    """Yield one `(local_second, window)` pair per second of a cycle."""

    windows = stage_windows(plan)
    for second in range(plan.cycle):
        for window in windows:
            if window.start_s <= second < window.start_s + window.duration_s:
                yield second, window
                break


def apply_offsets(
    plan: SignalPlan,
    offset_s: int,
) -> tuple[StageWindow, ...]:
    """Shift all windows by an offset and normalize starts into the cycle."""

    shifted = []
    for window in stage_windows(plan):
        shifted.append(
            StageWindow(
                stage_id=window.stage_id,
                start_s=normalize_second(window.start_s + offset_s, plan.cycle),
                duration_s=window.duration_s,
                green_s=window.green_s,
                clearance_s=window.clearance_s,
            )
        )
    return tuple(shifted)
