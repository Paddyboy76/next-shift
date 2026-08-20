import unittest
from unittest.mock import Mock, patch

from workers.facilities_worker import (
    WORKER_NAME,
    callback,
    process_facilities_issue,
)


def make_event(
    *,
    event_id: str = "event-001",
    issue_id: str = "issue-001",
) -> dict[str, str]:
    return {
        "event_id": event_id,
        "event_type": "handover.issue.received",
        "event_version": "1.0",
        "occurred_at": "2026-08-20T00:00:00+00:00",
        "issue_id": issue_id,
        "owner": "Facilities",
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-test-001",
    }


class FakeMessage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.message_id = "message-001"
        self.delivery_attempt = 1
        self.ack = Mock()
        self.nack = Mock()


class FacilitiesRoutingTests(unittest.TestCase):
    @patch("workers.facilities_worker.transition_issue")
    @patch("workers.facilities_worker.get_issue")
    def test_facilities_received_issue_is_triaged(
        self,
        mock_get_issue: Mock,
        mock_transition_issue: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-001",
            "owner": "Facilities",
            "state": "RECEIVED",
        }
        mock_transition_issue.return_value = {
            "id": "issue-001",
            "owner": "Facilities",
            "state": "TRIAGED",
        }

        outcome = process_facilities_issue("issue-001")

        self.assertEqual(outcome, "TRIAGED")

        mock_transition_issue.assert_called_once_with(
            issue_id="issue-001",
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "Versioned Pub/Sub handover event routed a newly received "
                "Facilities-owned issue to the Facilities workflow."
            ),
        )

    @patch("workers.facilities_worker.transition_issue")
    @patch("workers.facilities_worker.get_issue")
    def test_non_facilities_issue_is_skipped(
        self,
        mock_get_issue: Mock,
        mock_transition_issue: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-002",
            "owner": "Logistics",
            "state": "RECEIVED",
        }

        outcome = process_facilities_issue("issue-002")

        self.assertEqual(outcome, "SKIPPED_NON_FACILITIES")
        mock_transition_issue.assert_not_called()

    @patch("workers.facilities_worker.transition_issue")
    @patch("workers.facilities_worker.get_issue")
    def test_already_progressed_issue_is_not_mutated(
        self,
        mock_get_issue: Mock,
        mock_transition_issue: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-003",
            "owner": "Facilities",
            "state": "TRIAGED",
        }

        outcome = process_facilities_issue("issue-003")

        self.assertEqual(outcome, "SKIPPED_STATE_TRIAGED")
        mock_transition_issue.assert_not_called()


class FacilitiesCallbackTests(unittest.TestCase):
    @patch("workers.facilities_worker.record_processed_event")
    @patch("workers.facilities_worker.process_facilities_issue")
    @patch(
        "workers.facilities_worker.event_already_processed",
        return_value=True,
    )
    def test_duplicate_event_is_acked_without_processing(
        self,
        mock_already_processed: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        import json

        message = FakeMessage(
            json.dumps(make_event()).encode("utf-8")
        )

        callback(message)

        mock_already_processed.assert_called_once_with("event-001")
        mock_process.assert_not_called()
        mock_record.assert_not_called()
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    def test_invalid_json_is_nacked(self) -> None:
        message = FakeMessage(b"{not-json")

        callback(message)

        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch("workers.facilities_worker.record_processed_event")
    @patch(
        "workers.facilities_worker.process_facilities_issue",
        return_value="TRIAGED",
    )
    @patch(
        "workers.facilities_worker.event_already_processed",
        return_value=False,
    )
    def test_success_is_recorded_before_ack(
        self,
        mock_already_processed: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        import json

        message = FakeMessage(
            json.dumps(make_event()).encode("utf-8")
        )

        callback(message)

        mock_process.assert_called_once_with("issue-001")
        mock_record.assert_called_once_with(
            event_id="event-001",
            message_id="message-001",
            issue_id="issue-001",
            outcome="TRIAGED",
            worker=WORKER_NAME,
        )

        message.ack.assert_called_once()
        message.nack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
