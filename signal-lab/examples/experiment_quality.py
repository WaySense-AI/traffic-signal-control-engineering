"""Show temporal and physical traffic-data anomalies."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_lab import DetectionPoint, assess_series


def main() -> None:
    points = (
        DetectionPoint(0, 100, 2),
        DetectionPoint(1, 105, 2),
        DetectionPoint(2, 98, 3),
        DetectionPoint(3, 102, 2),
        DetectionPoint(4, 500, 2),
        DetectionPoint(5, 101, 2),
        DetectionPoint(6, 2, 30),
    )
    flags = assess_series(points, span=4, sigma=2.0)
    for point, flag in zip(points, flags):
        print(
            f"{point.time_index}: volume={point.volume_vph:>5.0f}, "
            f"queue={point.average_queue:>4.0f}, "
            f"time={flag.time_anomaly}, physical={flag.physical_inconsistency}"
        )


if __name__ == "__main__":
    main()

