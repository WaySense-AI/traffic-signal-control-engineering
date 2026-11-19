"""Event-time window aggregation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .model import InvariantViolation


@dataclass(frozen=True)
class CountEvent:
    event_id: str
    event_at_s: int
    count: int

    def __post_init__(self) -> None:
        if not self.event_id:
            raise InvariantViolation("event_id must not be empty")
        if self.count < 0:
            raise InvariantViolation("event count must be non-negative")


@dataclass(frozen=True)
class WindowAggregate:
    window_start_s: int
    window_end_s: int
    count: int
    volume_vph: float


def aggregate_count_windows(
    events: Iterable[CountEvent],
    *,
    origin_s: int,
    window_s: int,
    window_count: int,
) -> tuple[WindowAggregate, ...]:
    """Aggregate events into half-open [start, end) windows.

    Duplicate event IDs are rejected rather than double-counted. Events outside
    the requested range are ignored so callers can pass a larger replay batch.
    """

    if window_s <= 0:
        raise InvariantViolation("window_s must be positive")
    if window_count <= 0:
        raise InvariantViolation("window_count must be positive")

    totals = [0] * window_count
    seen: set[str] = set()
    end_s = origin_s + window_s * window_count
    for event in events:
        if event.event_id in seen:
            raise InvariantViolation(f"duplicate event: {event.event_id}")
        seen.add(event.event_id)
        if event.event_at_s < origin_s or event.event_at_s >= end_s:
            continue
        index = (event.event_at_s - origin_s) // window_s
        totals[index] += event.count

    return tuple(
        WindowAggregate(
            window_start_s=origin_s + index * window_s,
            window_end_s=origin_s + (index + 1) * window_s,
            count=count,
            volume_vph=count * 3600.0 / window_s,
        )
        for index, count in enumerate(totals)
    )
