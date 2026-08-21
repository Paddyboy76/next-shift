import json
import unittest
from pathlib import Path

from next_shift.intake_contract import IntakeResult
from services.operations_ui.runtime import _event_from_stream_line
from services.operations_ui.runtime import _json_from_text
from services.operations_ui.runtime import _structured_results


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
OPERATIONS_APP = (
    ROOT / "services" / "operations_ui" / "static" / "app.js"
)
STATE_MAIN = (
    ROOT / "services" / "state_authority" / "main.py"
)
STATE_INTAKE = (
    ROOT / "services" / "state_authority" / "intake.py"
)
STATE_VALIDATION = (
    ROOT / "services" / "state_authority" / "intake_validation.py"
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


def _sample_payload() -> dict[str, object]:
    return {
        "issues": [
            {
                "title": "Wheelchair needed",
                "description": "Standard wheelchair required in Room 512",
                "owner": "AssetLogistics",
                "workflow_input": {
                    "destination": "Room 512",
                },
                "human_approval_required": False,
            }
        ],
        "rejected_clinical_requests": [],
        "summary": "One operational issue identified.",
    }


def _observed_runtime_event() -> dict[str, object]:
    return {
        "model_version": "gemini-3.5-flash",
        "content": {
            "parts": [
                {
                    "text": json.dumps(
                        _sample_payload(),
                        separators=(",", ":"),
                    )
                }
            ],
            "role": "model",
        },
        "finish_reason": "STOP",
        "author": "next_shift",
    }


class IntakeStateAuthorityTests(unittest.TestCase):
    def test_typed_contract_accepts_multi_issue_intake(self) -> None:
        result = IntakeResult.model_validate(
            {
                "issues": [
                    _sample_payload()["issues"][0],
                    {
                        "title": "Spanish interpreter needed",
                        "description": (
                            "Spanish interpreter required in Room 512"
                        ),
                        "owner": "LanguageAccess",
                        "workflow_input": {
                            "language": "Spanish",
                            "service_location": "Room 512",
                        },
                        "human_approval_required": False,
                    },
                ],
                "rejected_clinical_requests": [],
                "summary": "Two unresolved operational issues identified.",
            }
        )

        self.assertEqual(len(result.issues), 2)
        self.assertEqual(
            result.issues[0].owner,
            "AssetLogistics",
        )

    def test_runtime_parses_schema_json_from_final_text(self) -> None:
        parsed = _json_from_text(
            json.dumps(_sample_payload())
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(
            parsed["issues"][0]["owner"],
            "AssetLogistics",
        )

    def test_runtime_parses_fenced_schema_json(self) -> None:
        payload = {
            "issues": [],
            "rejected_clinical_requests": [
                "Medication dosage change"
            ],
            "summary": "Clinical request rejected.",
        }

        parsed = _json_from_text(
            "```json\n"
            + json.dumps(payload)
            + "\n```"
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(
            parsed["rejected_clinical_requests"],
            ["Medication dosage change"],
        )

    def test_runtime_parses_serialized_event_output(self) -> None:
        results = _structured_results(
            {
                "output": json.dumps(
                    _sample_payload()
                )
            }
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["issues"][0]["owner"],
            "AssetLogistics",
        )

    def test_runtime_accepts_observed_bare_json_stream_line(self) -> None:
        event = _event_from_stream_line(
            json.dumps(_observed_runtime_event())
        )

        self.assertIsNotNone(event)
        results = _structured_results(event)
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["issues"][0]["owner"],
            "AssetLogistics",
        )

    def test_runtime_still_accepts_sse_data_framing(self) -> None:
        event = _event_from_stream_line(
            "data: "
            + json.dumps(_observed_runtime_event())
        )

        self.assertIsNotNone(event)
        results = _structured_results(event)
        self.assertEqual(len(results), 1)

    def test_operations_ui_requires_structured_output_before_persisting(
        self,
    ) -> None:
        runtime_source = OPERATIONS_RUNTIME.read_text(
            encoding="utf-8"
        )
        main_source = OPERATIONS_MAIN.read_text(
            encoding="utf-8"
        )
        client_source = OPERATIONS_AUTHORITY.read_text(
            encoding="utf-8"
        )
        app_source = OPERATIONS_APP.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '"structured_output": False',
            runtime_source,
        )
        self.assertIn(
            'result.get("structured_output") is not True',
            main_source,
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
        self.assertIn(
            "const raw = await response.text();",
            app_source,
        )
        self.assertIn(
            "payload?.message",
            app_source,
        )

    def test_state_authority_allowlists_model_workflow_fields(self) -> None:
        validation_source = STATE_VALIDATION.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "WORKFLOW_FIELDS_BY_OWNER",
            validation_source,
        )
        self.assertIn(
            "REQUIRED_WORKFLOW_FIELDS_BY_OWNER",
            validation_source,
        )
        self.assertIn(
            "workflow_input_field_not_authorized",
            validation_source,
        )
        self.assertIn(
            "workflow_input_field_required",
            validation_source,
        )
        self.assertIn(
            '"home_oxygen"',
            validation_source,
        )
        self.assertIn(
            '"air_conditioning"',
            validation_source,
        )
        self.assertIn(
            '"wheelchair"',
            validation_source,
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
