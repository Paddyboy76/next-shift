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
from next_shift.workflows.asset_logistics import (
    triage_asset_issue,
)


PROJECT_ID = "next-shift-506004"
SUBSCRIPTION_ID = "next-shift-asset-logistics"
WORKER_NAME = "asset_logistics_worker"


def process_asset_logistics_issue(
    issue_id: str,
) -> str:
    triage_asset_issue(issue_id)
    return "TRIAGED"


def callback(
    message: pubsub_v1.subscriber.message.Message,
) -> None:
    print(
        f"RECEIVED message_id={message.message_id} "
        f"delivery_attempt={message.delivery_attempt}"
    )

    try:
        payload = json.loads(
            message.data.decode("utf-8")
        )

        route = route_handover_received_event(payload)

        event_id = route["event_id"]
        issue_id = route["issue_id"]

        if route["worker"] != WORKER_NAME:
            print(
                f"ACK_NOT_ROUTED event_id={event_id} "
                f"issue_id={issue_id} "
                f"target_worker={route['worker']}"
            )
            message.ack()
            return

        if event_already_processed(event_id):
            print(
                f"ACK_DUPLICATE event_id={event_id} "
                f"issue_id={issue_id}"
            )
            message.ack()
            return

        outcome = process_asset_logistics_issue(issue_id)

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
            f"outcome={outcome}"
        )

    except json.JSONDecodeError as exc:
        print(
            f"INVALID_JSON message_id={message.message_id}: {exc}",
            file=sys.stderr,
        )
        message.nack()

    except Exception as exc:
        print(
            f"PROCESSING_FAILED message_id={message.message_id}: "
            f"{exc}",
            file=sys.stderr,
        )
        traceback.print_exc()
        message.nack()


def main() -> None:
    subscriber = pubsub_v1.SubscriberClient()

    subscription_path = subscriber.subscription_path(
        PROJECT_ID,
        SUBSCRIPTION_ID,
    )

    print(f"Listening on {subscription_path}")

    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=callback,
    )

    try:
        streaming_pull_future.result()

    except KeyboardInterrupt:
        print("\nStopping AssetLogistics worker...")
        streaming_pull_future.cancel()
        streaming_pull_future.result()

    finally:
        subscriber.close()


if __name__ == "__main__":
    main()
