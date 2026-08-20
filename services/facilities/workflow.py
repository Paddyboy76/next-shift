from __future__ import annotations

import uuid
from typing import Any

from state_authority import transition_issue


FACILITY_TEAMS = {
    "plumbing": {
        "team_id": "FAC-PLUMB-01",
        "team_name": "Facilities Plumbing Team",
    },
    "air_conditioning": {
        "team_id": "FAC-HVAC-01",
        "team_name": "Facilities HVAC Team",
    },
    "electrical": {
        "team_id": "FAC-GEN-01",
        "team_name": (
            "Facilities General Maintenance"
        ),
    },
    "room_maintenance": {
        "team_id": "FAC-GEN-01",
        "team_name": (
            "Facilities General Maintenance"
        ),
    },
}


def _validated_location(
    value: Any,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            "Facilities location must be text"
        )

    location = value.strip()

    if (
        not location
        or len(location) > 200
    ):
        raise ValueError(
            "Invalid Facilities location"
        )

    return location


def process_facilities_issue(
    *,
    issue_id: str,
    facility_type: str,
    location: str,
) -> dict[str, Any]:
    if facility_type not in FACILITY_TEAMS:
        raise ValueError(
            f"Unsupported facility type: "
            f"{facility_type}"
        )

    location = _validated_location(
        location
    )

    team = FACILITY_TEAMS[
        facility_type
    ]

    transition_issue(
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "Facilities accepted the routed "
            "maintenance request."
        ),
        updates={},
    )

    work_order_id = (
        f"FAC-{uuid.uuid4().hex[:8].upper()}"
    )

    transition_issue(
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"Facilities work order "
            f"{work_order_id} assigned to "
            f"{team['team_name']} for "
            f"{location}."
        ),
        updates={
            "facility_type": facility_type,
            "facilities_location": location,
            "facilities_work_order_id": (
                work_order_id
            ),
            "facilities_team_id": (
                team["team_id"]
            ),
            "facilities_team_name": (
                team["team_name"]
            ),
            "facilities_status": "ASSIGNED",
        },
    )

    final = transition_issue(
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"Facilities work order "
            f"{work_order_id} is awaiting "
            "repair completion."
        ),
        updates={
            "facilities_status": (
                "REPAIR_PENDING"
            ),
        },
    )

    return {
        "issue_id": issue_id,
        "work_order_id": work_order_id,
        "state": final["to_state"],
    }
