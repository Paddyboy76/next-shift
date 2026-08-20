from __future__ import annotations

import uuid
from typing import Any

from next_shift.domain.interpreters import (
    find_qualified_interpreter,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "language_access_worker"


def advance_language_access_issue(
    issue_id: str,
    *,
    language: str,
    service_location: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "LanguageAccess":
        raise ValueError(
            f"LanguageAccess cannot process owner: "
            f"{issue['owner']}"
        )

    if not service_location.strip():
        raise ValueError(
            "Interpreter service location is required"
        )

    if issue["state"] == "RECEIVED":
        issue = transition_issue(
            issue_id=issue_id,
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "LanguageAccess accepted the routed "
                "interpreter request."
            ),
        )

    if issue["state"] == "TRIAGED":
        interpreter = find_qualified_interpreter(
            language
        )

        booking_id = (
            f"LANG-{uuid.uuid4().hex[:8].upper()}"
        )

        assignment = {
            "language": language,
            "interpreter_id": (
                interpreter["interpreter_id"]
            ),
            "interpreter_name": interpreter["name"],
            "interpreter_booking_id": booking_id,
            "interpreter_slot": (
                interpreter["next_slot"]
            ),
            "interpreter_service_location": (
                service_location
            ),
            "interpreter_status": "BOOKED",
        }

        update_issue_document(
            issue_id,
            assignment,
        )

        issue.update(assignment)

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ASSIGNED",
            actor=WORKER_NAME,
            reason=(
                f"Qualified {language} interpreter "
                f"{interpreter['name']} booked for "
                f"{interpreter['next_slot']}."
            ),
        )

    if issue["state"] == "ASSIGNED":
        update_issue_document(
            issue_id,
            {
                "interpreter_status": (
                    "AWAITING_ATTENDANCE"
                ),
            },
        )

        issue["interpreter_status"] = (
            "AWAITING_ATTENDANCE"
        )

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ACTION_PENDING",
            actor=WORKER_NAME,
            reason=(
                f"Interpreter booking "
                f"{issue['interpreter_booking_id']} "
                f"is awaiting attendance at "
                f"{issue['interpreter_service_location']}."
            ),
        )

    if issue["state"] == "ACTION_PENDING":
        return {
            "outcome": "ACTION_PENDING",
            "issue": issue,
        }

    raise ValueError(
        f"LanguageAccess cannot resume issue from "
        f"state: {issue['state']}"
    )
