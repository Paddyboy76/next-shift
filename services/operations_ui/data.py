from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import (
    FieldFilter,
)


PROJECT_ID = "next-shift-506004"

ISSUES = "handover_issues"
EVIDENCE = "issue_evidence"
TRANSITIONS = "issue_transition_events"
SHIFTS = "shift_snapshots"


def _db() -> firestore.Client:
    return firestore.Client(
        project=PROJECT_ID
    )


def _serialize(
    value: Any,
) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _serialize(item)
            for item in value
        ]

    return value


def _time_key(
    item: dict[str, Any],
) -> str:
    value = (
        item.get("updated_at")
        or item.get("created_at")
        or item.get("committed_at")
        or ""
    )

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def list_issues(
    limit: int = 120,
) -> list[dict[str, Any]]:
    snapshots = (
        _db()
        .collection(ISSUES)
        .stream()
    )

    issues = [
        _serialize(snapshot.to_dict())
        for snapshot in snapshots
    ]

    issues.sort(
        key=_time_key,
        reverse=True,
    )

    return issues[:limit]


def get_issue_bundle(
    issue_id: str,
) -> dict[str, Any]:
    db = _db()

    snapshot = (
        db
        .collection(ISSUES)
        .document(issue_id)
        .get()
    )

    if not snapshot.exists:
        raise KeyError(
            f"Issue not found: {issue_id}"
        )

    issue = _serialize(
        snapshot.to_dict()
    )

    evidence = [
        _serialize(item.to_dict())
        for item in (
            db
            .collection(EVIDENCE)
            .where(
                filter=FieldFilter(
                    "issue_id",
                    "==",
                    issue_id,
                )
            )
            .stream()
        )
    ]

    transitions = [
        _serialize(item.to_dict())
        for item in (
            db
            .collection(TRANSITIONS)
            .where(
                filter=FieldFilter(
                    "issue_id",
                    "==",
                    issue_id,
                )
            )
            .stream()
        )
    ]

    evidence.sort(
        key=_time_key,
        reverse=True,
    )

    transitions.sort(
        key=_time_key,
        reverse=True,
    )

    return {
        "issue": issue,
        "evidence": evidence,
        "transitions": transitions,
    }


def list_shift_snapshots(
    limit: int = 20,
) -> list[dict[str, Any]]:
    snapshots = (
        _db()
        .collection(SHIFTS)
        .stream()
    )

    results = [
        _serialize(snapshot.to_dict())
        for snapshot in snapshots
    ]

    results.sort(
        key=_time_key,
        reverse=True,
    )

    return results[:limit]


def dashboard_summary() -> dict[str, Any]:
    issues = list_issues(
        limit=250
    )

    state_counts = Counter(
        issue.get(
            "state",
            "UNKNOWN",
        )
        for issue in issues
    )

    owner_counts = Counter(
        issue.get(
            "owner",
            "Unknown",
        )
        for issue in issues
    )

    terminal = {
        "CLOSED",
        "FAILED",
    }

    open_count = sum(
        count
        for state, count
        in state_counts.items()
        if state not in terminal
    )

    return {
        "total": len(issues),
        "open": open_count,
        "closed": state_counts.get(
            "CLOSED",
            0,
        ),
        "verifying": state_counts.get(
            "VERIFYING",
            0,
        ),
        "blocked": state_counts.get(
            "BLOCKED",
            0,
        ),
        "human_review": state_counts.get(
            "HUMAN_REVIEW",
            0,
        ),
        "states": dict(state_counts),
        "owners": dict(owner_counts),
    }
