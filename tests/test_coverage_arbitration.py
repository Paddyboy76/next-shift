from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "services" / "operations_ui"),
)

from coverage_arbitration import arbitrate_coverage


MESSY_HUMAN_HANDOVER = (
    "The meeting room on the 7th floor has a leaking aircon. "
    "The kitchen on the 8th floor has the floor covered in water "
    "from a leaking thing in the cupboard it looks like"
)


def _proposal(title: str) -> dict[str, object]:
    return {
        "owner": "Facilities",
        "title": title,
        "description": title,
        "human_approval_required": False,
        "workflow_input": {
            "facility_type": "room_maintenance",
            "location": "synthetic location",
        },
    }


def test_uncertainty_does_not_veto_safe_human_handover_work():
    proposals = [
        _proposal("Leaking air conditioning on 7th floor"),
        _proposal("Water leak source unknown in 8th floor kitchen"),
    ]
    review = {
        "decision": "REVIEW_REQUIRED",
        "summary": "One component is not identified precisely.",
        "findings": [
            {
                "type": "UNCERTAIN",
                "detail": "Exact source inside the cupboard is unknown.",
                "proposal_indexes": [1],
                "suggested_owner": "Facilities",
            }
        ],
    }

    result = arbitrate_coverage(proposals, review)

    assert MESSY_HUMAN_HANDOVER
    assert result["dispatchable"] == proposals
    assert result["held"] == []
    assert result["review_required"] is True


def test_misrouted_item_is_held_without_suppressing_unrelated_work():
    proposals = [
        _proposal("Valid Facilities work"),
        _proposal("Disputed second proposal"),
    ]
    review = {
        "decision": "REVIEW_REQUIRED",
        "findings": [
            {
                "type": "MISROUTED",
                "detail": "Second proposal needs a different owner.",
                "proposal_indexes": [1],
                "suggested_owner": "AssetLogistics",
            }
        ],
    }

    result = arbitrate_coverage(proposals, review)

    assert result["dispatchable"] == [proposals[0]]
    assert result["held"] == [proposals[1]]
    assert result["review_required"] is True
    assert result["unbounded_review"] is False


def test_unscoped_blocking_finding_fails_safe():
    proposals = [_proposal("One"), _proposal("Two")]
    review = {
        "decision": "REVIEW_REQUIRED",
        "findings": [
            {
                "type": "CONFLATED",
                "detail": "Unable to identify which proposal is affected.",
                "proposal_indexes": [],
                "suggested_owner": None,
            }
        ],
    }

    result = arbitrate_coverage(proposals, review)

    assert result["dispatchable"] == []
    assert result["held"] == proposals
    assert result["unbounded_review"] is True
