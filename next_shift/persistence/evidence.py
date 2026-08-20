from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from next_shift.persistence.firestore import get_db


COLLECTION = "issue_evidence"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_evidence(
    *,
    issue_id: str,
    evidence_type: str,
    source: str,
    subject: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    doc_ref = get_db().collection(COLLECTION).document()

    evidence = {
        "id": doc_ref.id,
        "issue_id": issue_id,
        "evidence_type": evidence_type,
        "source": source,
        "subject": subject,
        "details": dict(details),
        "created_at": _now_iso(),
    }

    doc_ref.set(evidence)

    return evidence


def list_issue_evidence(
    issue_id: str,
) -> list[dict[str, Any]]:
    snapshots = (
        get_db()
        .collection(COLLECTION)
        .where("issue_id", "==", issue_id)
        .stream()
    )

    return [snapshot.to_dict() for snapshot in snapshots]
