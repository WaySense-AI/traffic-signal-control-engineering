import unittest

from signal_lab.cycle import PiecewiseLinearCycleModel, allocate_green_by_ratio
from signal_lab.demand import (
    MovementDemand,
    degree_of_saturation,
    lane_capacity_vph,
    stage_flow_ratios,
)
from signal_lab.model import InvariantViolation, SignalStage, total_green


def stage(stage_id: str, minimum: int = 10) -> SignalStage:
    return SignalStage(
        stage_id=stage_id,
        green=minimum,
        green_flash=3,
        yellow=3,
        all_red=2,
        min_green=minimum,
        phase_ids=(f"phase-{stage_id}",),
    )


class DemandTests(unittest.TestCase):
    def test_stage_ratio_uses_critical_movement(self) -> None:
        demands = {
            "east-left": MovementDemand("east-left", 320, 1600),
            "east-through": MovementDemand("east-through", 720, 1600),
            "west-through": MovementDemand("west-through", 400, 1600),
        }
        ratios = stage_flow_ratios(
            {
                "A": ("east-left", "east-through"),
                "B": ("west-through",),
            },
            demands,
        )
        self.assertAlmostEqual(ratios["A"], 0.45)
        self.assertAlmostEqual(ratios["B"], 0.25)

    def test_zero_saturation_is_rejected(self) -> None:
        demand = MovementDemand("east", 100, 0)
        with self.assertRaises(InvariantViolation):
            _ = demand.flow_ratio

    def test_capacity_and_degree_of_saturation(self) -> None:
        capacity = lane_capacity_vph(
            saturation_vph=1800,
            effective_green_s=27,
            cycle_s=90,
        )
        self.assertAlmostEqual(capacity, 540)
        self.assertAlmostEqual(degree_of_saturation(486, capacity), 0.9)


class CycleTests(unittest.TestCase):
    def test_piecewise_linear_cycle_model(self) -> None:
        model = PiecewiseLinearCycleModel(((0.3, 60), (0.6, 90), (0.9, 150)))
        self.assertEqual(model.predict(0.1), 60)
        self.assertEqual(model.predict(0.45), 75)
        self.assertEqual(model.predict(0.7), 110)
        self.assertEqual(model.predict(1.0), 150)

    def test_green_allocation_preserves_cycle_and_minimum(self) -> None:
        stages = (stage("A"), stage("B"), stage("C"))
        plan = allocate_green_by_ratio(
            stages,
            {"A": 0.5, "B": 0.3, "C": 0.2},
            cycle=90,
        )
        self.assertEqual(plan.cycle, 90)
        self.assertEqual(total_green(plan), 66)
        self.assertTrue(all(item.green >= item.min_green for item in plan.stages))
        self.assertEqual(plan.stages[0].green, 28)
        self.assertEqual(plan.stages[1].green, 21)
        self.assertEqual(plan.stages[2].green, 17)

    def test_impossible_cycle_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            allocate_green_by_ratio(
                (stage("A"), stage("B"), stage("C")),
                {"A": 1.0},
                cycle=40,
            )


if __name__ == "__main__":
    unittest.main()

