from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from next_shift.persistence.continuity import (
    create_shift_snapshot_document,
    get_shift_snapshot_document,
    list_unresolved_issues,
)
from next_shift.workflows.handover import get_issue


TERMINAL_STATES = {"CLOSED", "FAILED"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_action(state: str) -> str:
    actions = {
        "RECEIVED": "Await specialist triage",
        "TRIAGED": "Await specialist assignment",
        "ASSIGNED": "Begin operational action",
        "ACTION_PENDING": "Await external completion evidence",
        "VERIFYING": "Await independent verification",
        "BLOCKED": "Resolve blocking dependency",
        "HUMAN_REVIEW": "Await authorized human decision",
    }

    return actions.get(
        state,
        "Review current operational state",
    )


def create_shift_handover(
    *,
    outgoing_shift: str,
    incoming_shift: str,
) -> dict[str, Any]:
    if not outgoing_shift.strip():
        raise ValueError("Outgoing shift is required")

    if not incoming_shift.strip():
        raise ValueError("Incoming shift is required")

    issues = list_unresolved_issues()
    created_at = _now_iso()

    issue_summaries = []

    for issue in issues:
        history = issue.get("history", [])
        last_event = history[-1] if history else None

        issue_summaries.append(
            {
                "issue_id": issue["id"],
                "title": issue.get("title"),
                "owner": issue.get("owner"),
                "state": issue.get("state"),
                "next_action": _next_action(
                    issue.get("state", "")
                ),
                "updated_at": issue.get("updated_at"),
                "last_event": last_event,
            }
        )

    owner_counts = Counter(
        issue.get("owner")
        for issue in issues
        if issue.get("owner")
    )

    snapshot = {
        "created_at": created_at,
        "outgoing_shift": outgoing_shift,
        "incoming_shift": incoming_shift,
        "unresolved_count": len(issue_summaries),
        "issues_by_owner": dict(owner_counts),
        "issues": issue_summaries,
    }

    return create_shift_snapshot_document(snapshot)


def resume_from_shift_handover(
    snapshot_id: str,
) -> dict[str, Any]:
    snapshot = get_shift_snapshot_document(
        snapshot_id
    )

    inherited = []
    still_open = []
    resolved_since_handover = []

    for captured in snapshot.get("issues", []):
        issue = get_issue(captured["issue_id"])

        current = {
            "issue_id": issue["id"],
            "title": issue.get("title"),
            "owner": issue.get("owner"),
            "snapshot_state": captured.get("state"),
            "current_state": issue.get("state"),
            "changed_since_handover": (
                captured.get("state")
                != issue.get("state")
            ),
            "next_action": _next_action(
                issue.get("state", "")
            ),
            "updated_at": issue.get("updated_at"),
        }

        inherited.append(current)

        if issue.get("state") in TERMINAL_STATES:
            resolved_since_handover.append(current)
        else:
            still_open.append(current)

    return {
        "snapshot_id": snapshot["id"],
        "outgoing_shift": snapshot["outgoing_shift"],
        "incoming_shift": snapshot["incoming_shift"],
        "snapshot_created_at": snapshot["created_at"],
        "captured_count": len(inherited),
        "still_open_count": len(still_open),
        "resolved_since_handover_count": len(
            resolved_since_handover
        ),
        "still_open": still_open,
        "resolved_since_handover": (
            resolved_since_handover
        ),
    }
