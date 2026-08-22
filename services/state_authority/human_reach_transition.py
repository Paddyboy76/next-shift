from __future__ import annotations

import json
import sys
from typing import Any

from human_reach import ensure_delivery_for_action_pending
from state import authorize_and_transition as _authorize_and_transition


def _emit_delivery_failure(
    *,
    issue_id: str,
    error: Exception,
) -> None:
    print(
        json.dumps(
            {
                "severity": "ERROR",
                "event_type": "human_reach.dispatch_failure",
                "issue_id": issue_id,
                "error_type": type(error).__name__,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        file=sys.stdout,
        flush=True,
    )


def authorize_and_transition(
    *,
    principal: str,
    issue_id: str,
    capability: str,
    expected_state: str,
    new_state: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    result = _authorize_and_transition(
        principal=principal,
        issue_id=issue_id,
        capability=capability,
        expected_state=expected_state,
        new_state=new_state,
        reason=reason,
        updates=updates,
    )

    if new_state != "ACTION_PENDING":
        return result

    try:
        human_reach = (
            ensure_delivery_for_action_pending(
                issue_id=issue_id,
            )
        )
    except Exception as exc:
        # The operational state transition has already committed. Human Reach
        # is intentionally a separately durable delivery concern; never
        # misreport the workflow transition as failed or cause a specialist
        # retry that could duplicate work. The failure remains visible and can
        # be reconciled safely because delivery IDs are issue IDs.
        _emit_delivery_failure(
            issue_id=issue_id,
            error=exc,
        )
        human_reach = {
            "delivery_id": issue_id,
            "event_dispatch_status": "FAILED",
            "error_type": type(exc).__name__,
        }

    return {
        **result,
        "human_reach": human_reach,
    }
