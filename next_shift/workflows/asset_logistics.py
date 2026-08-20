from __future__ import annotations

from typing import Any

from next_shift.domain.assets import find_available_asset
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "asset_logistics_worker"


def triage_asset_issue(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"AssetLogistics cannot process owner: {issue['owner']}"
        )

    if issue["state"] != "RECEIVED":
        raise ValueError(
            f"Expected RECEIVED issue, got: {issue['state']}"
        )

    return transition_issue(
        issue_id=issue_id,
        new_state="TRIAGED",
        actor=WORKER_NAME,
        reason=(
            "AssetLogistics accepted the routed operational asset request."
        ),
    )


def locate_standard_wheelchair(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"AssetLogistics cannot process owner: {issue['owner']}"
        )

    if issue["state"] != "TRIAGED":
        raise ValueError(
            f"Expected TRIAGED issue, got: {issue['state']}"
        )

    asset = find_available_asset("standard_wheelchair")

    updated = transition_issue(
        issue_id=issue_id,
        new_state="ASSIGNED",
        actor=WORKER_NAME,
        reason=(
            f"Synthetic RTLS located available wheelchair "
            f"{asset['asset_id']} at {asset['location']}."
        ),
    )

    return {
        "issue": updated,
        "asset": asset,
    }


def advance_asset_issue(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "AssetLogistics":
        raise ValueError(
            f"AssetLogistics cannot process owner: {issue['owner']}"
        )

    if issue["state"] == "RECEIVED":
        issue = triage_asset_issue(issue_id)

    if issue["state"] == "TRIAGED":
        result = locate_standard_wheelchair(issue_id)

        return {
            "outcome": "ASSIGNED",
            "issue": result["issue"],
            "asset": result["asset"],
        }

    if issue["state"] == "ASSIGNED":
        return {
            "outcome": "ASSIGNED",
            "issue": issue,
            "asset": None,
        }

    raise ValueError(
        f"AssetLogistics cannot resume issue from state: {issue['state']}"
    )
