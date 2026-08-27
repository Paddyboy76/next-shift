from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "services" / "state_authority"),
)

from critique import _validate_decision_findings
from security import AuthorizationError


def test_pass_may_preserve_advisory_uncertainty():
    _validate_decision_findings(
        "PASS",
        [
            {
                "type": "UNCERTAIN",
                "detail": "Exact failed component is unknown but Facilities can inspect safely.",
                "proposal_indexes": [1],
                "suggested_owner": "Facilities",
            }
        ],
    )


def test_pass_rejects_blocking_coverage_findings():
    with pytest.raises(AuthorizationError):
        _validate_decision_findings(
            "PASS",
            [
                {
                    "type": "MISROUTED",
                    "detail": "Proposal would go to the wrong specialist.",
                    "proposal_indexes": [0],
                    "suggested_owner": "AssetLogistics",
                }
            ],
        )


def test_review_required_still_needs_a_real_finding():
    with pytest.raises(AuthorizationError):
        _validate_decision_findings("REVIEW_REQUIRED", [])
