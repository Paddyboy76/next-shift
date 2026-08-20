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


TRUSTED_SOURCE = "synthetic_language_service"
VERIFIER_ACTOR = "independent_verifier"


def record_interpreter_attendance(
    *,
    issue_id: str,
    booking_id: str,
    interpreter_id: str,
    service_location: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "LanguageAccess":
        raise ValueError(
            f"Cannot record LanguageAccess evidence "
            f"for owner: {issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: "
            f"{issue['state']}"
        )

    if booking_id != issue.get(
        "interpreter_booking_id"
    ):
        raise ValueError(
            "Interpreter booking does not match"
        )

    if interpreter_id != issue.get(
        "interpreter_id"
    ):
        raise ValueError(
            "Interpreter identity does not match"
        )

    if service_location != issue.get(
        "interpreter_service_location"
    ):
        raise ValueError(
            "Interpreter location does not match"
        )

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="interpreter_attendance",
        source=TRUSTED_SOURCE,
        subject=booking_id,
        details={
            "interpreter_id": interpreter_id,
            "service_location": service_location,
            "status": "PRESENT",
        },
    )

    update_issue_document(
        issue_id,
        {
            "interpreter_status": "PRESENT",
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_SOURCE,
        reason=(
            f"Language service confirmed interpreter "
            f"{interpreter_id} present at "
            f"{service_location}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_interpreter_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "LanguageAccess":
        raise ValueError(
            f"Verifier cannot close owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: "
            f"{issue['state']}"
        )

    booking_id = issue.get(
        "interpreter_booking_id"
    )
    interpreter_id = issue.get(
        "interpreter_id"
    )
    service_location = issue.get(
        "interpreter_service_location"
    )

    matching = None

    for evidence in list_issue_evidence(issue_id):
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type")
            == "interpreter_attendance"
            and evidence.get("source")
            == TRUSTED_SOURCE
            and evidence.get("subject")
            == booking_id
            and details.get("interpreter_id")
            == interpreter_id
            and details.get("service_location")
            == service_location
            and details.get("status") == "PRESENT"
        ):
            matching = evidence
            break

    if matching is None:
        raise ValueError(
            "Trusted interpreter attendance evidence "
            "not found; issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted "
            f"LanguageAccess evidence "
            f"{matching['id']} confirming attendance."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching,
    }
