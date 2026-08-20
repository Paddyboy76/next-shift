from __future__ import annotations

import json
import sys
from typing import Any


def emit_security_event(
    *,
    decision: str,
    principal: str,
    capability: str,
    issue_id: str,
    target_owner: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    event = {
        "severity": (
            "WARNING"
            if decision == "DENY"
            else "INFO"
        ),
        "event_type": "authorization.decision",
        "decision": decision,
        "principal": principal,
        "capability": capability,
        "issue_id": issue_id,
        "target_owner": target_owner,
        "reason": reason,
        "details": details or {},
    }

    print(
        json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
        ),
        file=sys.stdout,
        flush=True,
    )
