from __future__ import annotations

from typing import Any

from next_shift.domain.routing import (
    validate_operational_owner,
    worker_for_owner,
)
from next_shift.events.contracts import (
    validate_handover_received_event,
)


def route_handover_received_event(
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    Validate a handover event and resolve its deterministic worker route.

    This function does not mutate workflow state, publish another event,
    or call an LLM.
    """
    validate_handover_received_event(payload)

    owner = payload["owner"]

    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("Operational owner is required for routing")

    validate_operational_owner(owner)

    return {
        "issue_id": payload["issue_id"],
        "event_id": payload["event_id"],
        "owner": owner,
        "worker": worker_for_owner(owner),
    }
