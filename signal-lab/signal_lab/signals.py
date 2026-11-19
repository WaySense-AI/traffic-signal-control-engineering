"""Real-time signal state model and validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Mapping

from .model import InvariantViolation


class ControlMode(IntEnum):
    FIXED_CYCLE = 1
    YELLOW_FLASH = 2
    ALL_RED = 3
    LIGHTS_OFF = 4
    OFFLINE = 5
    LAMP_TEST = 6
    MANUAL = 7
    ADAPTIVE = 8
    SEMI_ACTUATED = 9
    FULL_ACTUATED = 10
    CABLELESS_COORDINATION = 11
    ACTUATED_COORDINATION = 12
    DYNAMIC_COORDINATION = 13
    REGION_COORDINATION = 14
    TEMPORARY_CONTROL = 15


STAGE_OPTIONAL_MODES = frozenset(
    {
        ControlMode.YELLOW_FLASH,
        ControlMode.ALL_RED,
        ControlMode.LIGHTS_OFF,
        ControlMode.OFFLINE,
        ControlMode.LAMP_TEST,
    }
)


@dataclass(frozen=True)
class SignalState:
    site_id: str
    observed_at_epoch_s: int
    cycle_s: int
    elapsed_s: int
    control_mode: ControlMode
    current_stage_id: str | None
    source: str

    def validate(self) -> None:
        if not self.site_id:
            raise InvariantViolation("site_id must not be empty")
        if not self.source:
            raise InvariantViolation("state source must not be empty")
        if self.cycle_s <= 0:
            raise InvariantViolation("cycle_s must be positive")
        if not 0 <= self.elapsed_s < self.cycle_s:
            raise InvariantViolation(
                "elapsed_s must be within [0, cycle_s)"
            )
        if (
            self.current_stage_id is None
            and self.control_mode not in STAGE_OPTIONAL_MODES
        ):
            raise InvariantViolation(
                f"{self.control_mode.name}: current_stage_id is required"
            )

    def is_stale(self, now_epoch_s: int, max_age_s: int) -> bool:
        if max_age_s < 0:
            raise InvariantViolation("max_age_s must be non-negative")
        return now_epoch_s - self.observed_at_epoch_s > max_age_s


def normalize_control_mode(
    platform_mode: int,
    vendor_aliases: Mapping[str, int],
    vendor_value: str | None,
) -> ControlMode:
    try:
        return ControlMode(platform_mode)
    except ValueError as error:
        raise InvariantViolation(
            f"unsupported platform control mode: {platform_mode}"
        ) from error

