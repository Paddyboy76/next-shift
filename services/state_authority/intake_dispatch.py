from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import pubsub_v1


PROJECT_ID = "next-shift-506004"
HANDOVER_TOPIC = "next-shift-handover-received"
HANDOVER_EVENT_TYPE = "handover.issue.received"
HANDOVER_EVENT_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def publish_received(
    issue: dict[str, Any],
) -> dict[str, str]:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        PROJECT_ID,
        HANDOVER_TOPIC,
    )

    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": HANDOVER_EVENT_TYPE,
        "event_version": HANDOVER_EVENT_VERSION,
        "occurred_at": _now_iso(),
        "issue_id": issue["id"],
        "owner": issue["owner"],
        "state": issue["state"],
        "source_type": issue["source_type"],
        "source_reference": issue[
            "source_reference"
        ],
        "workflow_input": dict(
            issue.get(
                "workflow_input",
                {},
            )
        ),
    }

    future = publisher.publish(
        topic_path,
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8"),
        event_type=HANDOVER_EVENT_TYPE,
        event_version=HANDOVER_EVENT_VERSION,
        issue_id=issue["id"],
        owner=issue["owner"],
    )

    return {
        "event_id": event_id,
        "message_id": future.result(),
    }
