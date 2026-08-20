from __future__ import annotations

from typing import Any

from next_shift.persistence.evidence import (
    create_evidence,
    list_issue_evidence,
)
from next_shift.persistence.firestore import update_issue_document
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


TRUSTED_SOURCE = "synthetic_dme_vendor"
VERIFIER_ACTOR = "independent_verifier"


def record_dme_delivery(
    *,
    issue_id: str,
    order_id: str,
    destination: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "DischargeDME":
        raise ValueError(
            f"Cannot record DME evidence for owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: "
            f"{issue['state']}"
        )

    if order_id != issue.get("dme_order_id"):
        raise ValueError(
            "DME delivery order does not match assigned order"
        )

    if destination != issue.get("dme_delivery_destination"):
        raise ValueError(
            "DME delivery destination does not match request"
        )

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="dme_delivery",
        source=TRUSTED_SOURCE,
        subject=order_id,
        details={
            "destination": destination,
            "status": "DELIVERED",
        },
    )

    update_issue_document(
        issue_id,
        {
            "dme_order_status": "DELIVERED",
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_SOURCE,
        reason=(
            f"Trusted DME vendor reported order {order_id} "
            f"delivered to {destination}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_dme_delivery_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "DischargeDME":
        raise ValueError(
            f"Verifier cannot close owner: {issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: {issue['state']}"
        )

    expected_order = issue.get("dme_order_id")
    expected_destination = issue.get(
        "dme_delivery_destination"
    )

    matching = None

    for evidence in list_issue_evidence(issue_id):
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type") == "dme_delivery"
            and evidence.get("source") == TRUSTED_SOURCE
            and evidence.get("subject") == expected_order
            and details.get("destination")
            == expected_destination
            and details.get("status") == "DELIVERED"
        ):
            matching = evidence
            break

    if matching is None:
        raise ValueError(
            "Trusted DME delivery evidence not found; "
            "issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted DME evidence "
            f"{matching['id']} confirming order "
            f"{expected_order} delivered."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching,
    }
