from __future__ import annotations

import uuid
from typing import Any

from next_shift.domain.facilities import (
    find_facilities_team,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "facilities_worker"


def advance_facilities_issue(
    issue_id: str,
    *,
    facility_type: str,
    location: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "Facilities":
        raise ValueError(
            f"Facilities cannot process owner: "
            f"{issue['owner']}"
        )

    if not location.strip():
        raise ValueError(
            "Facilities location is required"
        )

    if issue["state"] == "RECEIVED":
        issue = transition_issue(
            issue_id=issue_id,
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "Facilities accepted the routed "
                "maintenance request."
            ),
        )

    if issue["state"] == "TRIAGED":
        team = find_facilities_team(
            facility_type
        )

        work_order_id = (
            f"FAC-{uuid.uuid4().hex[:8].upper()}"
        )

        assignment = {
            "facility_type": facility_type,
            "facilities_location": location,
            "facilities_work_order_id": work_order_id,
            "facilities_team_id": team["team_id"],
            "facilities_team_name": team["name"],
            "facilities_status": "ASSIGNED",
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
                f"Facilities work order {work_order_id} "
                f"assigned to {team['name']} "
                f"for {location}."
            ),
        )

    if issue["state"] == "ASSIGNED":
        update_issue_document(
            issue_id,
            {
                "facilities_status": "REPAIR_PENDING",
            },
        )

        issue["facilities_status"] = "REPAIR_PENDING"

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ACTION_PENDING",
            actor=WORKER_NAME,
            reason=(
                f"Facilities work order "
                f"{issue['facilities_work_order_id']} "
                f"is awaiting repair completion."
            ),
        )

    if issue["state"] == "ACTION_PENDING":
        return {
            "outcome": "ACTION_PENDING",
            "issue": issue,
        }

    raise ValueError(
        f"Facilities cannot resume issue from "
        f"state: {issue['state']}"
    )
