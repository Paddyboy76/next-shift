from __future__ import annotations

from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from human_reach import authorize_and_get_delivery as _authorize_and_get_delivery
from human_reach_contract import DELIVERY_COLLECTION


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def authorize_and_get_fresh_delivery(
    *,
    principal: str,
    delivery_id: str,
) -> dict[str, Any]:
    delivery = _authorize_and_get_delivery(
        principal=principal,
        delivery_id=delivery_id,
    )

    issue_id = delivery.get("issue_id")

    if not isinstance(issue_id, str) or not issue_id:
        return delivery

    db = _db()
    issue_snapshot = (
        db.collection(ISSUE_COLLECTION)
        .document(issue_id)
        .get()
    )

    if not issue_snapshot.exists:
        return delivery

    issue = issue_snapshot.to_dict() or {}
    current_state = str(issue.get("state") or "UNKNOWN")
    delivery["authoritative_issue_state"] = current_state
    delivery["authoritative_verification_status"] = issue.get("verification_status")
    delivery["authoritative_issue_updated_at"] = issue.get("updated_at")

    if delivery.get("delivery_status") != "PENDING" or current_state == "ACTION_PENDING":
        return delivery

    ref = (
        db.collection(DELIVERY_COLLECTION)
        .document(delivery_id)
    )
    updates = {
        "delivery_status": "CANCELLED",
        "cancelled_reason": "authoritative_issue_advanced",
        "cancelled_issue_state": current_state,
        "last_delivery_update_at": firestore.SERVER_TIMESTAMP,
    }
    ref.update(updates)
    delivery.update(updates)

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability="human_reach.delivery_update",
        issue_id=issue_id,
        target_owner=str(delivery.get("owner", "UNKNOWN")),
        reason="human_reach_stale_delivery_cancelled",
        details={
            "delivery_id": delivery_id,
            "current_issue_state": current_state,
        },
    )

    return delivery
