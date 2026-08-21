from __future__ import annotations

import json
import os
import uuid
from typing import Any

from google.cloud import pubsub_v1

from human_reach_contract import DELIVERY_EVENT_TYPE
from human_reach_contract import DELIVERY_SCHEMA_VERSION


PROJECT_ID = "next-shift-506004"
DEFAULT_TOPIC = "next-shift-human-reach-requested"


def _topic_name() -> str:
    return os.environ.get(
        "HUMAN_REACH_TOPIC",
        DEFAULT_TOPIC,
    ).strip() or DEFAULT_TOPIC


def publish_delivery_request(
    delivery: dict[str, Any],
) -> dict[str, str]:
    event_id = str(uuid.uuid4())
    event = {
        "event_id": event_id,
        "event_type": DELIVERY_EVENT_TYPE,
        "schema_version": DELIVERY_SCHEMA_VERSION,
        "delivery_id": delivery["delivery_id"],
        "issue_id": delivery["issue_id"],
        "owner": delivery["owner"],
        "routing_key": delivery["routing_key"],
    }

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        PROJECT_ID,
        _topic_name(),
    )

    future = publisher.publish(
        topic_path,
        json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
        event_type=DELIVERY_EVENT_TYPE,
        schema_version=DELIVERY_SCHEMA_VERSION,
        owner=str(delivery["owner"]),
    )

    message_id = future.result(timeout=20)

    return {
        "event_id": event_id,
        "message_id": message_id,
    }
