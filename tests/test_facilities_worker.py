import json
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
    owner: str = "Facilities",
) -> dict[str, str]:
    return {
        "event_id": event_id,
        "event_type": "handover.issue.received",
        "event_version": "1.0",
        "occurred_at": "2026-08-20T00:00:00+00:00",
        "issue_id": issue_id,
        "owner": owner,
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
    @patch("workers.facilities_worker.advance_facilities_issue")
    def test_facilities_issue_uses_resumable_workflow(
        self,
        mock_advance: Mock,
    ) -> None:
        mock_advance.return_value = {"outcome": "ACTION_PENDING"}

        outcome = process_facilities_issue(
            "issue-001",
            facility_type="electrical",
            location="Floor 2 corridor",
        )

        self.assertEqual(outcome, "ACTION_PENDING")
        mock_advance.assert_called_once_with(
            "issue-001",
            facility_type="electrical",
            location="Floor 2 corridor",
        )


class FacilitiesCallbackTests(unittest.TestCase):
    @patch("workers.facilities_worker.record_processed_event")
    @patch("workers.facilities_worker.process_facilities_issue")
    @patch(
        "workers.facilities_worker.event_already_processed",
        return_value=True,
    )
    def test_duplicate_target_event_is_acked_without_processing(
        self,
        mock_already_processed: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
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
        message = FakeMessage(
            json.dumps(make_event()).encode("utf-8")
        )

        callback(message)

        mock_process.assert_called_once_with(
            "issue-001",
            facility_type="plumbing",
            location="Room 402",
        )

        mock_record.assert_called_once_with(
            event_id="event-001",
            message_id="message-001",
            issue_id="issue-001",
            outcome="TRIAGED",
            worker=WORKER_NAME,
        )

        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("workers.facilities_worker.record_processed_event")
    @patch("workers.facilities_worker.process_facilities_issue")
    @patch("workers.facilities_worker.event_already_processed")
    def test_event_for_other_worker_is_acked_without_claiming_it(
        self,
        mock_already_processed: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        message = FakeMessage(
            json.dumps(
                make_event(owner="AssetLogistics")
            ).encode("utf-8")
        )

        callback(message)

        mock_already_processed.assert_not_called()
        mock_process.assert_not_called()
        mock_record.assert_not_called()

        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch("workers.facilities_worker.record_processed_event")
    @patch("workers.facilities_worker.process_facilities_issue")
    def test_invalid_event_version_is_nacked(
        self,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        payload = make_event()
        payload["event_version"] = "999.0"

        message = FakeMessage(
            json.dumps(payload).encode("utf-8")
        )

        callback(message)

        mock_process.assert_not_called()
        mock_record.assert_not_called()

        message.nack.assert_called_once()
        message.ack.assert_not_called()

    @patch("workers.facilities_worker.record_processed_event")
    @patch("workers.facilities_worker.process_facilities_issue")
    def test_unknown_owner_is_nacked(
        self,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        message = FakeMessage(
            json.dumps(
                make_event(owner="RandomDepartment")
            ).encode("utf-8")
        )

        callback(message)

        mock_process.assert_not_called()
        mock_record.assert_not_called()

        message.nack.assert_called_once()
        message.ack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
