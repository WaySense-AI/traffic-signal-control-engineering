import unittest

from signal_lab.model import (
    InvariantViolation,
    SignalPlan,
    SignalStage,
    repair_min_green,
    total_clearance,
    total_green,
    validate_plan,
)


def stage(stage_id: str, green: int, min_green: int = 10) -> SignalStage:
    return SignalStage(
        stage_id=stage_id,
        green=green,
        green_flash=3,
        yellow=3,
        all_red=2,
        min_green=min_green,
        phase_ids=(f"phase-{stage_id}",),
    )


class SignalPlanTests(unittest.TestCase):
    def test_valid_cycle(self) -> None:
        plan = SignalPlan(
            site_id="site-a",
            cycle=98,
            stages=(stage("A", 30), stage("B", 24), stage("C", 20)),
        )
        validate_plan(plan)
        self.assertEqual(total_green(plan), 74)
        self.assertEqual(total_clearance(plan), 24)

    def test_cycle_mismatch_is_rejected(self) -> None:
        plan = SignalPlan(
            site_id="site-a",
            cycle=99,
            stages=(stage("A", 30), stage("B", 24), stage("C", 20)),
        )
        with self.assertRaises(InvariantViolation):
            validate_plan(plan)

    def test_minimum_green_repair_preserves_cycle_and_clearance(self) -> None:
        plan = SignalPlan(
            site_id="site-a",
            cycle=90,
            stages=(stage("A", 38), stage("B", 8, min_green=14), stage("C", 20)),
        )
        repaired = repair_min_green(plan)
        validate_plan(repaired)
        self.assertEqual(repaired.cycle, plan.cycle)
        self.assertEqual(total_clearance(repaired), total_clearance(plan))
        self.assertTrue(all(s.green >= s.min_green for s in repaired.stages))

    def test_impossible_minimum_green_repair_is_rejected(self) -> None:
        plan = SignalPlan(
            site_id="site-a",
            cycle=30,
            stages=(stage("A", 10, min_green=20), stage("B", 4, min_green=10)),
        )
        with self.assertRaises(InvariantViolation):
            repair_min_green(plan)


if __name__ == "__main__":
    unittest.main()

