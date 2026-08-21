import unittest
from pathlib import Path

from services.verifier_runtime.main import _matches


ROOT = Path(__file__).resolve().parents[1]
STATE_MAIN = ROOT / "services" / "state_authority" / "main.py"
STATE_EVIDENCE = ROOT / "services" / "state_authority" / "evidence.py"
STATE_POLICY = ROOT / "services" / "state_authority" / "policy.py"
EVIDENCE_RUNTIME = ROOT / "services" / "evidence_runtime" / "main.py"
VERIFIER_RUNTIME = ROOT / "services" / "verifier_runtime" / "main.py"
OPERATIONS_MAIN = ROOT / "services" / "operations_ui" / "main.py"
OPERATIONS_CLIENT = ROOT / "services" / "operations_ui" / "completion.py"
OPERATIONS_JS = ROOT / "services" / "operations_ui" / "static" / "app.js"
DEPLOY = ROOT / "deploy_verification_path.sh"


class FortifiedVerificationPathTests(unittest.TestCase):
    def test_state_authority_owns_evidence_and_closure(self) -> None:
        main = STATE_MAIN.read_text(encoding="utf-8")
        evidence = STATE_EVIDENCE.read_text(encoding="utf-8")

        self.assertIn(
            '@app.post(\n    "/v1/issues/<issue_id>/evidence"',
            main,
        )
        self.assertIn(
            '"/v1/issues/<issue_id>/verification-context"',
            main,
        )
        self.assertIn(
            '"/v1/issues/<issue_id>/verify"',
            main,
        )
        self.assertIn(
            '"state": "VERIFYING"',
            evidence,
        )
        self.assertIn(
            '"state": "CLOSED"',
            evidence,
        )
        self.assertIn(
            "issue_evidence",
            evidence,
        )
        self.assertIn(
            "issue_transition_events",
            evidence,
        )

    def test_evidence_and_verifier_have_separate_identities(self) -> None:
        policy = STATE_POLICY.read_text(encoding="utf-8")
        deploy = DEPLOY.read_text(encoding="utf-8")

        self.assertIn(
            '"ns-trusted-evidence@"',
            policy,
        )
        self.assertIn(
            '"evidence.record"',
            policy,
        )
        self.assertIn(
            '"ns-verifier@"',
            policy,
        )
        self.assertIn(
            '"verification.read"',
            policy,
        )
        self.assertIn(
            '"verification.close"',
            policy,
        )
        self.assertIn(
            'EVIDENCE_SA_NAME="ns-trusted-evidence"',
            deploy,
        )
        self.assertIn(
            'VERIFIER_SA_NAME="ns-verifier"',
            deploy,
        )

    def test_completion_runtimes_do_not_use_legacy_workflows(self) -> None:
        evidence_runtime = EVIDENCE_RUNTIME.read_text(
            encoding="utf-8"
        )
        verifier_runtime = VERIFIER_RUNTIME.read_text(
            encoding="utf-8"
        )

        for source in (evidence_runtime, verifier_runtime):
            self.assertNotIn(
                "next_shift.workflows",
                source,
            )
            self.assertNotIn(
                "google.cloud.firestore",
                source,
            )
            self.assertIn(
                "STATE_AUTHORITY_URL",
                source,
            )

    def test_operations_ui_exposes_two_step_completion(self) -> None:
        main = OPERATIONS_MAIN.read_text(encoding="utf-8")
        client = OPERATIONS_CLIENT.read_text(encoding="utf-8")
        app = OPERATIONS_JS.read_text(encoding="utf-8")

        self.assertIn(
            '@app.post("/api/issues/<issue_id>/complete")',
            main,
        )
        self.assertIn(
            '@app.post("/api/issues/<issue_id>/verify")',
            main,
        )
        self.assertIn(
            '"EVIDENCE_SERVICE_URL"',
            client,
        )
        self.assertIn(
            '"VERIFIER_SERVICE_URL"',
            client,
        )
        self.assertIn(
            "Record synthetic trusted evidence",
            app,
        )
        self.assertIn(
            "Run independent verifier",
            app,
        )

    def test_independent_verifier_matches_all_six_contracts(self) -> None:
        cases = [
            (
                {
                    "owner": "Facilities",
                    "facilities_work_order_id": "FAC-ABCDEF12",
                    "facilities_location": "Room 512",
                },
                {
                    "evidence_type": "facilities_repair_complete",
                    "source": "synthetic_facilities_system",
                    "subject": "FAC-ABCDEF12",
                    "details": {
                        "location": "Room 512",
                        "status": "REPAIRED",
                    },
                },
            ),
            (
                {
                    "owner": "AssetLogistics",
                    "assigned_asset_id": "WC-041",
                    "dispatch_destination": "Room 512",
                },
                {
                    "evidence_type": "asset_arrival",
                    "source": "synthetic_rtls",
                    "subject": "WC-041",
                    "details": {
                        "location": "Room 512",
                        "status": "PRESENT",
                    },
                },
            ),
            (
                {
                    "owner": "LanguageAccess",
                    "interpreter_booking_id": "LANG-12345678",
                    "interpreter_id": "INT-ESP-014",
                    "interpreter_service_location": "Room 512",
                },
                {
                    "evidence_type": "interpreter_attendance",
                    "source": "synthetic_language_service",
                    "subject": "LANG-12345678",
                    "details": {
                        "interpreter_id": "INT-ESP-014",
                        "service_location": "Room 512",
                        "status": "PRESENT",
                    },
                },
            ),
            (
                {
                    "owner": "DischargeDME",
                    "dme_order_id": "DME-12345678",
                    "dme_delivery_destination": "Discharge Lounge",
                },
                {
                    "evidence_type": "dme_delivery",
                    "source": "synthetic_dme_vendor",
                    "subject": "DME-12345678",
                    "details": {
                        "destination": "Discharge Lounge",
                        "status": "DELIVERED",
                    },
                },
            ),
            (
                {
                    "owner": "EVSThroughput",
                    "evs_cleaning_id": "EVS-12345678",
                    "evs_room": "Room 512",
                },
                {
                    "evidence_type": "evs_cleaning_complete",
                    "source": "synthetic_evs_system",
                    "subject": "EVS-12345678",
                    "details": {
                        "room": "Room 512",
                        "status": "CLEAN",
                        "completed_at": "2026-08-21T06:30:00+00:00",
                    },
                },
            ),
            (
                {
                    "owner": "PatientTransport",
                    "transport_request_id": "TRN-12345678",
                    "transport_destination": "Discharge Lounge",
                },
                {
                    "evidence_type": "transport_arrival",
                    "source": "synthetic_transport_system",
                    "subject": "TRN-12345678",
                    "details": {
                        "destination": "Discharge Lounge",
                        "status": "ARRIVED",
                    },
                },
            ),
        ]

        for issue, evidence in cases:
            with self.subTest(owner=issue["owner"]):
                self.assertTrue(
                    _matches(issue, evidence)
                )

    def test_verifier_rejects_mismatched_evidence(self) -> None:
        issue = {
            "owner": "AssetLogistics",
            "assigned_asset_id": "WC-041",
            "dispatch_destination": "Room 512",
        }
        evidence = {
            "evidence_type": "asset_arrival",
            "source": "synthetic_rtls",
            "subject": "WC-999",
            "details": {
                "location": "Room 512",
                "status": "PRESENT",
            },
        }

        self.assertFalse(
            _matches(issue, evidence)
        )


if __name__ == "__main__":
    unittest.main()
