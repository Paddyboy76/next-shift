from __future__ import annotations

from typing import Any

from next_shift.persistence.evidence import (
    create_evidence,
    list_issue_evidence,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


TRUSTED_SOURCE = "synthetic_facilities_system"
VERIFIER_ACTOR = "independent_verifier"


def record_facilities_completion(
    *,
    issue_id: str,
    work_order_id: str,
    location: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "Facilities":
        raise ValueError(
            f"Cannot record Facilities evidence "
            f"for owner: {issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: "
            f"{issue['state']}"
        )

    if work_order_id != issue.get(
        "facilities_work_order_id"
    ):
        raise ValueError(
            "Facilities work order does not match"
        )

    if location != issue.get(
        "facilities_location"
    ):
        raise ValueError(
            "Facilities location does not match"
        )

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="facilities_repair_complete",
        source=TRUSTED_SOURCE,
        subject=work_order_id,
        details={
            "location": location,
            "status": "REPAIRED",
        },
    )

    update_issue_document(
        issue_id,
        {
            "facilities_status": "REPAIRED",
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_SOURCE,
        reason=(
            f"Trusted Facilities system reported "
            f"work order {work_order_id} repaired "
            f"at {location}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_facilities_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "Facilities":
        raise ValueError(
            f"Verifier cannot close owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: "
            f"{issue['state']}"
        )

    work_order_id = issue.get(
        "facilities_work_order_id"
    )
    location = issue.get(
        "facilities_location"
    )

    matching = None

    for evidence in list_issue_evidence(issue_id):
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type")
            == "facilities_repair_complete"
            and evidence.get("source")
            == TRUSTED_SOURCE
            and evidence.get("subject")
            == work_order_id
            and details.get("location")
            == location
            and details.get("status")
            == "REPAIRED"
        ):
            matching = evidence
            break

    if matching is None:
        raise ValueError(
            "Trusted Facilities completion evidence "
            "not found; issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted Facilities "
            f"evidence {matching['id']} confirming "
            f"repair at {location}."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching,
    }
