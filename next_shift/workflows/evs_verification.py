from __future__ import annotations

from datetime import datetime, timezone
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


TRUSTED_SOURCE = "synthetic_evs_system"
VERIFIER_ACTOR = "independent_verifier"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_evs_completion(
    *,
    issue_id: str,
    cleaning_id: str,
    room: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "EVSThroughput":
        raise ValueError(
            f"Cannot record EVS evidence for owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: "
            f"{issue['state']}"
        )

    if cleaning_id != issue.get("evs_cleaning_id"):
        raise ValueError(
            "EVS cleaning ID does not match"
        )

    if room != issue.get("evs_room"):
        raise ValueError(
            "EVS room does not match"
        )

    completed_at = _now_iso()

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="evs_cleaning_complete",
        source=TRUSTED_SOURCE,
        subject=cleaning_id,
        details={
            "room": room,
            "status": "CLEAN",
            "completed_at": completed_at,
        },
    )

    update_issue_document(
        issue_id,
        {
            "evs_status": "CLEAN",
            "evs_completed_at": completed_at,
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_SOURCE,
        reason=(
            f"Trusted EVS system reported {room} "
            f"clean under request {cleaning_id}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_evs_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "EVSThroughput":
        raise ValueError(
            f"Verifier cannot close owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: "
            f"{issue['state']}"
        )

    cleaning_id = issue.get("evs_cleaning_id")
    room = issue.get("evs_room")

    matching = None

    for evidence in list_issue_evidence(issue_id):
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type")
            == "evs_cleaning_complete"
            and evidence.get("source")
            == TRUSTED_SOURCE
            and evidence.get("subject")
            == cleaning_id
            and details.get("room") == room
            and details.get("status") == "CLEAN"
        ):
            matching = evidence
            break

    if matching is None:
        raise ValueError(
            "Trusted EVS completion evidence not found; "
            "issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted EVS "
            f"evidence {matching['id']} confirming "
            f"{room} is clean."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching,
    }
