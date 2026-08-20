from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import pubsub_v1

from next_shift.domain.routing import validate_operational_owner
from next_shift.events.contracts import (
    HANDOVER_RECEIVED_EVENT_TYPE,
    HANDOVER_RECEIVED_EVENT_VERSION,
)


PROJECT_ID = "next-shift-506004"
HANDOVER_RECEIVED_TOPIC = "next-shift-handover-received"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def publish_handover_received(
    issue: dict[str, Any],
) -> dict[str, str]:
    owner = issue.get("owner")

    if not isinstance(owner, str) or not owner.strip():
        raise ValueError(
            "Operational owner is required for publication"
        )

    validate_operational_owner(owner)

    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(
        PROJECT_ID,
        HANDOVER_RECEIVED_TOPIC,
    )

    event_id = str(uuid.uuid4())

    payload = {
        "event_id": event_id,
        "event_type": HANDOVER_RECEIVED_EVENT_TYPE,
        "event_version": HANDOVER_RECEIVED_EVENT_VERSION,
        "occurred_at": _now_iso(),
        "issue_id": issue["id"],
        "owner": owner,
        "state": issue["state"],
        "source_type": issue["source_type"],
        "source_reference": issue["source_reference"],
        "workflow_input": dict(
            issue.get("workflow_input", {})
        ),
    }

    future = publisher.publish(
        topic_path,
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8"),
        event_type=HANDOVER_RECEIVED_EVENT_TYPE,
        event_version=HANDOVER_RECEIVED_EVENT_VERSION,
        issue_id=issue["id"],
        owner=owner,
    )

    return {
        "event_id": event_id,
        "message_id": future.result(),
    }
