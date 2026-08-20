from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from next_shift.persistence.firestore import get_db


ISSUE_COLLECTION = "handover_issues"
SHIFT_COLLECTION = "shift_snapshots"
TERMINAL_STATES = ["CLOSED", "FAILED"]


def list_unresolved_issues() -> list[dict[str, Any]]:
    snapshots = (
        get_db()
        .collection(ISSUE_COLLECTION)
        .where(
            filter=FieldFilter(
                "state",
                "not-in",
                TERMINAL_STATES,
            )
        )
        .stream()
    )

    issues = [snapshot.to_dict() for snapshot in snapshots]

    return sorted(
        issues,
        key=lambda issue: issue.get("updated_at", ""),
        reverse=True,
    )


def create_shift_snapshot_document(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    doc_ref = (
        get_db()
        .collection(SHIFT_COLLECTION)
        .document()
    )

    stored = dict(snapshot)
    stored["id"] = doc_ref.id

    doc_ref.set(stored)

    return stored


def get_shift_snapshot_document(
    snapshot_id: str,
) -> dict[str, Any]:
    snapshot = (
        get_db()
        .collection(SHIFT_COLLECTION)
        .document(snapshot_id)
        .get()
    )

    if not snapshot.exists:
        raise KeyError(
            f"Shift snapshot not found: {snapshot_id}"
        )

    return snapshot.to_dict()
