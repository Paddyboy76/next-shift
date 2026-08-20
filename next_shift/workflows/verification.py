from __future__ import annotations

from typing import Any

from next_shift.persistence.evidence import (
    create_evidence,
    list_issue_evidence,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


VERIFIER_ACTOR = "independent_verifier"
TRUSTED_ARRIVAL_SOURCE = "synthetic_rtls"


def record_asset_arrival(
    *,
    issue_id: str,
    asset_id: str,
    location: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"Cannot verify AssetLogistics evidence for owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: {issue['state']}"
        )

    expected_asset = issue.get("assigned_asset_id")
    expected_location = issue.get("dispatch_destination")

    if asset_id != expected_asset:
        raise ValueError(
            f"Arrival asset mismatch: expected {expected_asset}, "
            f"got {asset_id}"
        )

    if location != expected_location:
        raise ValueError(
            f"Arrival location mismatch: expected {expected_location}, "
            f"got {location}"
        )

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="asset_arrival",
        source=TRUSTED_ARRIVAL_SOURCE,
        subject=asset_id,
        details={
            "location": location,
            "status": "PRESENT",
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_ARRIVAL_SOURCE,
        reason=(
            f"Trusted RTLS evidence reported {asset_id} "
            f"present at {location}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_asset_arrival_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"Verifier cannot close owner: {issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: {issue['state']}"
        )

    expected_asset = issue.get("assigned_asset_id")
    expected_location = issue.get("dispatch_destination")

    evidence_records = list_issue_evidence(issue_id)

    matching_evidence = None

    for evidence in evidence_records:
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type") == "asset_arrival"
            and evidence.get("source") == TRUSTED_ARRIVAL_SOURCE
            and evidence.get("subject") == expected_asset
            and details.get("location") == expected_location
            and details.get("status") == "PRESENT"
        ):
            matching_evidence = evidence
            break

    if matching_evidence is None:
        raise ValueError(
            "Trusted asset arrival evidence not found; "
            "issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted evidence "
            f"{matching_evidence['id']} confirming "
            f"{expected_asset} at {expected_location}."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching_evidence,
    }
