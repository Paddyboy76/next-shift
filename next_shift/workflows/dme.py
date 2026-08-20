from __future__ import annotations

import uuid
from typing import Any

from next_shift.domain.dme import find_dme_provider
from next_shift.persistence.firestore import update_issue_document
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


WORKER_NAME = "discharge_dme_worker"


def advance_dme_issue(
    issue_id: str,
    *,
    equipment_type: str,
    delivery_destination: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "DischargeDME":
        raise ValueError(
            f"DischargeDME cannot process owner: {issue['owner']}"
        )

    if not delivery_destination.strip():
        raise ValueError("DME delivery destination is required")

    if issue["state"] == "RECEIVED":
        issue = transition_issue(
            issue_id=issue_id,
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "DischargeDME accepted the routed equipment "
                "coordination request."
            ),
        )

    if issue["state"] == "TRIAGED":
        provider = find_dme_provider(equipment_type)

        order_id = f"DME-{uuid.uuid4().hex[:8].upper()}"

        assignment = {
            "dme_equipment_type": equipment_type,
            "dme_provider_id": provider["provider_id"],
            "dme_provider_name": provider["name"],
            "dme_order_id": order_id,
            "dme_delivery_destination": delivery_destination,
            "dme_order_status": "ORDER_CREATED",
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
                f"DME order {order_id} assigned to "
                f"{provider['name']} for {equipment_type}."
            ),
        )

    if issue["state"] == "ASSIGNED":
        update_issue_document(
            issue_id,
            {
                "dme_order_status": "AWAITING_DELIVERY",
            },
        )

        issue["dme_order_status"] = "AWAITING_DELIVERY"

        issue = transition_issue(
            issue_id=issue_id,
            new_state="ACTION_PENDING",
            actor=WORKER_NAME,
            reason=(
                f"DME order {issue['dme_order_id']} is awaiting "
                f"delivery to {issue['dme_delivery_destination']}."
            ),
        )

    if issue["state"] == "ACTION_PENDING":
        return {
            "outcome": "ACTION_PENDING",
            "issue": issue,
        }

    raise ValueError(
        f"DischargeDME cannot resume issue from state: "
        f"{issue['state']}"
    )
