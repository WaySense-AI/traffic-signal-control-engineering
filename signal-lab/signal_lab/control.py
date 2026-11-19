"""Control command lifecycle and idempotent ledger."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .model import InvariantViolation


class CommandEvent(str, Enum):
    ACCEPT = "accept"
    DISPATCH = "dispatch"
    OBSERVE = "observe"
    TIMEOUT = "timeout"
    FAIL = "fail"
    ROLLBACK = "rollback"


class CommandStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    DISPATCHED = "dispatched"
    OBSERVED = "observed"
    UNKNOWN = "unknown"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class BatchStatus(str, Enum):
    WAITING = "waiting"
    OBSERVED = "observed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    FAILED = "failed"


@dataclass(frozen=True)
class StateVersion:
    event_time_s: int
    sequence: int

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise InvariantViolation("state sequence must be non-negative")


TRANSITIONS = {
    (CommandStatus.REQUESTED, CommandEvent.ACCEPT): CommandStatus.ACCEPTED,
    (CommandStatus.REQUESTED, CommandEvent.FAIL): CommandStatus.FAILED,
    (CommandStatus.ACCEPTED, CommandEvent.DISPATCH): CommandStatus.DISPATCHED,
    (CommandStatus.ACCEPTED, CommandEvent.TIMEOUT): CommandStatus.UNKNOWN,
    (CommandStatus.ACCEPTED, CommandEvent.FAIL): CommandStatus.FAILED,
    (CommandStatus.DISPATCHED, CommandEvent.OBSERVE): CommandStatus.OBSERVED,
    (CommandStatus.DISPATCHED, CommandEvent.TIMEOUT): CommandStatus.UNKNOWN,
    (CommandStatus.DISPATCHED, CommandEvent.FAIL): CommandStatus.FAILED,
    (CommandStatus.UNKNOWN, CommandEvent.OBSERVE): CommandStatus.OBSERVED,
    (CommandStatus.UNKNOWN, CommandEvent.FAIL): CommandStatus.FAILED,
    (CommandStatus.UNKNOWN, CommandEvent.ROLLBACK): CommandStatus.ROLLED_BACK,
    (CommandStatus.FAILED, CommandEvent.ROLLBACK): CommandStatus.ROLLED_BACK,
    (CommandStatus.OBSERVED, CommandEvent.ROLLBACK): CommandStatus.ROLLED_BACK,
}


@dataclass(frozen=True)
class ControlCommand:
    command_id: str
    batch_id: str
    site_id: str
    plan_version: str
    requested_at_s: int
    status: CommandStatus = CommandStatus.REQUESTED
    failure_reason: str | None = None

    def apply(self, event: CommandEvent, *, failure_reason: str | None = None) -> "ControlCommand":
        key = (self.status, event)
        if key not in TRANSITIONS:
            raise InvariantViolation(
                f"invalid command transition: {self.status.value} + {event.value}"
            )
        if event is CommandEvent.FAIL and not failure_reason:
            raise InvariantViolation("failure transition requires a reason")
        return replace(
            self,
            status=TRANSITIONS[key],
            failure_reason=failure_reason if event is CommandEvent.FAIL else self.failure_reason,
        )


class CommandLedger:
    def __init__(self) -> None:
        self._commands: dict[str, ControlCommand] = {}

    def submit(self, command: ControlCommand) -> tuple[ControlCommand, bool]:
        existing = self._commands.get(command.command_id)
        if existing is not None:
            return existing, False
        self._commands[command.command_id] = command
        return command, True

    def update(self, command: ControlCommand) -> None:
        if command.command_id not in self._commands:
            raise InvariantViolation(f"unknown command: {command.command_id}")
        self._commands[command.command_id] = command

    def get(self, command_id: str) -> ControlCommand:
        try:
            return self._commands[command_id]
        except KeyError as error:
            raise InvariantViolation(f"unknown command: {command_id}") from error

    def values(self) -> tuple[ControlCommand, ...]:
        return tuple(self._commands[key] for key in sorted(self._commands))


def accept_state_version(
    current: StateVersion | None,
    incoming: StateVersion,
) -> tuple[bool, str]:
    """Decide whether an event may replace the current cached state."""

    if current is None:
        return True, "first-state"
    if (incoming.event_time_s, incoming.sequence) > (
        current.event_time_s,
        current.sequence,
    ):
        return True, "newer"
    if (incoming.event_time_s, incoming.sequence) == (
        current.event_time_s,
        current.sequence,
    ):
        return False, "duplicate-or-conflict"
    return False, "older"


def aggregate_batch_status(
    statuses: tuple[CommandStatus, ...],
    *,
    deadline_passed: bool,
) -> BatchStatus:
    """Aggregate per-site command states without hiding partial execution."""

    if not statuses:
        raise InvariantViolation("batch aggregation requires at least one command")
    observed = sum(status is CommandStatus.OBSERVED for status in statuses)
    failed = sum(status is CommandStatus.FAILED for status in statuses)
    if observed == len(statuses):
        return BatchStatus.OBSERVED
    if failed == len(statuses):
        return BatchStatus.FAILED
    if observed or failed:
        return BatchStatus.PARTIAL
    return BatchStatus.UNKNOWN if deadline_passed else BatchStatus.WAITING

