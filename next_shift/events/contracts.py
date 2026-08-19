from __future__ import annotations

from typing import Any


HANDOVER_RECEIVED_EVENT_TYPE = "handover.issue.received"
HANDOVER_RECEIVED_EVENT_VERSION = "1.0"


def validate_handover_received_event(
    payload: dict[str, Any],
) -> None:
    required = {
        "event_id",
        "event_type",
        "event_version",
        "occurred_at",
        "issue_id",
        "owner",
        "state",
        "source_type",
        "source_reference",
    }

    missing = sorted(required - payload.keys())

    if missing:
        raise ValueError(
            f"Missing required event fields: {', '.join(missing)}"
        )

    if payload["event_type"] != HANDOVER_RECEIVED_EVENT_TYPE:
        raise ValueError(
            f"Unsupported event_type: {payload['event_type']}"
        )

    if payload["event_version"] != HANDOVER_RECEIVED_EVENT_VERSION:
        raise ValueError(
            f"Unsupported event_version: {payload['event_version']}"
        )
