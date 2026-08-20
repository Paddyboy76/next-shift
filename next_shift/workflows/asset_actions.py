from __future__ import annotations

from typing import Any

from next_shift.domain.assets import find_available_asset
from next_shift.persistence.firestore import update_issue_document
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


ACTOR = "asset_logistics_worker"


def dispatch_assigned_wheelchair(
    issue_id: str,
    destination: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"AssetLogistics cannot process owner: {issue['owner']}"
        )

    if issue["state"] != "ASSIGNED":
        raise ValueError(
            f"Expected ASSIGNED issue, got: {issue['state']}"
        )

    if not destination.strip():
        raise ValueError("Dispatch destination is required")

    asset = find_available_asset("standard_wheelchair")

    updated = transition_issue(
        issue_id=issue_id,
        new_state="ACTION_PENDING",
        actor=ACTOR,
        reason=(
            f"Dispatch requested for {asset['asset_id']} "
            f"from {asset['location']} to {destination}."
        ),
    )

    dispatch = {
        "assigned_asset_id": asset["asset_id"],
        "assigned_asset_type": asset["asset_type"],
        "assigned_asset_origin": asset["location"],
        "dispatch_destination": destination,
        "dispatch_status": "IN_TRANSIT",
    }

    update_issue_document(
        issue_id,
        dispatch,
    )

    updated.update(dispatch)

    return updated
