from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RecoveryPlannerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.planner = load(
            "recovery_planner_main",
            ROOT / "services/recovery_planner_runtime/main.py",
        )
        cls.policy = load(
            "recovery_policy",
            ROOT / "services/state_authority/policy.py",
        )
        cls.trace = load(
            "recovery_trace",
            ROOT / "services/operations_ui/trace.py",
        )

    def test_verification_failure_requires_fresh_evidence(self) -> None:
        proposal = self.planner._proposal({
            "issue": {"state": "ACTION_PENDING", "history": [{}, {}]},
            "latest_verification_failure": {"reason": "stale_evidence"},
        })
        self.assertEqual(proposal["recommended_action"], "REQUEST_FRESH_EVIDENCE")
        self.assertEqual(proposal["failure_reason"], "stale_evidence")
        self.assertIn("independent verifier", proposal["recommendation"])
        self.assertTrue(proposal["historical_context"][0]["advisory_only"])

    def test_planner_cannot_mutate_or_close(self) -> None:
        planner = self.policy.PRINCIPAL_POLICIES[
            "ns-coverage-critic@next-shift-506004.iam.gserviceaccount.com"
        ]
        self.assertTrue({"recovery.read", "recovery.plan"}.issubset(planner.capabilities))
        self.assertNotIn("verification.close", planner.capabilities)
        self.assertNotIn("evidence.record", planner.capabilities)
        self.assertEqual(self.policy.CAPABILITY_POLICIES["recovery.plan"].transitions, {})

    def test_trace_exposes_sanction_and_authority_boundary(self) -> None:
        result = self.trace.build_lifecycle_trace({
            "issue": {"id": "issue-1", "owner": "Facilities", "state": "ACTION_PENDING"},
            "recovery_plans": [{
                "id": "plan-1", "status": "SANCTIONED", "state_observed": "ACTION_PENDING",
                "recommended_action": "REQUEST_FRESH_EVIDENCE", "failure_reason": "stale_evidence",
                "recommendation": "Request a fresh observation.",
                "authority_boundary": "ADVISORY_NO_STATE_MUTATION_NO_CLOSURE",
                "planner": "planner", "sanctioned_by": "operator", "sanctioned_at": "2026-08-23T00:00:00Z",
            }],
        })
        event = next(item for item in result["items"] if item["stage"] == "CONTROLLED_RECOVERY")
        self.assertEqual(event["status"], "SANCTIONED")
        self.assertIn("NO_STATE_MUTATION_NO_CLOSURE", event["detail"])


if __name__ == "__main__":
    unittest.main()
