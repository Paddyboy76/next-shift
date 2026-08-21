from __future__ import annotations

from typing import Any

from next_shift.domain.routing import validate_operational_owner


def create_handover_issue(
    title: str,
    description: str,
    owner: str,
    workflow_input: dict[str, Any] | None = None,
    human_approval_required: bool = False,
) -> dict[str, Any]:
    """
    Propose one unresolved non-clinical operational issue.

    This tool is intentionally side-effect free. It does not write
    Firestore, publish Pub/Sub, or mutate workflow state. The trusted
    ingress persists validated proposals through State Authority.

    Valid owners:
    - Facilities
    - AssetLogistics
    - LanguageAccess
    - DischargeDME
    - EVSThroughput
    - PatientTransport

    workflow_input contains specialist-specific data.

    PatientTransport example:
        {
            "origin": "Room 402",
            "destination": "Discharge Lounge",
            "transport_type": "wheelchair"
        }

    Never use this tool for clinical orders, medication requests,
    diagnosis, treatment, triage, or licensed clinical decisions.
    """
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Issue title is required")

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Issue description is required")

    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("Operational owner is required")

    validate_operational_owner(owner)

    if workflow_input is None:
        workflow_input = {}

    if not isinstance(workflow_input, dict):
        raise ValueError("workflow_input must be a dictionary")

    if not isinstance(human_approval_required, bool):
        raise ValueError("human_approval_required must be a boolean")

    return {
        "proposal_type": "handover_issue",
        "proposal": {
            "title": title.strip(),
            "description": description.strip(),
            "owner": owner.strip(),
            "workflow_input": dict(workflow_input),
            "human_approval_required": human_approval_required,
        },
    }


def read_handover_issue(
    issue_id: str,
) -> dict[str, Any]:
    """Legacy local read helper; not exposed to the intake agent."""
    from next_shift.workflows.handover import get_issue

    return get_issue(issue_id)


def advance_handover_issue(
    issue_id: str,
    new_state: str,
    reason: str,
) -> dict[str, Any]:
    """Legacy local transition helper; not exposed to the intake agent."""
    from next_shift.workflows.handover import transition_issue

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
