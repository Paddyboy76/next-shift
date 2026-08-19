from __future__ import annotations

from datetime import datetime, timezone

from next_shift.persistence.firestore import get_db


COLLECTION = "processed_events"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_already_processed(event_id: str) -> bool:
    snapshot = (
        get_db()
        .collection(COLLECTION)
        .document(event_id)
        .get()
    )

    return snapshot.exists


def record_processed_event(
    *,
    event_id: str,
    message_id: str,
    issue_id: str,
    outcome: str,
    worker: str,
) -> None:
    get_db().collection(COLLECTION).document(event_id).set(
        {
            "event_id": event_id,
            "message_id": message_id,
            "issue_id": issue_id,
            "outcome": outcome,
            "worker": worker,
            "processed_at": _now_iso(),
        }
    )
