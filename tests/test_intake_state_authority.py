import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from next_shift.intake_contract import IntakeResult
from services.operations_ui.runtime import _event_from_stream_line
from services.operations_ui.runtime import _json_from_text
from services.operations_ui.runtime import _structured_results


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_RUNTIME = ROOT / "services" / "operations_ui" / "runtime.py"
OPERATIONS_MAIN = ROOT / "services" / "operations_ui" / "main.py"
OPERATIONS_AUTHORITY = (
    ROOT / "services" / "operations_ui" / "state_authority.py"
)
OPERATIONS_APP = (
    ROOT / "services" / "operations_ui" / "static" / "app.js"
)
STATE_MAIN = ROOT / "services" / "state_authority" / "main.py"
STATE_INTAKE = ROOT / "services" / "state_authority" / "intake.py"
STATE_VALIDATION = (
    ROOT / "services" / "state_authority" / "intake_validation.py"
)
STATE_DISPATCH = (
    ROOT / "services" / "state_authority" / "intake_dispatch.py"
)
STATE_POLICY = ROOT / "services" / "state_authority" / "policy.py"
STATE_REQUIREMENTS = (
    ROOT / "services" / "state_authority" / "requirements.txt"
)


def _sample_payload() -> dict[str, object]:
    return {
        "facilities": [],
        "asset_logistics": [
            {
                "title": "Wheelchair needed",
                "description": "Standard wheelchair required in Room 512",
                "workflow_input": {
                    "destination": "Room 512",
                },
                "human_approval_required": False,
            }
        ],
        "language_access": [],
        "discharge_dme": [],
        "evs_throughput": [],
        "patient_transport": [],
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
    def test_typed_contract_accepts_multi_owner_intake(self) -> None:
        payload = _sample_payload()
        payload["language_access"] = [
            {
                "title": "Spanish interpreter needed",
                "description": "Spanish interpreter required in Room 512",
                "workflow_input": {
                    "language": "Spanish",
                    "service_location": "Room 512",
                },
                "human_approval_required": False,
            }
        ]

        result = IntakeResult.model_validate(payload)

        self.assertEqual(len(result.asset_logistics), 1)
        self.assertEqual(len(result.language_access), 1)
        self.assertEqual(
            result.language_access[0].workflow_input.language,
            "Spanish",
        )

    def test_typed_contract_rejects_missing_language_fields(self) -> None:
        payload = _sample_payload()
        payload["language_access"] = [
            {
                "title": "Spanish interpreter needed",
                "description": "Interpreter required in Room 512",
                "workflow_input": {},
                "human_approval_required": False,
            }
        ]

        with self.assertRaises(ValidationError):
            IntakeResult.model_validate(payload)

    def test_typed_contract_rejects_missing_facilities_fields(self) -> None:
        payload = _sample_payload()
        payload["facilities"] = [
            {
                "title": "Leaking sink",
                "description": "Sink leaking in Room 512",
                "workflow_input": {
                    "facility_type": "plumbing",
                },
                "human_approval_required": False,
            }
        ]

        with self.assertRaises(ValidationError):
            IntakeResult.model_validate(payload)

    def test_runtime_flattens_owner_bucket_into_canonical_proposal(self) -> None:
        parsed = _json_from_text(
            json.dumps(_sample_payload())
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(
            parsed["issues"][0]["owner"],
            "AssetLogistics",
        )
        self.assertEqual(
            parsed["issues"][0]["workflow_input"]["destination"],
            "Room 512",
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
            "data: " + json.dumps(_observed_runtime_event())
        )

        self.assertIsNotNone(event)
        self.assertEqual(len(_structured_results(event)), 1)

    def test_runtime_preserves_legacy_structured_shape_during_rollout(
        self,
    ) -> None:
        legacy = {
            "issues": [
                {
                    "title": "Wheelchair needed",
                    "description": "Wheelchair required",
                    "owner": "AssetLogistics",
                    "workflow_input": {"destination": "Room 512"},
                    "human_approval_required": False,
                }
            ],
            "rejected_clinical_requests": [],
            "summary": "One issue.",
        }

        parsed = _json_from_text(json.dumps(legacy))

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["issues"][0]["owner"], "AssetLogistics")

    def test_operations_ui_requires_structured_output_before_persisting(
        self,
    ) -> None:
        runtime_source = OPERATIONS_RUNTIME.read_text(encoding="utf-8")
        main_source = OPERATIONS_MAIN.read_text(encoding="utf-8")
        client_source = OPERATIONS_AUTHORITY.read_text(encoding="utf-8")
        app_source = OPERATIONS_APP.read_text(encoding="utf-8")

        self.assertIn('"structured_output": False', runtime_source)
        self.assertIn(
            'result.get("structured_output") is not True',
            main_source,
        )
        self.assertIn("persist_handover_proposals(", main_source)
        self.assertIn("STATE_AUTHORITY_URL", client_source)
        self.assertIn('f"{authority_url}/v1/issues"', client_source)
        self.assertIn("const raw = await response.text();", app_source)
        self.assertIn("payload?.message", app_source)

    def test_state_authority_allowlists_and_requires_workflow_fields(
        self,
    ) -> None:
        validation_source = STATE_VALIDATION.read_text(encoding="utf-8")

        self.assertIn("WORKFLOW_FIELDS_BY_OWNER", validation_source)
        self.assertIn(
            "REQUIRED_WORKFLOW_FIELDS_BY_OWNER",
            validation_source,
        )
        self.assertIn(
            "workflow_input_field_not_authorized",
            validation_source,
        )
        self.assertIn("workflow_input_field_required", validation_source)
        self.assertIn('"home_oxygen"', validation_source)
        self.assertIn('"air_conditioning"', validation_source)
        self.assertIn('"wheelchair"', validation_source)

    def test_state_authority_owns_creation_and_dispatch(self) -> None:
        main_source = STATE_MAIN.read_text(encoding="utf-8")
        intake_source = STATE_INTAKE.read_text(encoding="utf-8")
        dispatch_source = STATE_DISPATCH.read_text(encoding="utf-8")
        policy_source = STATE_POLICY.read_text(encoding="utf-8")
        requirements = STATE_REQUIREMENTS.read_text(encoding="utf-8")

        self.assertIn('@app.post("/v1/issues")', main_source)
        self.assertIn("authorize_and_create(", main_source)
        self.assertIn('"ns-operations-ui@"', policy_source)
        self.assertIn('"intake.create"', policy_source)
        self.assertIn("publish_received(issue)", intake_source)
        self.assertIn("pubsub_v1.PublisherClient()", dispatch_source)
        self.assertIn('"state": "RECEIVED"', intake_source)
        self.assertIn("google-cloud-pubsub==2.39.0", requirements)


if __name__ == "__main__":
    unittest.main()
