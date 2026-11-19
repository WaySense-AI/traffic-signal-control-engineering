"""Exercise command rejection, idempotency, and partial batch execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import (
    CommandEvent,
    CommandLedger,
    CommandStatus,
    ControlCommand,
    aggregate_batch_status,
)


def run_lab() -> dict[str, object]:
    ledger = CommandLedger()
    per_site = {}
    for site_id in ("S1", "S2", "S3", "S4"):
        command = ControlCommand(
            command_id=f"batch-1700:{site_id}",
            batch_id="batch-1700",
            site_id=site_id,
            plan_version=f"{site_id}-v42",
            requested_at_s=0,
        )
        ledger.submit(command)
        command = command.apply(CommandEvent.ACCEPT)
        if site_id == "S3":
            command = command.apply(
                CommandEvent.FAIL,
                failure_reason="device offline",
            )
        else:
            command = command.apply(CommandEvent.DISPATCH)
            if site_id != "S4":
                command = command.apply(CommandEvent.OBSERVE)
        ledger.update(command)
        per_site[site_id] = command.status.value

    duplicate, was_inserted = ledger.submit(
        ControlCommand(
            command_id="batch-1700:S1",
            batch_id="batch-1700",
            site_id="S1",
            plan_version="stale-v41",
            requested_at_s=1,
        )
    )
    statuses = tuple(
        ledger.get(f"batch-1700:{site_id}").status
        for site_id in ("S1", "S2", "S3", "S4")
    )
    batch = aggregate_batch_status(statuses, deadline_passed=False)
    return {
        "per_site": per_site,
        "batch_status": batch.value,
        "duplicate_was_inserted": was_inserted,
        "duplicate_resolved_version": duplicate.plan_version,
        "failed_commands": [
            item.command_id
            for item in ledger.values()
            if item.status is CommandStatus.FAILED
        ],
    }


def main() -> None:
    print(json.dumps(run_lab(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
