"""Compare offsets and resulting green-band widths."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import green_band_width_s, green_band_width_sweep_s


def main() -> None:
    offsets = {
        "aligned": (0, 0),
        "travel matched": (0, 10),
        "early downstream": (0, 5),
        "late downstream": (0, 25),
    }
    for label, values in offsets.items():
        inputs = dict(
            cycle_s=100,
            offsets_s=values,
            travel_times_s=(0, 10),
            green_duration_s=(40, 40),
        )
        width = green_band_width_s(**inputs)
        sweep = green_band_width_sweep_s(**inputs)
        print(
            f"{label:>16}: offsets={values}, band={width}s, "
            f"event_sweep={sweep}s"
        )


if __name__ == "__main__":
    main()

