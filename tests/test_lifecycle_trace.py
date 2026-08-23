import unittest
from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader

from services.operations_ui.trace import build_lifecycle_trace


class LifecycleTraceTests(unittest.TestCase):
    def test_builds_governed_trace_from_authoritative_records(self) -> None:
        bundle = {
            "issue": {
                "id": "issue-1",
                "owner": "PatientTransport",
                "title": "Patient transfer",
                "state": "CLOSED",
                "verification_status": "VERIFIED",
                "created_at": "2026-08-22T09:00:00+00:00",
                "intake_principal": "ns-operations-ui@example",
                "source_reference": "operations-ui:test",
                "handover_received_event_id": "event-1",
                "handover_received_message_id": "message-1",
                "transport_request_id": "TRN-123",
            },
            "transitions": [
                {
                    "id": "transition-1",
                    "issue_id": "issue-1",
                    "from_state": "RECEIVED",
                    "to_state": "ACTION_PENDING",
                    "committed_at": "2026-08-22T09:01:00+00:00",
                    "principal": "ns-worker-patient-transport@example",
                    "capability": "patient_transport.coordinate",
                    "reason": "Transport assigned.",
                },
                {
                    "id": "transition-2",
                    "issue_id": "issue-1",
                    "from_state": "VERIFYING",
                    "to_state": "CLOSED",
                    "committed_at": "2026-08-22T09:03:00+00:00",
                    "principal": "ns-verifier@example",
                    "capability": "verification.close",
                    "reason": "Verified evidence accepted.",
                },
            ],
            "human_reach": {
                "delivery_status": "DELIVERED",
                "delivered_at": "2026-08-22T09:01:30+00:00",
                "human_reach_event_id": "hr-event-1",
                "human_reach_message_id": "hr-message-1",
                "chat_message_name": "spaces/example/messages/example",
                "destination_display_name": "Next Shift - Patient Flow",
                "work_order": "TRN-123",
                "who": "Transport Team 17",
                "what": "Patient transfer",
                "where": "Room 618 -> Discharge Lounge",
                "response_history": [],
            },
            "evidence": [
                {
                    "id": "evidence-1",
                    "evidence_type": "transport_arrival",
                    "source": "synthetic_transport_system",
                    "subject": "TRN-123",
                    "created_at": "2026-08-22T09:02:00+00:00",
                    "recorded_by": "ns-trusted-evidence@example",
                    "verified_by": "ns-verifier@example",
                    "details": {"status": "ARRIVED"},
                }
            ],
            "verification_attempts": [
                {
                    "id": "attempt-1",
                    "decision": "REJECTED",
                    "reason": "stale_evidence",
                    "evidence_id": "evidence-old",
                    "verifier": "ns-verifier@example",
                    "created_at": "2026-08-22T09:01:50+00:00",
                    "recoverable": True,
                    "recovery_state": "ACTION_PENDING",
                }
            ],
        }

        trace = build_lifecycle_trace(bundle)

        self.assertEqual(trace["issue_id"], "issue-1")
        self.assertEqual(trace["current_state"], "CLOSED")
        self.assertEqual(trace["verification_status"], "VERIFIED")
        self.assertEqual(trace["work_order"], "TRN-123")

        stages = [item["stage"] for item in trace["items"]]
        self.assertIn("INTAKE", stages)
        self.assertIn("SPECIALIST", stages)
        self.assertIn("HUMAN_REACH", stages)
        self.assertIn("EVIDENCE", stages)
        self.assertIn("VERIFIER", stages)
        self.assertIn("VERIFICATION_FAILURE", stages)

        identifiers = {
            key: value
            for item in trace["items"]
            for key, value in item["identifiers"].items()
        }
        self.assertEqual(identifiers["handover_event_id"], "event-1")
        self.assertEqual(identifiers["human_reach_event_id"], "hr-event-1")
        self.assertEqual(identifiers["evidence_id"], "evidence-1")
        self.assertEqual(identifiers["verification_attempt_id"], "attempt-1")

    def test_trace_template_renders_items_list(self) -> None:
        template_dir = (
            Path(__file__).resolve().parents[1]
            / "services"
            / "operations_ui"
            / "templates"
        )
        environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        template = environment.get_template("trace.html")
        rendered = template.render(
            trace={
                "issue_id": "issue-1",
                "owner": "PatientTransport",
                "work_order": "TRN-123",
                "current_state": "CLOSED",
                "verification_status": "VERIFIED",
                "items": [
                    {
                        "stage": "VERIFIER",
                        "title": "Independent verification",
                        "status": "CLOSED",
                        "at": "2026-08-22T09:03:00+00:00",
                        "authority": "State Authority",
                        "actor": "ns-verifier@example",
                        "detail": "Verified evidence accepted.",
                        "identifiers": {
                            "evidence_id": "evidence-1",
                        },
                    }
                ],
            },
            error=None,
        )

        self.assertIn("Governed lifecycle trace", rendered)
        self.assertIn("Independent verification", rendered)
        self.assertIn("evidence_id = evidence-1", rendered)


if __name__ == "__main__":
    unittest.main()
