"""Single-intersection timing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Mapping

from .model import InvariantViolation, SignalPlan, validate_plan


@dataclass(frozen=True)
class WebsterResult:
    critical_ratio_sum: float
    theoretical_cycle_s: float
    bounded_cycle_s: int


def webster_cycle(
    stage_flow_ratios: Mapping[str, float],
    lost_time_s: float,
    *,
    min_cycle_s: int = 40,
    max_cycle_s: int = 180,
    gamma: float = 1.5,
    delta: float = 5.0,
) -> WebsterResult:
    """Evaluate the classical Webster cycle model.

    The function rejects Y >= 1 instead of silently clamping an over-capacity
    intersection to a finite cycle.
    """

    if not stage_flow_ratios:
        raise InvariantViolation("at least one stage ratio is required")
    if any(value < 0 for value in stage_flow_ratios.values()):
        raise InvariantViolation("stage ratios must be non-negative")
    if lost_time_s < 0:
        raise InvariantViolation("lost time must be non-negative")
    if not 0 < min_cycle_s <= max_cycle_s:
        raise InvariantViolation("cycle limits must be positive and ordered")

    critical_ratio_sum = sum(stage_flow_ratios.values())
    if critical_ratio_sum >= 1.0:
        raise InvariantViolation(
            "critical ratio sum reaches capacity; Webster cycle is unbounded"
        )
    theoretical = (gamma * lost_time_s + delta) / (1.0 - critical_ratio_sum)
    bounded = min(max(round(theoretical), min_cycle_s), max_cycle_s)
    return WebsterResult(
        critical_ratio_sum=critical_ratio_sum,
        theoretical_cycle_s=theoretical,
        bounded_cycle_s=bounded,
    )


def blend_target_ratios(
    original_ratios: Mapping[str, float],
    target_ratios: Mapping[str, float],
    *,
    target_weight: float,
) -> dict[str, float]:
    """Blend original and target stage proportions in a stable way."""

    if not 0.0 <= target_weight <= 1.0:
        raise InvariantViolation("target_weight must be between 0 and 1")
    keys = set(original_ratios) | set(target_ratios)
    values: dict[str, float] = {}
    for key in keys:
        original = original_ratios.get(key, 0.0)
        target = target_ratios.get(key, 0.0)
        if original < 0 or target < 0:
            raise InvariantViolation("stage proportions must be non-negative")
        values[key] = (1.0 - target_weight) * original + target_weight * target
    total = sum(values.values())
    if total <= 0:
        raise InvariantViolation("blended stage proportions have zero total")
    return {key: value / total for key, value in values.items()}


def stage_green_ratios(plan: SignalPlan) -> dict[str, float]:
    """Use green time rather than total duration as adaptive-plan proportions."""

    total = sum(stage.green for stage in plan.stages)
    if total <= 0:
        raise InvariantViolation("plan contains no green time")
    return {stage.stage_id: stage.green / total for stage in plan.stages}


def apply_green_proportions(
    template: SignalPlan,
    proportions: Mapping[str, float],
) -> SignalPlan:
    """Apply proportions to total green while preserving clearance time."""

    total_green = sum(stage.green for stage in template.stages)
    valid_total = sum(proportions.get(stage.stage_id, 0.0) for stage in template.stages)
    if valid_total <= 0:
        raise InvariantViolation("proportions do not allocate positive green")

    raw = {
        stage.stage_id: total_green
        * proportions.get(stage.stage_id, 0.0)
        / valid_total
        for stage in template.stages
    }
    greens = {stage_id: floor(value) for stage_id, value in raw.items()}
    remainder = total_green - sum(greens.values())
    rank = sorted(
        raw,
        key=lambda stage_id: (-(raw[stage_id] - greens[stage_id]), stage_id),
    )
    for stage_id in rank[:remainder]:
        greens[stage_id] += 1

    result = SignalPlan(
        site_id=template.site_id,
        cycle=template.cycle,
        stages=tuple(
            stage.with_green(greens[stage.stage_id]) for stage in template.stages
        ),
    )
    validate_plan(result)
    return result


@dataclass(frozen=True)
class AutomationReadiness:
    plan_validated: bool
    telemetry_fresh: bool
    device_online: bool
    control_mode_allows_automation: bool
    input_confidence: float
    minimum_confidence: float = 0.7

    def rejection_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.plan_validated:
            reasons.append("plan is not validated")
        if not self.telemetry_fresh:
            reasons.append("telemetry is stale")
        if not self.device_online:
            reasons.append("device is offline")
        if not self.control_mode_allows_automation:
            reasons.append("manual or incompatible control mode")
        if self.input_confidence < self.minimum_confidence:
            reasons.append("input confidence is below threshold")
        return tuple(reasons)

    @property
    def can_auto_apply(self) -> bool:
        return not self.rejection_reasons()


@dataclass(frozen=True)
class AdaptiveDecision:
    apply: bool
    consecutive_qualifying: int
    reason: str


def evaluate_adaptive_change(
    current_greens: Mapping[str, int],
    candidate_greens: Mapping[str, int],
    *,
    deadband_s: int,
    required_confirmations: int,
    prior_confirmations: int,
    cycle_index: int,
    last_applied_cycle: int | None,
    cooldown_cycles: int,
) -> AdaptiveDecision:
    """Apply deterministic deadband, confirmation, and cooldown rules."""

    if deadband_s < 0:
        raise InvariantViolation("deadband_s must be non-negative")
    if required_confirmations <= 0 or cooldown_cycles < 0:
        raise InvariantViolation("confirmation and cooldown settings are invalid")
    if not current_greens:
        raise InvariantViolation("adaptive decision requires at least one stage")
    if set(current_greens) != set(candidate_greens):
        raise InvariantViolation("current and candidate stages must match")
    if cycle_index < 0 or prior_confirmations < 0:
        raise InvariantViolation("cycle and confirmation counters must be non-negative")

    maximum_change = max(
        abs(candidate_greens[stage_id] - current_greens[stage_id])
        for stage_id in current_greens
    )
    if maximum_change < deadband_s:
        return AdaptiveDecision(False, 0, "inside-deadband")

    confirmations = prior_confirmations + 1
    if confirmations < required_confirmations:
        return AdaptiveDecision(False, confirmations, "awaiting-confirmation")
    if (
        last_applied_cycle is not None
        and cycle_index - last_applied_cycle < cooldown_cycles
    ):
        return AdaptiveDecision(False, confirmations, "cooldown")
    return AdaptiveDecision(True, 0, "apply")

