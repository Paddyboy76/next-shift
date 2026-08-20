from __future__ import annotations

import json
import sys
import traceback

from google.cloud import pubsub_v1

from next_shift.events.routing import route_handover_received_event
from next_shift.persistence.processed_events import (
    event_already_processed,
    record_processed_event,
)
from next_shift.workflows.dme import advance_dme_issue


PROJECT_ID = "next-shift-506004"
SUBSCRIPTION_ID = "next-shift-discharge-dme"
WORKER_NAME = "discharge_dme_worker"


def process_dme_issue(
    issue_id: str,
    *,
    equipment_type: str,
    delivery_destination: str,
) -> str:
    result = advance_dme_issue(
        issue_id,
        equipment_type=equipment_type,
        delivery_destination=delivery_destination,
    )

    return result["outcome"]


def callback(
    message: pubsub_v1.subscriber.message.Message,
) -> None:
    print(
        f"RECEIVED message_id={message.message_id} "
        f"delivery_attempt={message.delivery_attempt}",
        flush=True,
    )

    try:
        payload = json.loads(
            message.data.decode("utf-8")
        )

        route = route_handover_received_event(payload)

        if route["worker"] != WORKER_NAME:
            message.ack()
            return

        event_id = route["event_id"]
        issue_id = route["issue_id"]

        if event_already_processed(event_id):
            message.ack()
            return

        issue_payload = payload.get("workflow_input", {})

        equipment_type = issue_payload.get(
            "equipment_type",
            "home_oxygen",
        )
        delivery_destination = issue_payload.get(
            "delivery_destination",
            "Patient Home",
        )

        outcome = process_dme_issue(
            issue_id,
            equipment_type=equipment_type,
            delivery_destination=delivery_destination,
        )

        record_processed_event(
            event_id=event_id,
            message_id=message.message_id,
            issue_id=issue_id,
            outcome=outcome,
            worker=WORKER_NAME,
        )

        message.ack()

        print(
            f"ACK_SUCCESS event_id={event_id} "
            f"issue_id={issue_id} "
            f"outcome={outcome}",
            flush=True,
        )

    except json.JSONDecodeError as exc:
        print(
            f"INVALID_JSON: {exc}",
            file=sys.stderr,
            flush=True,
        )
        message.nack()

    except Exception as exc:
        print(
            f"PROCESSING_FAILED: {exc}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc()
        message.nack()


def main() -> None:
    subscriber = pubsub_v1.SubscriberClient()

    subscription_path = subscriber.subscription_path(
        PROJECT_ID,
        SUBSCRIPTION_ID,
    )

    print(
        f"Listening on {subscription_path}",
        flush=True,
    )

    future = subscriber.subscribe(
        subscription_path,
        callback=callback,
    )

    try:
        future.result()

    except KeyboardInterrupt:
        future.cancel()
        future.result()

    finally:
        subscriber.close()


if __name__ == "__main__":
    main()
