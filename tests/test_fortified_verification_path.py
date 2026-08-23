import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.verifier_runtime.main import _matches, _rejection_reason


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
    @staticmethod
    def _with_provenance(issue, evidence, *, observed_at=None):
        at = observed_at or datetime.now(timezone.utc).isoformat()
        issue = {"id": "issue-1", **issue}
        evidence = {
            "id": "evidence-1",
            "issue_id": "issue-1",
            "owner": issue["owner"],
            "schema_version": "1.0",
            "recorded_by": (
                "ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com"
            ),
            "created_at": at,
            **evidence,
        }
        evidence["provenance"] = {
            "authority": "state_authority",
            "issuer": evidence["recorded_by"],
            "integration": evidence["source"],
            "observation_mode": "synthetic_external_system",
            "observed_at": at,
            "workflow_state_observed": "ACTION_PENDING",
        }
        return issue, evidence

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
                issue, evidence = self._with_provenance(issue, evidence)
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
        issue, evidence = self._with_provenance(issue, evidence)

        self.assertFalse(
            _matches(issue, evidence)
        )
        self.assertEqual(
            _rejection_reason(issue, evidence),
            "wrong_capability_evidence",
        )

    def test_specialist_claim_or_missing_evidence_cannot_match(self) -> None:
        issue = {
            "id": "issue-1",
            "owner": "AssetLogistics",
            "assigned_asset_id": "WC-041",
            "dispatch_destination": "Room 512",
        }
        specialist_claim = {
            "issue_id": "issue-1",
            "owner": "AssetLogistics",
            "evidence_type": "asset_arrival",
            "source": "synthetic_rtls",
            "subject": "WC-041",
            "details": {"location": "Room 512", "status": "PRESENT"},
            "recorded_by": "ns-worker-asset-logistics@example",
        }
        self.assertFalse(_matches(issue, specialist_claim))
        self.assertEqual(
            _rejection_reason(issue, specialist_claim),
            "untrusted_evidence_provenance",
        )

    def test_stale_and_malformed_evidence_cannot_match(self) -> None:
        issue = {
            "owner": "Facilities",
            "facilities_work_order_id": "FAC-ABCDEF12",
            "facilities_location": "Room 512",
        }
        evidence = {
            "evidence_type": "facilities_repair_complete",
            "source": "synthetic_facilities_system",
            "subject": "FAC-ABCDEF12",
            "details": {"location": "Room 512", "status": "REPAIRED"},
        }
        stale_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        issue, stale = self._with_provenance(issue, evidence, observed_at=stale_at)
        self.assertEqual(_rejection_reason(issue, stale), "stale_evidence")

        malformed = dict(stale)
        malformed["created_at"] = "not-a-timestamp"
        self.assertEqual(_rejection_reason(issue, malformed), "malformed_evidence")

    def test_verification_rejection_is_authoritative_and_recoverable(self) -> None:
        state = STATE_EVIDENCE.read_text(encoding="utf-8")
        main = STATE_MAIN.read_text(encoding="utf-8")
        self.assertIn("verification_attempts", state)
        self.assertIn('"recoverable": True', state)
        self.assertIn('"recovery_state": "ACTION_PENDING"', state)
        self.assertIn('"from": "VERIFYING"', state)
        self.assertIn('"to": "ACTION_PENDING"', state)
        self.assertIn("verification-rejection", main)


if __name__ == "__main__":
    unittest.main()
