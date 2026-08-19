from __future__ import annotations

import json
import time

from google.cloud import firestore
from google.cloud import pubsub_v1

from next_shift.events.contracts import (
    HANDOVER_RECEIVED_EVENT_TYPE,
    HANDOVER_RECEIVED_EVENT_VERSION,
)
from next_shift.workflows.handover import create_issue, get_issue


PROJECT_ID = "next-shift-506004"
TOPIC_ID = "next-shift-handover-received"


def wait_for_state(
    issue_id: str,
    expected_state: str,
    timeout_seconds: int = 30,
) -> dict:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        issue = get_issue(issue_id)

        if issue["state"] == expected_state:
            return issue

        time.sleep(1)

    raise RuntimeError(
        f"Issue {issue_id} did not reach {expected_state} "
        f"within {timeout_seconds} seconds"
    )


def processed_event_exists(event_id: str) -> bool:
    db = firestore.Client(project=PROJECT_ID)

    return (
        db.collection("processed_events")
        .document(event_id)
        .get()
        .exists
    )


def publish_payload(
    payload: dict,
) -> str:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    future = publisher.publish(
        topic_path,
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8"),
    )

    return future.result()


def main() -> None:
    print("===== 1. CREATE VALID ISSUE =====")

    issue = create_issue(
        title="Room 1211 air conditioner unresolved",
        description=(
            "Synthetic acceptance demo-008. "
            "Air conditioner remains broken and Facilities attendance "
            "has not been confirmed."
        ),
        source_type="handover_note",
        source_reference="synthetic-demo-008",
        owner="Facilities",
        human_approval_required=False,
    )

    issue_id = issue["id"]
    event_id = issue["handover_received_event_id"]

    print("issue_id:", issue_id)
    print("event_id:", event_id)
    print(
        "message_id:",
        issue["handover_received_message_id"],
    )
    print("initial_state:", issue["state"])

    print("\n===== 2. WAIT FOR ASYNC TRIAGE =====")

    triaged = wait_for_state(
        issue_id,
        "TRIAGED",
    )

    print("final_state:", triaged["state"])

    print("\n===== 3. VERIFY PROCESSED EVENT =====")

    if not processed_event_exists(event_id):
        raise RuntimeError(
            f"Processed-event record missing for {event_id}"
        )

    print("processed_event_record: PASS")

    print("\n===== 4. REPUBLISH EXACT DUPLICATE EVENT =====")

    duplicate_payload = {
        "event_id": event_id,
        "event_type": HANDOVER_RECEIVED_EVENT_TYPE,
        "event_version": HANDOVER_RECEIVED_EVENT_VERSION,
        "occurred_at": issue["created_at"],
        "issue_id": issue_id,
        "owner": issue["owner"],
        "state": "RECEIVED",
        "source_type": issue["source_type"],
        "source_reference": issue["source_reference"],
    }

    duplicate_message_id = publish_payload(
        duplicate_payload
    )

    print(
        "duplicate_message_id:",
        duplicate_message_id,
    )

    time.sleep(5)

    duplicate_check = get_issue(issue_id)

    if duplicate_check["state"] != "TRIAGED":
        raise RuntimeError(
            "Duplicate event changed workflow state unexpectedly"
        )

    print("duplicate_state_protection: PASS")

    print("\n===== 5. PUBLISH INVALID VERSION =====")

    bad_payload = {
        "event_id": "acceptance-invalid-version-001",
        "event_type": HANDOVER_RECEIVED_EVENT_TYPE,
        "event_version": "999.0",
        "occurred_at": issue["created_at"],
        "issue_id": issue_id,
        "owner": "Facilities",
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-invalid-event",
    }

    bad_message_id = publish_payload(
        bad_payload
    )

    print("bad_message_id:", bad_message_id)
    print(
        "Invalid event published. "
        "Worker should NACK it and Pub/Sub should retry it."
    )

    print("\n===== ACCEPTANCE RESULT =====")
    print("VALID_ASYNC_HANDOFF=PASS")
    print("IDEMPOTENCY=PASS")
    print("INVALID_EVENT_RETRY=STARTED")


if __name__ == "__main__":
    main()
