import unittest

from signal_lab.model import InvariantViolation
from signal_lab.quality import DetectionPoint, assess_series
from signal_lab.signals import ControlMode, SignalState


class QualityTests(unittest.TestCase):
    def test_spike_is_flagged(self) -> None:
        points = tuple(
            DetectionPoint(index, volume)
            for index, volume in enumerate((100, 105, 98, 102, 500, 101))
        )
        flags = assess_series(points, span=4, sigma=2.0)
        self.assertTrue(flags[4].time_anomaly)

    def test_low_volume_high_queue_is_inconsistent(self) -> None:
        points = (DetectionPoint(0, 2, 30),)
        flags = assess_series(points)
        self.assertTrue(flags[0].physical_inconsistency)


class SignalStateTests(unittest.TestCase):
    def test_valid_fixed_cycle_state(self) -> None:
        state = SignalState(
            site_id="S1",
            observed_at_epoch_s=1000,
            cycle_s=90,
            elapsed_s=35,
            control_mode=ControlMode.FIXED_CYCLE,
            current_stage_id="B",
            source="vendor-adapter",
        )
        state.validate()
        self.assertTrue(state.is_stale(1101, max_age_s=100))

    def test_elapsed_time_must_be_inside_cycle(self) -> None:
        state = SignalState(
            site_id="S1",
            observed_at_epoch_s=1000,
            cycle_s=90,
            elapsed_s=90,
            control_mode=ControlMode.FIXED_CYCLE,
            current_stage_id="A",
            source="vendor-adapter",
        )
        with self.assertRaises(InvariantViolation):
            state.validate()

    def test_offline_state_may_have_no_current_stage(self) -> None:
        state = SignalState(
            site_id="S1",
            observed_at_epoch_s=1000,
            cycle_s=90,
            elapsed_s=0,
            control_mode=ControlMode.OFFLINE,
            current_stage_id=None,
            source="vendor-adapter",
        )
        state.validate()


if __name__ == "__main__":
    unittest.main()

