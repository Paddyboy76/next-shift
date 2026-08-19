from __future__ import annotations

import json
from typing import Any

from google.cloud import pubsub_v1


PROJECT_ID = "next-shift-506004"
TOPIC_ID = "next-shift-handover-received"


def publish_handover_received(issue: dict[str, Any]) -> str:
    """
    Publish safe routing metadata for a newly created handover issue.

    Returns:
        The Pub/Sub message ID.
    """
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    payload = {
        "issue_id": issue["id"],
        "owner": issue.get("owner"),
        "state": issue["state"],
        "source_type": issue["source_type"],
        "source_reference": issue["source_reference"],
    }

    future = publisher.publish(
        topic_path,
        json.dumps(payload).encode("utf-8"),
    )

    return future.result()
