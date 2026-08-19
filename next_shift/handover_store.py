from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from next_shift.events import publish_handover_received


PROJECT_ID = "next-shift-506004"
COLLECTION = "handover_issues"

VALID_STATES = {
    "RECEIVED",
    "TRIAGED",
    "ASSIGNED",
    "ACTION_PENDING",
    "VERIFYING",
    "CLOSED",
    "BLOCKED",
    "HUMAN_REVIEW",
    "FAILED",
}

ALLOWED_TRANSITIONS = {
    "RECEIVED": {"TRIAGED", "HUMAN_REVIEW", "FAILED"},
    "TRIAGED": {"ASSIGNED", "HUMAN_REVIEW", "FAILED"},
    "ASSIGNED": {"ACTION_PENDING", "BLOCKED", "HUMAN_REVIEW", "FAILED"},
    "ACTION_PENDING": {"VERIFYING", "BLOCKED", "HUMAN_REVIEW", "FAILED"},
    "VERIFYING": {"CLOSED", "ACTION_PENDING", "BLOCKED", "HUMAN_REVIEW", "FAILED"},
    "BLOCKED": {"ASSIGNED", "ACTION_PENDING", "HUMAN_REVIEW", "FAILED"},
    "HUMAN_REVIEW": {"ASSIGNED", "ACTION_PENDING", "FAILED"},
    "FAILED": set(),
    "CLOSED": set(),
}


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_issue(
    *,
    title: str,
    description: str,
    source_type: str,
    source_reference: str,
    owner: str | None = None,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    db = _db()
    doc_ref = db.collection(COLLECTION).document()

    issue = {
        "id": doc_ref.id,
        "title": title,
        "description": description,
        "source_type": source_type,
        "source_reference": source_reference,
        "owner": owner,
        "human_approval_required": human_approval_required,
        "state": "RECEIVED",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "history": [
            {
                "from": None,
                "to": "RECEIVED",
                "at": _now_iso(),
                "actor": "system",
                "reason": "Issue created",
            }
        ],
    }

    doc_ref.set(issue)

    message_id = publish_handover_received(issue)

    issue["handover_received_message_id"] = message_id

    doc_ref.update(
        {
            "handover_received_message_id": message_id,
            "updated_at": _now_iso(),
        }
    )

    return issue


def get_issue(issue_id: str) -> dict[str, Any]:
    snapshot = _db().collection(COLLECTION).document(issue_id).get()

    if not snapshot.exists:
        raise KeyError(f"Issue not found: {issue_id}")

    return snapshot.to_dict()


def transition_issue(
    *,
    issue_id: str,
    new_state: str,
    actor: str,
    reason: str,
) -> dict[str, Any]:
    if new_state not in VALID_STATES:
        raise ValueError(f"Invalid state: {new_state}")

    db = _db()
    doc_ref = db.collection(COLLECTION).document(issue_id)

    @firestore.transactional
    def _transition(transaction: firestore.Transaction) -> dict[str, Any]:
        snapshot = doc_ref.get(transaction=transaction)

        if not snapshot.exists:
            raise KeyError(f"Issue not found: {issue_id}")

        issue = snapshot.to_dict()
        current_state = issue["state"]

        if new_state not in ALLOWED_TRANSITIONS[current_state]:
            raise ValueError(
                f"Invalid transition: {current_state} -> {new_state}"
            )

        history = list(issue.get("history", []))
        history.append(
            {
                "from": current_state,
                "to": new_state,
                "at": _now_iso(),
                "actor": actor,
                "reason": reason,
            }
        )

        updates = {
            "state": new_state,
            "updated_at": _now_iso(),
            "history": history,
        }

        transaction.update(doc_ref, updates)

        issue.update(updates)
        return issue

    transaction = db.transaction()
    return _transition(transaction)
