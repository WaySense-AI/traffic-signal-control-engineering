import unittest

from signal_lab.coordination import (
    CorridorSegment,
    common_cycle_s,
    downstream_offset_s,
    green_band_width_s,
)
from signal_lab.model import InvariantViolation


class CoordinationTests(unittest.TestCase):
    def test_common_cycle_can_be_even(self) -> None:
        self.assertEqual(common_cycle_s((80, 91, 76)), 91)
        self.assertEqual(common_cycle_s((80, 91, 76), even=True), 92)

    def test_travel_time_offset(self) -> None:
        segment = CorridorSegment("A", "B", length_m=180, speed_kmh=36)
        self.assertAlmostEqual(segment.travel_time_s, 18)
        self.assertEqual(downstream_offset_s(30, segment, 90), 48)

    def test_aligned_green_gives_full_band(self) -> None:
        width = green_band_width_s(
            cycle_s=100,
            offsets_s=(0, 0),
            travel_times_s=(0, 10),
            green_duration_s=(40, 40),
        )
        self.assertEqual(width, 30)

    def test_misaligned_green_reduces_band(self) -> None:
        width = green_band_width_s(
            cycle_s=100,
            offsets_s=(0, 25),
            travel_times_s=(0, 10),
            green_duration_s=(40, 40),
        )
        self.assertEqual(width, 25)

    def test_invalid_speed_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            CorridorSegment("A", "B", 100, 0)


if __name__ == "__main__":
    unittest.main()
