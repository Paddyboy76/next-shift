from __future__ import annotations

import uuid
from typing import Any

from next_shift.domain.transport import (
    find_available_transporter,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "patient_transport_worker"


def advance_transport_issue(
    issue_id: str,
    *,
    origin: str,
    destination: str,
    transport_type: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "PatientTransport":
        raise ValueError(
            f"PatientTransport cannot process owner: "
            f"{issue['owner']}"
        )

    if not origin.strip():
        raise ValueError("Transport origin is required")

    if not destination.strip():
        raise ValueError(
            "Transport destination is required"
        )

    if issue["state"] == "RECEIVED":
        issue = transition_issue(
            issue_id=issue_id,
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "PatientTransport accepted the routed "
                "transport request."
            ),
        )

    if issue["state"] == "TRIAGED":
        transporter = find_available_transporter(
            transport_type
        )

        transport_id = (
            f"TRN-{uuid.uuid4().hex[:8].upper()}"
        )

        assignment = {
            "transport_request_id": transport_id,
            "transport_type": transport_type,
            "transport_origin": origin,
            "transport_destination": destination,
            "transporter_id": (
                transporter["transporter_id"]
            ),
            "transporter_name": transporter["name"],
            "transport_status": "ASSIGNED",
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
                f"Transport request {transport_id} assigned "
                f"to {transporter['name']} from {origin} "
                f"to {destination}."
            ),
        )

    if issue["state"] == "ASSIGNED":
        update_issue_document(
            issue_id,
            {
                "transport_status": "AWAITING_PICKUP",
            },
        )

        issue["transport_status"] = "AWAITING_PICKUP"

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ACTION_PENDING",
            actor=WORKER_NAME,
            reason=(
                f"Transport request "
                f"{issue['transport_request_id']} is "
                f"awaiting pickup at "
                f"{issue['transport_origin']}."
            ),
        )

    if issue["state"] == "ACTION_PENDING":
        return {
            "outcome": "ACTION_PENDING",
            "issue": issue,
        }

    raise ValueError(
        f"PatientTransport cannot resume issue from "
        f"state: {issue['state']}"
    )
