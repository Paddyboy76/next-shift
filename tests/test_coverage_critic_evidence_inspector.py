from __future__ import annotations

import unittest
from datetime import datetime, timezone

from services.evidence_inspector_runtime.main import inspection_reasons


class CoverageCriticEvidenceInspectorTests(unittest.TestCase):
    def _case(self):
        now = datetime.now(timezone.utc).isoformat()
        issue = {"id":"issue-1","owner":"PatientTransport","transport_request_id":"TRN-1","transport_destination":"Discharge Lounge"}
        evidence = {"id":"ev-1","issue_id":"issue-1","owner":"PatientTransport","evidence_type":"transport_arrival",
            "source":"synthetic_transport_system","subject":"TRN-1","details":{"destination":"Discharge Lounge","status":"ARRIVED"},
            "recorded_by":"ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com","created_at":now,
            "provenance":{"authority":"state_authority","issuer":"ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com",
                "integration":"synthetic_transport_system","observation_mode":"synthetic_external_system","workflow_state_observed":"ACTION_PENDING","observed_at":now}}
        return issue,evidence

    def test_independent_inspector_accepts_complete_provenance(self):
        issue,evidence=self._case()
        self.assertEqual(inspection_reasons(issue,evidence),["coverage_complete"])

    def test_independent_inspector_rejects_specialist_claim(self):
        issue,evidence=self._case(); evidence["recorded_by"]="ns-worker-patient-transport@next-shift-506004.iam.gserviceaccount.com"
        self.assertEqual(inspection_reasons(issue,evidence),["untrusted_evidence_provenance"])

    def test_independent_inspector_rejects_wrong_capability(self):
        issue,evidence=self._case(); evidence["subject"]="TRN-WRONG"
        self.assertEqual(inspection_reasons(issue,evidence),["wrong_capability_evidence"])
