"""Deterministic cycle-level queue dynamics for the book labs.

The model is intentionally small. It isolates the conservation law that
connects demand, signal service, storage capacity, and spillback. It is not a
car-following simulator and does not claim to predict field delay.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

from .demand import degree_of_saturation, lane_capacity_vph
from .model import InvariantViolation


@dataclass(frozen=True)
class QueueStep:
    """State transition for one signal cycle at one approach."""

    cycle_index: int
    demand_vph: float
    capacity_vph: float
    cycle_s: int
    effective_green_s: float
    start_queue_veh: float
    arrivals_veh: float
    service_veh: float
    served_veh: float
    end_queue_veh: float
    overflow_veh: float

    @property
    def degree_of_saturation(self) -> float:
        return degree_of_saturation(self.demand_vph, self.capacity_vph)

    @property
    def unserved_veh(self) -> float:
        return self.start_queue_veh + self.arrivals_veh - self.served_veh


def simulate_queue(
    demands_vph: Iterable[float],
    *,
    cycle_s: int,
    effective_green_s: float,
    saturation_vph: float,
    initial_queue_veh: float = 0.0,
    storage_capacity_veh: float | None = None,
) -> tuple[QueueStep, ...]:
    """Simulate a finite sequence of cycles using conservation of vehicles.

    During cycle ``k``, the approach receives ``q C / 3600`` vehicle arrivals
    and can serve at most ``s g_e / 3600`` vehicles, where ``g_e`` is effective
    green. The queue at the end of the cycle is what remains after service.

    ``storage_capacity_veh`` is the number of queued vehicles the approach can
    hold. When the post-service queue exceeds it, the excess is reported as
    spillback and the locally stored queue is capped at the physical limit.
    Spillback affects the upstream approach; this single-approach model does
    not attempt to propagate that effect.
    """

    demands = tuple(float(value) for value in demands_vph)
    if not demands:
        raise InvariantViolation("queue simulation requires at least one cycle")
    if cycle_s <= 0:
        raise InvariantViolation("cycle must be positive")
    if not 0 <= effective_green_s <= cycle_s:
        raise InvariantViolation("effective green must be within the cycle")
    if saturation_vph <= 0:
        raise InvariantViolation("saturation flow must be positive")
    if initial_queue_veh < 0:
        raise InvariantViolation("initial queue must be non-negative")
    if storage_capacity_veh is not None and storage_capacity_veh <= 0:
        raise InvariantViolation("storage capacity must be positive when supplied")
    for value in (initial_queue_veh, saturation_vph, *demands):
        if not isfinite(value):
            raise InvariantViolation("queue inputs must be finite")
    if any(value < 0 for value in demands):
        raise InvariantViolation("demand must be non-negative")

    capacity_vph = lane_capacity_vph(
        saturation_vph,
        effective_green_s,
        cycle_s,
    )
    service_per_cycle = saturation_vph * effective_green_s / 3600
    queue = float(initial_queue_veh)
    result: list[QueueStep] = []

    for cycle_index, demand_vph in enumerate(demands):
        arrivals = demand_vph * cycle_s / 3600
        available = queue + arrivals
        served = min(available, service_per_cycle)
        residual = available - served
        overflow = 0.0
        if storage_capacity_veh is not None and residual > storage_capacity_veh:
            overflow = residual - storage_capacity_veh
            residual = storage_capacity_veh

        result.append(
            QueueStep(
                cycle_index=cycle_index,
                demand_vph=demand_vph,
                capacity_vph=capacity_vph,
                cycle_s=cycle_s,
                effective_green_s=effective_green_s,
                start_queue_veh=queue,
                arrivals_veh=arrivals,
                service_veh=service_per_cycle,
                served_veh=served,
                end_queue_veh=residual,
                overflow_veh=overflow,
            )
        )
        queue = residual

    return tuple(result)


def queue_clearance_cycles(
    states: Iterable[QueueStep],
) -> int | None:
    """Return how many complete cycles are needed to reach an empty queue.

    ``None`` means that the supplied horizon ends while queue remains. This is
    an observation about the finite run, not a proof that the queue will never
    clear.
    """

    items = tuple(states)
    for item in items:
        if item.end_queue_veh <= 1e-9:
            return item.cycle_index + 1
    return None
