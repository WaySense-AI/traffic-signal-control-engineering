"""Simple, explainable traffic-data quality checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Iterable

from .model import InvariantViolation


@dataclass(frozen=True)
class DetectionPoint:
    time_index: int
    volume_vph: float
    average_queue: float = 0.0

    def __post_init__(self) -> None:
        if self.volume_vph < 0:
            raise InvariantViolation("volume must be non-negative")
        if self.average_queue < 0:
            raise InvariantViolation("queue must be non-negative")


@dataclass(frozen=True)
class QualityFlag:
    time_anomaly: bool
    physical_inconsistency: bool

    @property
    def abnormal(self) -> bool:
        return self.time_anomaly or self.physical_inconsistency


def exponential_moving_average(values: Iterable[float], span: int) -> tuple[float, ...]:
    if span < 1:
        raise InvariantViolation("span must be positive")
    result: list[float] = []
    alpha = 2.0 / (span + 1.0)
    current: float | None = None
    for value in values:
        current = value if current is None else alpha * value + (1.0 - alpha) * current
        result.append(current)
    return tuple(result)


def assess_series(
    points: tuple[DetectionPoint, ...],
    *,
    span: int = 4,
    sigma: float = 3.0,
    low_volume: float = 3.0,
    high_queue: float = 20.0,
) -> tuple[QualityFlag, ...]:
    """Flag temporal deviations and a basic demand/queue contradiction.

    The temporal check compares each observation with an exponential moving
    average. The threshold uses residual standard deviation and is deliberately
    conservative for short series.
    """

    if sigma <= 0:
        raise InvariantViolation("sigma must be positive")
    ordered = tuple(sorted(points, key=lambda point: point.time_index))
    if len({point.time_index for point in ordered}) != len(ordered):
        raise InvariantViolation("time_index values must be unique")
    if not ordered:
        return ()

    baseline = exponential_moving_average(
        (point.volume_vph for point in ordered), span=span
    )
    residuals = [
        point.volume_vph - expected for point, expected in zip(ordered, baseline)
    ]
    center = mean(residuals)
    variance = mean((residual - center) ** 2 for residual in residuals)
    threshold = max(sigma * sqrt(variance), 1.0)

    flags: list[QualityFlag] = []
    for point, residual in zip(ordered, residuals):
        time_anomaly = abs(residual - center) > threshold
        physical_inconsistency = (
            point.volume_vph <= low_volume and point.average_queue >= high_queue
        )
        flags.append(
            QualityFlag(
                time_anomaly=time_anomaly,
                physical_inconsistency=physical_inconsistency,
            )
        )
    return tuple(flags)

