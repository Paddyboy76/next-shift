from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from next_shift.domain.routing import validate_operational_owner
from next_shift.domain.states import (
    ALLOWED_TRANSITIONS,
    VALID_STATES,
)
from next_shift.events.publisher import publish_handover_received
from next_shift.persistence.firestore import (
    create_issue_document,
    get_issue_document,
    get_issue_reference,
    new_transaction,
    update_issue_document,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_issue(
    *,
    title: str,
    description: str,
    source_type: str,
    source_reference: str,
    owner: str | None = None,
    workflow_input: dict[str, Any] | None = None,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("Operational owner is required")

    validate_operational_owner(owner)

    if workflow_input is None:
        workflow_input = {}

    if not isinstance(workflow_input, dict):
        raise ValueError("workflow_input must be a dictionary")

    now = _now_iso()

    issue = create_issue_document(
        {
            "title": title,
            "description": description,
            "source_type": source_type,
            "source_reference": source_reference,
            "owner": owner,
            "workflow_input": dict(workflow_input),
            "human_approval_required": human_approval_required,
            "state": "RECEIVED",
            "created_at": now,
            "updated_at": now,
            "history": [
                {
                    "from": None,
                    "to": "RECEIVED",
                    "at": now,
                    "actor": "system",
                    "reason": "Issue created",
                }
            ],
        }
    )

    event = publish_handover_received(issue)

    event_updates = {
        "handover_received_event_id": event["event_id"],
        "handover_received_message_id": event["message_id"],
        "updated_at": _now_iso(),
    }

    update_issue_document(
        issue["id"],
        event_updates,
    )

    issue.update(event_updates)

    return issue


def get_issue(issue_id: str) -> dict[str, Any]:
    return get_issue_document(issue_id)


def transition_issue(
    *,
    issue_id: str,
    new_state: str,
    actor: str,
    reason: str,
) -> dict[str, Any]:
    if new_state not in VALID_STATES:
        raise ValueError(f"Invalid state: {new_state}")

    doc_ref = get_issue_reference(issue_id)

    @firestore.transactional
    def _transition(
        transaction: firestore.Transaction,
    ) -> dict[str, Any]:
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
        now = _now_iso()

        history.append(
            {
                "from": current_state,
                "to": new_state,
                "at": now,
                "actor": actor,
                "reason": reason,
            }
        )

        updates = {
            "state": new_state,
            "updated_at": now,
            "history": history,
        }

        transaction.update(
            doc_ref,
            updates,
        )

        issue.update(updates)

        return issue

    return _transition(new_transaction())
