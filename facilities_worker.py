from __future__ import annotations

import json
import sys
import traceback

from google.cloud import pubsub_v1

from next_shift.handover_store import get_issue, transition_issue


PROJECT_ID = "next-shift-506004"
SUBSCRIPTION_ID = "next-shift-handover-received-test"


def process_facilities_issue(issue_id: str) -> None:
    issue = get_issue(issue_id)

    if issue["owner"] != "Facilities":
        print(
            f"SKIP issue_id={issue_id} "
            f"owner={issue.get('owner')!r}"
        )
        return

    if issue["state"] != "RECEIVED":
        print(
            f"SKIP issue_id={issue_id} "
            f"state={issue.get('state')!r}"
        )
        return

    updated = transition_issue(
        issue_id=issue_id,
        new_state="TRIAGED",
        actor="facilities_worker",
        reason=(
            "Pub/Sub routed a newly received Facilities-owned issue "
            "to the Facilities specialist workflow."
        ),
    )

    print(
        f"TRIAGED issue_id={issue_id} "
        f"state={updated['state']}"
    )


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    print(
        f"RECEIVED message_id={message.message_id} "
        f"data={message.data!r}"
    )

    try:
        payload = json.loads(message.data.decode("utf-8"))

        issue_id = payload["issue_id"]
        owner = payload.get("owner")
        state = payload.get("state")

        if owner != "Facilities":
            print(
                f"ACK_NON_FACILITIES issue_id={issue_id} "
                f"owner={owner!r}"
            )
            message.ack()
            return

        if state != "RECEIVED":
            print(
                f"ACK_NON_RECEIVED issue_id={issue_id} "
                f"state={state!r}"
            )
            message.ack()
            return

        process_facilities_issue(issue_id)

        message.ack()

        print(
            f"ACK_SUCCESS message_id={message.message_id} "
            f"issue_id={issue_id}"
        )

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
        print("\nStopping Facilities worker...")
        streaming_pull_future.cancel()
        streaming_pull_future.result()
    finally:
        subscriber.close()


if __name__ == "__main__":
    main()
