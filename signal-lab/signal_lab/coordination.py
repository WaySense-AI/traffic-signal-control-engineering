"""Basic subarea timing, offsets, and time-space band calculation."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable, Sequence

from .model import InvariantViolation


@dataclass(frozen=True)
class CorridorSegment:
    from_site_id: str
    to_site_id: str
    length_m: float
    speed_kmh: float

    def __post_init__(self) -> None:
        if not self.from_site_id or not self.to_site_id:
            raise InvariantViolation("segment endpoint IDs must not be empty")
        if self.from_site_id == self.to_site_id:
            raise InvariantViolation("segment endpoints must differ")
        if self.length_m <= 0:
            raise InvariantViolation("segment length must be positive")
        if self.speed_kmh <= 0:
            raise InvariantViolation("coordination speed must be positive")

    @property
    def travel_time_s(self) -> float:
        speed_mps = self.speed_kmh / 3.6
        return self.length_m / speed_mps


def common_cycle_s(cycles: Iterable[int], *, even: bool = False) -> int:
    values = tuple(cycles)
    if not values or any(cycle <= 0 for cycle in values):
        raise InvariantViolation("common cycle requires positive cycles")
    cycle = max(values)
    if even and cycle % 2:
        cycle += 1
    return cycle


def downstream_offset_s(
    upstream_offset_s: int,
    segment: CorridorSegment,
    cycle_s: int,
) -> int:
    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    return round(upstream_offset_s + segment.travel_time_s) % cycle_s


def cumulative_travel_times_s(
    lengths_m: Sequence[float],
    speeds_kmh: Sequence[float],
) -> tuple[float, ...]:
    """Return travel times from the first intersection, including time zero."""

    if len(lengths_m) != len(speeds_kmh):
        raise InvariantViolation("length and speed arrays must have equal size")
    if any(length <= 0 for length in lengths_m):
        raise InvariantViolation("segment lengths must be positive")
    if any(speed <= 0 for speed in speeds_kmh):
        raise InvariantViolation("segment speeds must be positive")
    cumulative = [0.0]
    for length, speed in zip(lengths_m, speeds_kmh):
        cumulative.append(cumulative[-1] + length / (speed / 3.6))
    return tuple(cumulative)


def green_band_width_s(
    *,
    cycle_s: int,
    offsets_s: Sequence[int],
    travel_times_s: Sequence[float],
    green_duration_s: Sequence[int],
) -> int:
    """Measure the longest common green arrival interval in integer seconds.

    `travel_times_s[i]` is the cumulative travel time from the reference
    departure point to intersection `i`. The offset convention is that a green
    starts at `offset_s mod cycle_s`.
    """

    size = len(offsets_s)
    if size == 0:
        raise InvariantViolation("band requires at least one intersection")
    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    if not (len(travel_times_s) == len(green_duration_s) == size):
        raise InvariantViolation("band inputs must have equal lengths")
    if any(value < 0 for value in travel_times_s):
        raise InvariantViolation("travel times must be non-negative")
    if any(value < 0 or value > cycle_s for value in green_duration_s):
        raise InvariantViolation("green durations must be within the cycle")

    passing = []
    for departure_s in range(cycle_s):
        ok = True
        for offset, travel, green in zip(offsets_s, travel_times_s, green_duration_s):
            phase = (departure_s + travel - offset) % cycle_s
            if phase >= green:
                ok = False
                break
        passing.append(ok)

    longest = current = 0
    for _ in range(2):
        for ok in passing:
            current = current + 1 if ok else 0
            longest = max(longest, min(current, cycle_s))
    return longest


def green_band_width_sweep_s(
    *,
    cycle_s: int,
    offsets_s: Sequence[int],
    travel_times_s: Sequence[float],
    green_duration_s: Sequence[int],
) -> int:
    """Measure the same integer departure window with an endpoint sweep.

    For one intersection, a departure second ``k`` passes when

        (k + travel - offset) mod cycle < green.

    The allowed departures therefore form one circular integer interval.
    Splitting wrapped intervals at the cycle boundary and sweeping their start
    and end events returns the longest interval covered by every intersection
    in O(N log N), instead of testing every second in every intersection.
    """

    size = len(offsets_s)
    if size == 0:
        raise InvariantViolation("band requires at least one intersection")
    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    if not (len(travel_times_s) == len(green_duration_s) == size):
        raise InvariantViolation("band inputs must have equal lengths")
    if any(value < 0 for value in travel_times_s):
        raise InvariantViolation("travel times must be non-negative")
    if any(value < 0 or value > cycle_s for value in green_duration_s):
        raise InvariantViolation("green durations must be within the cycle")
    if any(green == 0 for green in green_duration_s):
        return 0

    events: dict[int, int] = {0: 0, cycle_s: 0}
    for offset, travel, green in zip(
        offsets_s,
        travel_times_s,
        green_duration_s,
    ):
        start_real = (offset - travel) % cycle_s
        start = ceil(start_real - 1e-12) % cycle_s
        end = start + green
        if end <= cycle_s:
            events[start] = events.get(start, 0) + 1
            events[end] = events.get(end, 0) - 1
        else:
            events[start] = events.get(start, 0) + 1
            events[cycle_s] = events.get(cycle_s, 0) - 1
            events[0] = events.get(0, 0) + 1
            events[end - cycle_s] = events.get(end - cycle_s, 0) - 1

    points = sorted(events)
    active = events[points[0]]
    previous = points[0]
    covered: list[tuple[int, int]] = []
    for point in points[1:]:
        if active == size:
            covered.append((previous, point))
        active += events[point]
        previous = point
    if not covered:
        return 0
    longest = max(end - start for start, end in covered)
    if covered[0][0] == 0 and covered[-1][1] == cycle_s:
        longest = max(
            longest,
            covered[-1][1] - covered[-1][0]
            + covered[0][1] - covered[0][0],
        )
    return longest

