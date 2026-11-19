import unittest

from signal_lab import (
    CircularInterval,
    InvariantViolation,
    SignalPlan,
    SignalStage,
    apply_offsets,
    green_at,
    green_band_width_s,
    green_band_width_sweep_s,
    iter_stage_seconds,
    normalize_second,
    queue_clearance_cycles,
    simulate_queue,
    stage_at,
    stage_windows,
)


def two_stage_plan() -> SignalPlan:
    return SignalPlan(
        site_id="S2",
        cycle=51,
        stages=(
            SignalStage("A", 20, 3, 3, 2, 10, ("phase-A",)),
            SignalStage("B", 15, 3, 3, 2, 10, ("phase-B",)),
        ),
    )


class QueueDynamicsTests(unittest.TestCase):
    def test_unserved_arrivals_accumulate_by_conservation(self):
        states = simulate_queue(
            [900] * 8,
            cycle_s=90,
            effective_green_s=27,
            saturation_vph=1800,
        )

        self.assertAlmostEqual(states[0].arrivals_veh, 22.5)
        self.assertAlmostEqual(states[0].service_veh, 13.5)
        self.assertAlmostEqual(states[0].served_veh, 13.5)
        self.assertAlmostEqual(states[0].end_queue_veh, 9.0)
        self.assertAlmostEqual(states[-1].end_queue_veh, 72.0)
        self.assertGreater(states[-1].degree_of_saturation, 1.0)
        self.assertIsNone(queue_clearance_cycles(states))

    def test_storage_limit_separates_local_queue_from_spillback(self):
        state = simulate_queue(
            [900],
            cycle_s=90,
            effective_green_s=27,
            saturation_vph=1800,
            storage_capacity_veh=5,
        )[0]

        self.assertAlmostEqual(state.end_queue_veh, 5.0)
        self.assertAlmostEqual(state.overflow_veh, 4.0)
        self.assertAlmostEqual(
            state.start_queue_veh + state.arrivals_veh,
            state.served_veh + state.end_queue_veh + state.overflow_veh,
        )

    def test_non_saturated_queue_clears(self):
        states = simulate_queue(
            [500],
            cycle_s=90,
            effective_green_s=30,
            saturation_vph=1800,
            initial_queue_veh=2,
        )
        self.assertEqual(queue_clearance_cycles(states), 1)

    def test_invalid_horizon_and_green_are_rejected(self):
        with self.assertRaises(InvariantViolation):
            simulate_queue([], cycle_s=90, effective_green_s=20, saturation_vph=1800)
        with self.assertRaises(InvariantViolation):
            simulate_queue([500], cycle_s=90, effective_green_s=91, saturation_vph=1800)


class TimelineTests(unittest.TestCase):
    def test_circular_interval_handles_wrap_and_half_open_end(self):
        interval = CircularInterval(start_s=85, duration_s=10, cycle_s=90)

        self.assertTrue(interval.wraps)
        self.assertFalse(interval.contains(84))
        self.assertTrue(interval.contains(85))
        self.assertTrue(interval.contains(89))
        self.assertTrue(interval.contains(90))
        self.assertFalse(interval.contains(5))
        self.assertFalse(interval.contains(10))

    def test_circular_intersection_counts_seconds(self):
        green = CircularInterval(70, 20, 90)
        arrival = CircularInterval(80, 20, 90)
        self.assertEqual(green.intersection(arrival), 10)

    def test_stage_windows_cover_the_cycle_once(self):
        plan = two_stage_plan()
        windows = stage_windows(plan)
        self.assertEqual([(item.stage_id, item.start_s) for item in windows], [("A", 0), ("B", 28)])
        self.assertEqual(len(tuple(iter_stage_seconds(plan))), 51)
        self.assertEqual(stage_at(plan, 27).stage_id, "A")
        self.assertEqual(stage_at(plan, 28).stage_id, "B")

    def test_green_and_offset_share_one_time_basis(self):
        plan = two_stage_plan()
        self.assertTrue(green_at(plan, 0))
        self.assertFalse(green_at(plan, 20))
        self.assertTrue(green_at(plan, 28))
        shifted = apply_offsets(plan, 28)
        self.assertTrue(any(item.stage_id == "B" and item.start_s == 5 for item in shifted))
        self.assertEqual(normalize_second(-1, 51), 50)


class BandAlgorithmTests(unittest.TestCase):
    def test_sweep_matches_scan_for_wrapped_and_fractional_travel(self):
        cases = (
            ((0, 26, 58, 76), (0, 26, 58, 76), (40, 40, 40, 40)),
            ((0, 50, 58, 76), (0, 26, 58, 76), (40, 40, 40, 40)),
            ((0, 17), (0, 17.25), (40, 35)),
            ((85, 5), (0, 12.5), (20, 20)),
        )
        for offsets, travel, greens in cases:
            with self.subTest(offsets=offsets, travel=travel):
                scan = green_band_width_s(
                    cycle_s=100,
                    offsets_s=offsets,
                    travel_times_s=travel,
                    green_duration_s=greens,
                )
                sweep = green_band_width_sweep_s(
                    cycle_s=100,
                    offsets_s=offsets,
                    travel_times_s=travel,
                    green_duration_s=greens,
                )
                self.assertEqual(sweep, scan)


if __name__ == "__main__":
    unittest.main()
