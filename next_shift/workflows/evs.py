from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from next_shift.domain.evs import (
    DEFAULT_TURNAROUND_TARGET_MINUTES,
    find_available_evs_team,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "evs_throughput_worker"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def advance_evs_issue(
    issue_id: str,
    *,
    room: str,
    zone: str,
    target_minutes: int = DEFAULT_TURNAROUND_TARGET_MINUTES,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "EVSThroughput":
        raise ValueError(
            f"EVSThroughput cannot process owner: "
            f"{issue['owner']}"
        )

    if not room.strip():
        raise ValueError("Room is required")

    if target_minutes <= 0:
        raise ValueError(
            "Turnaround target must be positive"
        )

    if issue["state"] == "RECEIVED":
        issue = transition_issue(
            issue_id=issue_id,
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "EVSThroughput accepted the routed "
                "bed-turnaround request."
            ),
        )

    if issue["state"] == "TRIAGED":
        team = find_available_evs_team(zone)

        cleaning_id = (
            f"EVS-{uuid.uuid4().hex[:8].upper()}"
        )

        assignment = {
            "evs_cleaning_id": cleaning_id,
            "evs_team_id": team["team_id"],
            "evs_team_name": team["name"],
            "evs_room": room,
            "evs_zone": zone,
            "evs_target_minutes": target_minutes,
            "evs_status": "ASSIGNED",
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
                f"Cleaning request {cleaning_id} assigned "
                f"to {team['name']} for {room}."
            ),
        )

    if issue["state"] == "ASSIGNED":
        started_at = _now_iso()

        update_issue_document(
            issue_id,
            {
                "evs_status": "CLEANING_PENDING",
                "evs_started_at": started_at,
            },
        )

        issue["evs_status"] = "CLEANING_PENDING"
        issue["evs_started_at"] = started_at

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ACTION_PENDING",
            actor=WORKER_NAME,
            reason=(
                f"EVS turnaround clock started for "
                f"{issue['evs_room']} with target "
                f"{issue['evs_target_minutes']} minutes."
            ),
        )

    if issue["state"] == "ACTION_PENDING":
        return {
            "outcome": "ACTION_PENDING",
            "issue": issue,
        }

    raise ValueError(
        f"EVSThroughput cannot resume issue from "
        f"state: {issue['state']}"
    )
