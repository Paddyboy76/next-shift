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
    workflow_input: dict[str, Any] | None = None,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    """
    Create one unresolved non-clinical operational issue.

    Call this tool once for every distinct operational issue found in a
    handover. A single handover may therefore require multiple tool calls.

    Valid owners:
    - Facilities
    - AssetLogistics
    - LanguageAccess
    - DischargeDME
    - EVSThroughput

    workflow_input contains structured specialist-specific routing data.

    Examples:

    AssetLogistics:
        {}

    LanguageAccess:
        {
            "language": "Spanish",
            "service_location": "Room 402"
        }

    DischargeDME:
        {
            "equipment_type": "home_oxygen",
            "delivery_destination": "Patient Home"
        }

    EVSThroughput:
        {
            "room": "Room 402",
            "zone": "North Tower"
        }

    Facilities:
        {}

    Never use this tool for clinical orders, medication requests,
    diagnosis, treatment, triage, or other licensed clinical decisions.
    """
    return create_issue(
        title=title,
        description=description,
        source_type=source_type,
        source_reference=source_reference,
        owner=owner,
        workflow_input=workflow_input,
        human_approval_required=human_approval_required,
    )


def read_handover_issue(
    issue_id: str,
) -> dict[str, Any]:
    """
    Read one tracked operational issue.
    """
    return get_issue(issue_id)


def advance_handover_issue(
    issue_id: str,
    new_state: WorkflowState,
    reason: str,
) -> dict[str, Any]:
    """
    Advance an issue through the controlled Next Shift workflow.

    This capability is not exposed to the intake agent.
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
