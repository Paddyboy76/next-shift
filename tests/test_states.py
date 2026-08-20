import unittest

from next_shift.domain.states import (
    ALLOWED_TRANSITIONS,
    VALID_STATES,
)


class WorkflowStateTests(unittest.TestCase):
    def test_canonical_states_are_exact(self) -> None:
        self.assertEqual(
            VALID_STATES,
            {
                "RECEIVED",
                "TRIAGED",
                "ASSIGNED",
                "ACTION_PENDING",
                "VERIFYING",
                "CLOSED",
                "BLOCKED",
                "HUMAN_REVIEW",
                "FAILED",
            },
        )

    def test_all_transition_sources_are_valid_states(self) -> None:
        self.assertEqual(set(ALLOWED_TRANSITIONS), VALID_STATES)

    def test_all_transition_targets_are_valid_states(self) -> None:
        for source, targets in ALLOWED_TRANSITIONS.items():
            with self.subTest(source=source):
                self.assertTrue(targets <= VALID_STATES)

    def test_received_can_only_enter_first_stage_outcomes(self) -> None:
        self.assertEqual(
            ALLOWED_TRANSITIONS["RECEIVED"],
            {"TRIAGED", "HUMAN_REVIEW", "FAILED"},
        )

    def test_workflow_cannot_skip_directly_to_closed(self) -> None:
        for state in VALID_STATES - {"VERIFYING", "CLOSED"}:
            with self.subTest(state=state):
                self.assertNotIn(
                    "CLOSED",
                    ALLOWED_TRANSITIONS[state],
                )

    def test_only_verifying_can_close_issue(self) -> None:
        closers = {
            state
            for state, targets in ALLOWED_TRANSITIONS.items()
            if "CLOSED" in targets
        }
        self.assertEqual(closers, {"VERIFYING"})

    def test_closed_is_terminal(self) -> None:
        self.assertEqual(ALLOWED_TRANSITIONS["CLOSED"], set())

    def test_failed_is_terminal(self) -> None:
        self.assertEqual(ALLOWED_TRANSITIONS["FAILED"], set())

    def test_verification_can_return_work_for_action(self) -> None:
        self.assertIn(
            "ACTION_PENDING",
            ALLOWED_TRANSITIONS["VERIFYING"],
        )


if __name__ == "__main__":
    unittest.main()
