from __future__ import annotations

from typing import Any

from google.cloud import firestore


PROJECT_ID = "next-shift-506004"
HANDOVER_COLLECTION = "handover_issues"


def get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def create_issue_document(issue: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    doc_ref = db.collection(HANDOVER_COLLECTION).document()

    stored_issue = dict(issue)
    stored_issue["id"] = doc_ref.id

    doc_ref.set(stored_issue)

    return stored_issue


def update_issue_document(
    issue_id: str,
    updates: dict[str, Any],
) -> None:
    get_db().collection(HANDOVER_COLLECTION).document(issue_id).update(updates)


def get_issue_document(issue_id: str) -> dict[str, Any]:
    snapshot = (
        get_db()
        .collection(HANDOVER_COLLECTION)
        .document(issue_id)
        .get()
    )

    if not snapshot.exists:
        raise KeyError(f"Issue not found: {issue_id}")

    return snapshot.to_dict()


def get_issue_reference(issue_id: str):
    return get_db().collection(HANDOVER_COLLECTION).document(issue_id)


def new_transaction() -> firestore.Transaction:
    return get_db().transaction()
