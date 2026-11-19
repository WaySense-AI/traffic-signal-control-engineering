import unittest

from signal_lab.mapping import LaneObservation, aggregate_lane_movements
from signal_lab.model import InvariantViolation
from signal_lab.safety import (
    ConflictMatrix,
    PhaseRightOfWay,
    validate_stage_phases,
)


EAST_STRAIGHT = ("east", "straight")
WEST_STRAIGHT = ("west", "straight")
NORTH_LEFT = ("north", "left")


class SafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.phases = {
            "east-west": PhaseRightOfWay(
                "east-west", frozenset((EAST_STRAIGHT, WEST_STRAIGHT))
            ),
            "north-left": PhaseRightOfWay(
                "north-left", frozenset((NORTH_LEFT,))
            ),
        }
        self.conflicts = ConflictMatrix.from_pairs(
            ((EAST_STRAIGHT, NORTH_LEFT), (WEST_STRAIGHT, NORTH_LEFT))
        )

    def test_compatible_phases_can_share_stage(self) -> None:
        validate_stage_phases(
            "A", ("east-west",), self.phases, self.conflicts
        )

    def test_conflicting_phases_cannot_share_stage(self) -> None:
        with self.assertRaises(InvariantViolation):
            validate_stage_phases(
                "A",
                ("east-west", "north-left"),
                self.phases,
                self.conflicts,
            )


class MappingTests(unittest.TestCase):
    def test_shared_lane_volume_is_split(self) -> None:
        result = aggregate_lane_movements(
            [
                LaneObservation("l1", "east", "straight", 600),
                LaneObservation("l2", "east", "straight_left", 400),
            ]
        )
        self.assertEqual(result[("east", "straight")].volume_vph, 800)
        self.assertEqual(result[("east", "left")].volume_vph, 200)
        self.assertEqual(result[("east", "straight")].missing_inputs, 0)

    def test_missing_input_does_not_become_zero(self) -> None:
        result = aggregate_lane_movements(
            [
                LaneObservation("l1", "east", "straight", 600),
                LaneObservation("l2", "east", "left", None, confidence=0.0),
            ]
        )
        self.assertEqual(result[("east", "straight")].volume_vph, 600)
        self.assertIsNone(result[("east", "left")].volume_vph)
        self.assertEqual(result[("east", "left")].missing_inputs, 1)

    def test_duplicate_lane_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            aggregate_lane_movements(
                [
                    LaneObservation("l1", "east", "straight", 600),
                    LaneObservation("l1", "east", "left", 100),
                ]
            )


if __name__ == "__main__":
    unittest.main()

