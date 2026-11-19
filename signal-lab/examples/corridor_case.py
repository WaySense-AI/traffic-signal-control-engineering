"""Run the S1-S4 corridor case used in the final chapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import (
    BatchStatus,
    CommandStatus,
    MovementDemand,
    PiecewiseLinearCycleModel,
    SignalStage,
    aggregate_batch_status,
    allocate_green_by_ratio,
    common_cycle_s,
    cumulative_travel_times_s,
    green_band_width_s,
    stage_flow_ratios,
)


SITE_FLOWS = {
    "S1": {
        "east-through": MovementDemand("east-through", 520, 1800),
        "east-left": MovementDemand("east-left", 180, 1450),
        "west-through": MovementDemand("west-through", 420, 1800),
        "north-left": MovementDemand("north-left", 150, 1450),
    },
    "S2": {
        "east-through": MovementDemand("east-through", 800, 1600),
        "east-left": MovementDemand("east-left", 200, 1450),
        "west-through": MovementDemand("west-through", 500, 1600),
        "north-left": MovementDemand("north-left", 220, 1450),
    },
    "S3": {
        "east-through": MovementDemand("east-through", 650, 1800),
        "east-left": MovementDemand("east-left", 180, 1450),
        "west-through": MovementDemand("west-through", 400, 1800),
        "north-left": MovementDemand("north-left", 180, 1450),
    },
    "S4": {
        "east-through": MovementDemand("east-through", 700, 1800),
        "east-left": MovementDemand("east-left", 160, 1450),
        "west-through": MovementDemand("west-through", 380, 1800),
        "north-left": MovementDemand("north-left", 160, 1450),
    },
}

STAGE_MOVEMENTS = {
    "A": ("east-through", "east-left"),
    "B": ("west-through",),
    "C": ("north-left",),
}


def empty_stages() -> tuple[SignalStage, ...]:
    return tuple(
        SignalStage(
            stage_id=stage_id,
            green=12,
            green_flash=3,
            yellow=3,
            all_red=2,
            min_green=12,
            phase_ids=(f"phase-{stage_id}",),
        )
        for stage_id in ("A", "B", "C")
    )


def run_case() -> dict:
    ratios_by_site = {
        site_id: stage_flow_ratios(STAGE_MOVEMENTS, demands)
        for site_id, demands in SITE_FLOWS.items()
    }
    cycle_model = PiecewiseLinearCycleModel(((0.3, 70), (0.6, 95), (0.9, 150)))
    natural_cycles = {
        site_id: cycle_model.predict(sum(ratios.values()))
        for site_id, ratios in ratios_by_site.items()
    }
    public_cycle = common_cycle_s(natural_cycles.values())
    plans = {
        site_id: allocate_green_by_ratio(
            empty_stages(),
            ratios,
            public_cycle,
        )
        for site_id, ratios in ratios_by_site.items()
    }

    travel_times = cumulative_travel_times_s((260, 320, 180), (36, 36, 36))
    offsets = tuple(round(value) % public_cycle for value in travel_times)
    green_a = tuple(plans[site_id].stages[0].green for site_id in ("S1", "S2", "S3", "S4"))
    forward_band = green_band_width_s(
        cycle_s=public_cycle,
        offsets_s=offsets,
        travel_times_s=travel_times,
        green_duration_s=green_a,
    )
    altered_band = green_band_width_s(
        cycle_s=public_cycle,
        offsets_s=(0, 50, 58, 76),
        travel_times_s=travel_times,
        green_duration_s=green_a,
    )

    batch = aggregate_batch_status(
        (
            CommandStatus.OBSERVED,
            CommandStatus.OBSERVED,
            CommandStatus.FAILED,
            CommandStatus.DISPATCHED,
        ),
        deadline_passed=False,
    )

    return {
        "stage_flow_ratios": {
            site_id: {key: round(value, 4) for key, value in ratios.items()}
            for site_id, ratios in ratios_by_site.items()
        },
        "natural_cycles_s": natural_cycles,
        "public_cycle_s": public_cycle,
        "pure_green_s": {
            site_id: [stage.green for stage in plan.stages]
            for site_id, plan in plans.items()
        },
        "cumulative_travel_times_s": travel_times,
        "forward_offsets_s": offsets,
        "forward_band_s": forward_band,
        "bad_s2_offset_band_s": altered_band,
        "batch_status": batch.value,
    }


def main() -> None:
    print(json.dumps(run_case(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
