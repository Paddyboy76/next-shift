from __future__ import annotations

from typing import Any

from next_shift.domain.states import WorkflowState
from next_shift.workflows.handover import (
    create_issue,
    get_issue,
    transition_issue,
)


def create_handover_issue(
    title: str,
    description: str,
    source_type: str,
    source_reference: str,
    owner: str,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    """
    Create a new unresolved operational handover issue.

    Args:
        title: Short operational issue title.
        description: Concise factual description.
        source_type: Source such as handover_note, email, pdf, image,
            or voice_note.
        source_reference: Identifier linking the issue to its source.
        owner: Operational owner or department.
        human_approval_required: Whether human approval is required.

    Returns:
        Stored issue including ID and workflow state.
    """
    return create_issue(
        title=title,
        description=description,
        source_type=source_type,
        source_reference=source_reference,
        owner=owner,
        human_approval_required=human_approval_required,
    )


def read_handover_issue(
    issue_id: str,
) -> dict[str, Any]:
    """
    Read one tracked operational issue.

    Args:
        issue_id: Unique handover issue ID.

    Returns:
        Complete stored issue.
    """
    return get_issue(issue_id)


def advance_handover_issue(
    issue_id: str,
    new_state: WorkflowState,
    reason: str,
) -> dict[str, Any]:
    """
    Advance an issue through the controlled Next Shift workflow.

    Args:
        issue_id: Unique handover issue ID.
        new_state: Valid Next Shift workflow state.
        reason: Evidence-based reason for the transition.

    Returns:
        Successful updated issue or structured rejection.
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
