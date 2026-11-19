import unittest

from signal_lab.control import (
    BatchStatus,
    CommandEvent,
    CommandLedger,
    CommandStatus,
    ControlCommand,
    aggregate_batch_status,
)
from signal_lab.evaluation import MovementEvaluation, SiteEvaluation
from signal_lab.model import InvariantViolation


class CommandTests(unittest.TestCase):
    def test_valid_command_lifecycle(self) -> None:
        command = ControlCommand(
            command_id="cmd-1",
            batch_id="batch-1",
            site_id="S1",
            plan_version="v3",
            requested_at_s=100,
        )
        command = command.apply(CommandEvent.ACCEPT)
        command = command.apply(CommandEvent.DISPATCH)
        command = command.apply(CommandEvent.OBSERVE)
        self.assertEqual(command.status, CommandStatus.OBSERVED)

    def test_invalid_transition_is_rejected(self) -> None:
        command = ControlCommand(
            command_id="cmd-1",
            batch_id="batch-1",
            site_id="S1",
            plan_version="v3",
            requested_at_s=100,
        )
        with self.assertRaises(InvariantViolation):
            command.apply(CommandEvent.OBSERVE)

    def test_timeout_is_unknown_until_observation_arrives(self) -> None:
        command = ControlCommand(
            command_id="cmd-2",
            batch_id="batch-1",
            site_id="S2",
            plan_version="v42",
            requested_at_s=100,
        )
        command = command.apply(CommandEvent.ACCEPT)
        command = command.apply(CommandEvent.DISPATCH)
        command = command.apply(CommandEvent.TIMEOUT)
        self.assertEqual(command.status, CommandStatus.UNKNOWN)
        command = command.apply(CommandEvent.OBSERVE)
        self.assertEqual(command.status, CommandStatus.OBSERVED)

    def test_expired_unresolved_batch_is_unknown(self) -> None:
        status = aggregate_batch_status(
            (CommandStatus.DISPATCHED, CommandStatus.UNKNOWN),
            deadline_passed=True,
        )
        self.assertEqual(status, BatchStatus.UNKNOWN)

    def test_ledger_submit_is_idempotent(self) -> None:
        ledger = CommandLedger()
        command = ControlCommand(
            command_id="cmd-1",
            batch_id="batch-1",
            site_id="S1",
            plan_version="v3",
            requested_at_s=100,
        )
        first, created = ledger.submit(command)
        second, created_again = ledger.submit(command)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first, second)


class EvaluationTests(unittest.TestCase):
    def test_over_capacity_is_reported(self) -> None:
        evaluation = SiteEvaluation(
            movements=(
                MovementEvaluation("east-through", 540, 1800, 27, 90),
                MovementEvaluation("west-through", 486, 1800, 27, 90),
            )
        )
        self.assertAlmostEqual(evaluation.max_degree_of_saturation, 1.0)
        self.assertEqual(evaluation.over_capacity_movements, ())

        over = SiteEvaluation(
            movements=(
                MovementEvaluation("east-through", 600, 1800, 27, 90),
            )
        )
        self.assertEqual(over.over_capacity_movements, ("east-through",))


if __name__ == "__main__":
    unittest.main()

