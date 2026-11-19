import unittest

from signal_lab.model import InvariantViolation, SignalPlan, SignalStage
from signal_lab.optimizer import (
    AutomationReadiness,
    apply_green_proportions,
    blend_target_ratios,
    stage_green_ratios,
    webster_cycle,
)


def stage(stage_id: str, green: int) -> SignalStage:
    return SignalStage(
        stage_id=stage_id,
        green=green,
        green_flash=3,
        yellow=3,
        all_red=2,
        min_green=10,
        phase_ids=(f"phase-{stage_id}",),
    )


class WebsterTests(unittest.TestCase):
    def test_cycle_and_bounds(self) -> None:
        result = webster_cycle(
            {"A": 0.3, "B": 0.4},
            lost_time_s=12,
            min_cycle_s=45,
            max_cycle_s=180,
        )
        self.assertAlmostEqual(result.critical_ratio_sum, 0.7)
        self.assertAlmostEqual(result.theoretical_cycle_s, 76.6666666667)
        self.assertEqual(result.bounded_cycle_s, 77)

    def test_capacity_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            webster_cycle({"A": 0.5, "B": 0.5}, lost_time_s=12)


class AdaptiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = SignalPlan(
            site_id="S1",
            cycle=90,
            stages=(stage("A", 28), stage("B", 21), stage("C", 17)),
        )

    def test_blend_is_normalized(self) -> None:
        blended = blend_target_ratios(
            {"A": 0.5, "B": 0.3, "C": 0.2},
            {"A": 0.7, "B": 0.2, "C": 0.1},
            target_weight=0.3,
        )
        self.assertAlmostEqual(sum(blended.values()), 1.0)
        self.assertAlmostEqual(blended["A"], 0.56)

    def test_green_proportions_preserve_clearance(self) -> None:
        result = apply_green_proportions(
            self.plan,
            stage_green_ratios(self.plan),
        )
        self.assertEqual(result.cycle, self.plan.cycle)
        self.assertEqual(
            [item.green for item in result.stages],
            [item.green for item in self.plan.stages],
        )

    def test_automation_requires_all_safeguards(self) -> None:
        readiness = AutomationReadiness(
            plan_validated=True,
            telemetry_fresh=True,
            device_online=False,
            control_mode_allows_automation=True,
            input_confidence=0.9,
        )
        self.assertFalse(readiness.can_auto_apply)
        self.assertEqual(readiness.rejection_reasons(), ("device is offline",))


if __name__ == "__main__":
    unittest.main()

