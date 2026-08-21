import unittest
from pathlib import Path

from next_shift.tools import create_handover_issue


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_RUNTIME = (
    ROOT / "services" / "operations_ui" / "runtime.py"
)
OPERATIONS_MAIN = (
    ROOT / "services" / "operations_ui" / "main.py"
)
OPERATIONS_AUTHORITY = (
    ROOT / "services" / "operations_ui" / "state_authority.py"
)
STATE_MAIN = (
    ROOT / "services" / "state_authority" / "main.py"
)
STATE_INTAKE = (
    ROOT / "services" / "state_authority" / "intake.py"
)
STATE_DISPATCH = (
    ROOT / "services" / "state_authority" / "intake_dispatch.py"
)
STATE_POLICY = (
    ROOT / "services" / "state_authority" / "policy.py"
)
STATE_REQUIREMENTS = (
    ROOT / "services" / "state_authority" / "requirements.txt"
)


class IntakeStateAuthorityTests(unittest.TestCase):
    def test_agent_tool_returns_structured_proposal_without_issue_id(
        self,
    ) -> None:
        result = create_handover_issue(
            title="Wheelchair needed",
            description="Standard wheelchair required in Room 512",
            owner="AssetLogistics",
            workflow_input={
                "destination": "Room 512",
            },
        )

        self.assertEqual(
            result["proposal_type"],
            "handover_issue",
        )
        proposal = result["proposal"]
        self.assertEqual(
            proposal["owner"],
            "AssetLogistics",
        )
        self.assertNotIn("id", proposal)
        self.assertNotIn("state", proposal)

    def test_agent_tool_rejects_unknown_owner(self) -> None:
        with self.assertRaises(ValueError):
            create_handover_issue(
                title="Bad owner",
                description="Invalid routing target",
                owner="GeneralAgent",
            )

    def test_operations_ui_extracts_and_persists_proposals(self) -> None:
        runtime_source = OPERATIONS_RUNTIME.read_text(
            encoding="utf-8"
        )
        main_source = OPERATIONS_MAIN.read_text(
            encoding="utf-8"
        )
        client_source = OPERATIONS_AUTHORITY.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'value.get("proposal_type") == "handover_issue"',
            runtime_source,
        )
        self.assertIn(
            "persist_handover_proposals(",
            main_source,
        )
        self.assertIn(
            "STATE_AUTHORITY_URL",
            client_source,
        )
        self.assertIn(
            'f"{authority_url}/v1/issues"',
            client_source,
        )

    def test_state_authority_owns_creation_and_dispatch(self) -> None:
        main_source = STATE_MAIN.read_text(
            encoding="utf-8"
        )
        intake_source = STATE_INTAKE.read_text(
            encoding="utf-8"
        )
        dispatch_source = STATE_DISPATCH.read_text(
            encoding="utf-8"
        )
        policy_source = STATE_POLICY.read_text(
            encoding="utf-8"
        )
        requirements = STATE_REQUIREMENTS.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '@app.post("/v1/issues")',
            main_source,
        )
        self.assertIn(
            "authorize_and_create(",
            main_source,
        )
        self.assertIn(
            '"ns-operations-ui@"',
            policy_source,
        )
        self.assertIn(
            '"intake.create"',
            policy_source,
        )
        self.assertIn(
            "publish_received(issue)",
            intake_source,
        )
        self.assertIn(
            "pubsub_v1.PublisherClient()",
            dispatch_source,
        )
        self.assertIn(
            '"state": "RECEIVED"',
            intake_source,
        )
        self.assertIn(
            "google-cloud-pubsub==2.39.0",
            requirements,
        )


if __name__ == "__main__":
    unittest.main()
