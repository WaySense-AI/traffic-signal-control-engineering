"""Time-of-day profile segmentation for fixed-time plans."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable

from .model import InvariantViolation


@dataclass(frozen=True)
class DemandProfile:
    start_s: int
    end_s: int
    ratios: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.end_s <= self.start_s:
            raise InvariantViolation("profile end must be after start")
        if not self.ratios or any(value < 0 for value in self.ratios):
            raise InvariantViolation("profiles require non-negative ratios")


@dataclass(frozen=True)
class DemandSegment:
    start_index: int
    end_index: int
    representative_ratios: tuple[float, ...]
    squared_error: float
    cycle_indices: tuple[int, ...]


def profile_distance(
    first: tuple[float, ...],
    second: tuple[float, ...],
    weights: tuple[float, ...] | None = None,
) -> float:
    if len(first) != len(second):
        raise InvariantViolation("profiles must have equal dimensions")
    if weights is None:
        weights = (1.0,) * len(first)
    if len(weights) != len(first) or any(value < 0 for value in weights):
        raise InvariantViolation("weights must match profiles and be non-negative")
    return sum(
        weight * (left - right) ** 2
        for left, right, weight in zip(first, second, weights)
    ) ** 0.5


def _segment(indices: range, profiles: tuple[DemandProfile, ...], weights):
    dimension = len(profiles[0].ratios)
    representative = tuple(
        sum(profiles[index].ratios[column] for index in indices) / len(indices)
        for column in range(dimension)
    )
    error = sum(
        profile_distance(profiles[index].ratios, representative, weights) ** 2
        for index in indices
    )
    start = indices.start
    end = indices.stop
    return DemandSegment(start, end, representative, error, tuple(indices))


def _segment_errors(
    profiles: tuple[DemandProfile, ...],
    weights: tuple[float, ...],
) -> list[list[float]]:
    """Precompute contiguous weighted SSE values in O(n^2 * dimensions)."""

    size = len(profiles)
    dimensions = len(profiles[0].ratios)
    prefix = [[0.0] * dimensions for _ in range(size + 1)]
    squared_norm = [0.0] * (size + 1)

    for index, profile in enumerate(profiles):
        for column, value in enumerate(profile.ratios):
            prefix[index + 1][column] = prefix[index][column] + value
        squared_norm[index + 1] = squared_norm[index] + sum(
            weight * value * value
            for weight, value in zip(weights, profile.ratios)
        )

    errors = [[inf] * (size + 1) for _ in range(size + 1)]
    for start in range(size):
        for end in range(start + 1, size + 1):
            length = end - start
            representative = tuple(
                (prefix[end][column] - prefix[start][column]) / length
                for column in range(dimensions)
            )
            explained = length * sum(
                weight * value * value
                for weight, value in zip(weights, representative)
            )
            # Floating-point cancellation can produce a tiny negative value
            # for a constant segment whose true SSE is zero.
            errors[start][end] = max(
                0.0,
                squared_norm[end] - squared_norm[start] - explained,
            )
    return errors


def segment_demand_profiles(
    profiles: Iterable[DemandProfile],
    *,
    segment_count: int,
    boundary_penalty: float = 0.0,
    weights: tuple[float, ...] | None = None,
) -> tuple[DemandSegment, ...]:
    """Find an exact-K contiguous segmentation with dynamic programming."""

    items = tuple(profiles)
    if not items:
        raise InvariantViolation("at least one profile is required")
    if not 1 <= segment_count <= len(items):
        raise InvariantViolation("segment_count must be within profile count")
    if boundary_penalty < 0:
        raise InvariantViolation("boundary_penalty must be non-negative")
    dimensions = {len(profile.ratios) for profile in items}
    if len(dimensions) != 1:
        raise InvariantViolation("profiles must have equal dimensions")
    if weights is None:
        weights = (1.0,) * len(items[0].ratios)
    if len(weights) != len(items[0].ratios) or any(value < 0 for value in weights):
        raise InvariantViolation("weights must match profile dimensions")

    size = len(items)
    segment_errors = _segment_errors(items, weights)
    cost = [[inf] * (size + 1) for _ in range(segment_count + 1)]
    previous = [[-1] * (size + 1) for _ in range(segment_count + 1)]
    cost[0][0] = 0.0

    for used in range(1, segment_count + 1):
        for end in range(used, size + 1):
            for start in range(used - 1, end):
                if cost[used - 1][start] == inf:
                    continue
                error = segment_errors[start][end]
                candidate = cost[used - 1][start] + error
                if used > 1:
                    candidate += boundary_penalty
                if candidate < cost[used][end]:
                    cost[used][end] = candidate
                    previous[used][end] = start

    result: list[DemandSegment] = []
    end = size
    for used in range(segment_count, 0, -1):
        start = previous[used][end]
        if start < 0:
            raise AssertionError("segmentation backtrack failed")
        result.append(_segment(range(start, end), items, weights))
        end = start
    return tuple(reversed(result))
