import unittest
from unittest.mock import Mock, patch

from next_shift.events.publisher import publish_handover_received
from next_shift.workflows.handover import create_issue


def make_issue(
    *,
    owner: str = "Facilities",
) -> dict[str, str]:
    return {
        "id": "issue-001",
        "owner": owner,
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-test-001",
    }


class PublisherRoutingTests(unittest.TestCase):
    @patch("next_shift.events.publisher.pubsub_v1.PublisherClient")
    def test_owner_is_published_as_message_attribute(
        self,
        mock_client_class: Mock,
    ) -> None:
        publisher = mock_client_class.return_value
        publisher.topic_path.return_value = (
            "projects/test/topics/test"
        )

        future = Mock()
        future.result.return_value = "message-001"
        publisher.publish.return_value = future

        result = publish_handover_received(
            make_issue(owner="AssetLogistics")
        )

        self.assertEqual(result["message_id"], "message-001")

        _, kwargs = publisher.publish.call_args

        self.assertEqual(
            kwargs["owner"],
            "AssetLogistics",
        )
        self.assertEqual(
            kwargs["event_type"],
            "handover.issue.received",
        )
        self.assertEqual(
            kwargs["event_version"],
            "1.0",
        )

    @patch("next_shift.events.publisher.pubsub_v1.PublisherClient")
    def test_unknown_owner_is_rejected_before_pubsub_client(
        self,
        mock_client_class: Mock,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported operational owner",
        ):
            publish_handover_received(
                make_issue(owner="WheelchairTeam")
            )

        mock_client_class.assert_not_called()


class IssueCreationOwnerTests(unittest.TestCase):
    @patch(
        "next_shift.workflows.handover.create_issue_document"
    )
    def test_missing_owner_is_rejected_before_firestore(
        self,
        mock_create_document: Mock,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Operational owner is required",
        ):
            create_issue(
                title="Test",
                description="Test",
                source_type="handover_note",
                source_reference="test-001",
                owner=None,
            )

        mock_create_document.assert_not_called()

    @patch(
        "next_shift.workflows.handover.create_issue_document"
    )
    def test_unknown_owner_is_rejected_before_firestore(
        self,
        mock_create_document: Mock,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported operational owner",
        ):
            create_issue(
                title="Test",
                description="Test",
                source_type="handover_note",
                source_reference="test-001",
                owner="WheelchairTeam",
            )

        mock_create_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
