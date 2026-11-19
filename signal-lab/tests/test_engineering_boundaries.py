import unittest

from signal_lab import (
    BatchStatus,
    CommandStatus,
    CountEvent,
    DemandProfile,
    InvariantViolation,
    StateVersion,
    accept_state_version,
    aggregate_batch_status,
    aggregate_count_windows,
    cumulative_travel_times_s,
    difference_in_differences,
    evaluate_adaptive_change,
    flow_weighted_speed,
    profile_distance,
    segment_demand_profiles,
)


class WindowTests(unittest.TestCase):
    def test_half_open_windows_convert_to_hourly_flow(self) -> None:
        windows = aggregate_count_windows(
            (
                CountEvent("a", 0, 10),
                CountEvent("b", 899, 5),
                CountEvent("c", 900, 20),
            ),
            origin_s=0,
            window_s=900,
            window_count=2,
        )
        self.assertEqual(windows[0].count, 15)
        self.assertEqual(windows[0].volume_vph, 60)
        self.assertEqual(windows[1].count, 20)

    def test_duplicate_event_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            aggregate_count_windows(
                (CountEvent("same", 10, 1), CountEvent("same", 20, 1)),
                origin_s=0,
                window_s=900,
                window_count=1,
            )


class ScheduleTests(unittest.TestCase):
    def test_segmentation_keeps_close_profiles_together(self) -> None:
        profiles = tuple(
            DemandProfile(index * 900, (index + 1) * 900, ratios)
            for index, ratios in enumerate(
                ((0.2, 0.1), (0.22, 0.1), (0.8, 0.5), (0.82, 0.52))
            )
        )
        segments = segment_demand_profiles(profiles, segment_count=2)
        self.assertEqual([segment.cycle_indices for segment in segments], [(0, 1), (2, 3)])
        self.assertAlmostEqual(segments[0].representative_ratios[0], 0.21)

    def test_dynamic_programming_matches_bruteforce_boundaries(self) -> None:
        profiles = tuple(
            DemandProfile(index * 900, (index + 1) * 900, ratios)
            for index, ratios in enumerate(
                (
                    (0.20, 0.10),
                    (0.24, 0.12),
                    (0.52, 0.30),
                    (0.58, 0.34),
                    (0.55, 0.32),
                )
            )
        )
        best = float("inf")
        for split in range(1, len(profiles)):
            segments = (profiles[:split], profiles[split:])
            error = 0.0
            for values in segments:
                representative = tuple(
                    sum(profile.ratios[column] for profile in values) / len(values)
                    for column in range(2)
                )
                error += sum(
                    profile_distance(profile.ratios, representative) ** 2
                    for profile in values
                )
            best = min(best, error)
        actual = segment_demand_profiles(profiles, segment_count=2)
        self.assertAlmostEqual(sum(segment.squared_error for segment in actual), best)


class AdaptiveGateTests(unittest.TestCase):
    def test_deadband_suppresses_small_change(self) -> None:
        decision = evaluate_adaptive_change(
            {"A": 30, "B": 20},
            {"A": 32, "B": 20},
            deadband_s=3,
            required_confirmations=2,
            prior_confirmations=0,
            cycle_index=10,
            last_applied_cycle=None,
            cooldown_cycles=0,
        )
        self.assertFalse(decision.apply)
        self.assertEqual(decision.reason, "inside-deadband")

    def test_confirmation_and_cooldown_are_applied(self) -> None:
        pending = evaluate_adaptive_change(
            {"A": 30},
            {"A": 36},
            deadband_s=3,
            required_confirmations=2,
            prior_confirmations=0,
            cycle_index=10,
            last_applied_cycle=None,
            cooldown_cycles=4,
        )
        self.assertFalse(pending.apply)
        cooling = evaluate_adaptive_change(
            {"A": 30},
            {"A": 36},
            deadband_s=3,
            required_confirmations=2,
            prior_confirmations=1,
            cycle_index=12,
            last_applied_cycle=10,
            cooldown_cycles=4,
        )
        self.assertEqual(cooling.reason, "cooldown")


class StateAndBatchTests(unittest.TestCase):
    def test_old_state_does_not_replace_new_state(self) -> None:
        accepted, reason = accept_state_version(
            StateVersion(100, 5),
            StateVersion(99, 20),
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "older")
        self.assertEqual(
            accept_state_version(StateVersion(100, 5), StateVersion(100, 6)),
            (True, "newer"),
        )

    def test_partial_batch_is_not_reported_as_success(self) -> None:
        status = aggregate_batch_status(
            (
                CommandStatus.OBSERVED,
                CommandStatus.OBSERVED,
                CommandStatus.FAILED,
                CommandStatus.DISPATCHED,
            ),
            deadline_passed=False,
        )
        self.assertEqual(status, BatchStatus.PARTIAL)


class CorridorAndEvaluationTests(unittest.TestCase):
    def test_cumulative_corridor_travel_times(self) -> None:
        times = cumulative_travel_times_s((260, 320, 180), (36, 36, 36))
        self.assertEqual(times, (0.0, 26.0, 58.0, 76.0))

    def test_weighted_speed_ignores_zero_flow(self) -> None:
        speed = flow_weighted_speed(((100, 20), (300, 30), (0, 100)))
        self.assertAlmostEqual(speed, 27.5)

    def test_difference_in_differences(self) -> None:
        effect = difference_in_differences(
            treatment_before=20,
            treatment_after=30,
            control_before=22,
            control_after=24,
        )
        self.assertAlmostEqual(effect, 8)


if __name__ == "__main__":
    unittest.main()
