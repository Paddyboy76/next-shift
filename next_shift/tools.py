from __future__ import annotations

from typing import Any, Literal

from next_shift.handover_store import (
    create_issue,
    get_issue,
    transition_issue,
)


WorkflowState = Literal[
    "RECEIVED",
    "TRIAGED",
    "ASSIGNED",
    "ACTION_PENDING",
    "VERIFYING",
    "CLOSED",
    "BLOCKED",
    "HUMAN_REVIEW",
    "FAILED",
]


def create_handover_issue(
    title: str,
    description: str,
    source_type: str,
    source_reference: str,
    owner: str,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    """
    Create a new unresolved operational handover issue in Firestore.

    Use this when a concrete operational issue must be tracked across shifts.

    Args:
        title: Short operational issue title.
        description: Concise factual description.
        source_type: Source type such as handover_note, email, pdf, image,
            or voice_note.
        source_reference: Identifier linking the issue to its source.
        owner: Operational owner or department, if known.
        human_approval_required: Whether a human must approve the next action.

    Returns:
        The stored issue including its ID and workflow state.
    """
    return create_issue(
        title=title,
        description=description,
        source_type=source_type,
        source_reference=source_reference,
        owner=owner,
        human_approval_required=human_approval_required,
    )


def read_handover_issue(issue_id: str) -> dict[str, Any]:
    """
    Read one tracked operational issue from Firestore.

    Args:
        issue_id: Unique handover issue ID.

    Returns:
        The complete stored issue including state and history.
    """
    return get_issue(issue_id)


def advance_handover_issue(
    issue_id: str,
    new_state: WorkflowState,
    reason: str,
) -> dict[str, Any]:
    """
    Advance an issue through the controlled Next Shift workflow.

    Valid states are:
    RECEIVED, TRIAGED, ASSIGNED, ACTION_PENDING, VERIFYING, CLOSED,
    BLOCKED, HUMAN_REVIEW, FAILED.

    Never invent additional states.

    Args:
        issue_id: Unique handover issue ID.
        new_state: One valid Next Shift workflow state.
        reason: Evidence-based reason for the transition.

    Returns:
        A successful updated issue, or a structured rejection explaining why
        the requested transition was not permitted.
    """
    try:
        return {
            "ok": True,
            "issue": transition_issue(
                issue_id=issue_id,
                new_state=new_state,
                actor="next_shift",
                reason=reason,
            ),
        }
    except (ValueError, KeyError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "issue_id": issue_id,
            "requested_state": new_state,
        }
