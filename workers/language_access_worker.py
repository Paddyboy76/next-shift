from __future__ import annotations

import json
import sys
import traceback

from google.cloud import pubsub_v1

from next_shift.events.routing import (
    route_handover_received_event,
)
from next_shift.persistence.processed_events import (
    event_already_processed,
    record_processed_event,
)
from next_shift.workflows.language_access import (
    advance_language_access_issue,
)


PROJECT_ID = "next-shift-506004"
SUBSCRIPTION_ID = "next-shift-language-access"
WORKER_NAME = "language_access_worker"


def process_language_access_issue(
    issue_id: str,
    *,
    language: str,
    service_location: str,
) -> str:
    result = advance_language_access_issue(
        issue_id,
        language=language,
        service_location=service_location,
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

        route = route_handover_received_event(
            payload
        )

        if route["worker"] != WORKER_NAME:
            message.ack()
            return

        event_id = route["event_id"]
        issue_id = route["issue_id"]

        if event_already_processed(event_id):
            message.ack()
            return

        workflow_input = payload.get(
            "workflow_input",
            {},
        )

        language = workflow_input.get(
            "language",
            "Spanish",
        )

        service_location = workflow_input.get(
            "service_location",
            "Room 402",
        )

        outcome = process_language_access_issue(
            issue_id,
            language=language,
            service_location=service_location,
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
