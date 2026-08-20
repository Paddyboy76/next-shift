import json
import unittest
from unittest.mock import Mock, patch

from next_shift.domain.assets import find_available_asset
from next_shift.workflows.asset_logistics import (
    advance_asset_issue,
    locate_standard_wheelchair,
    triage_asset_issue,
)
from workers.asset_logistics_worker import (
    WORKER_NAME,
    callback,
    process_asset_logistics_issue,
)


class FakeMessage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.message_id = "message-asset-001"
        self.delivery_attempt = 1
        self.ack = Mock()
        self.nack = Mock()


def make_event(
    *,
    owner: str = "AssetLogistics",
) -> dict[str, str]:
    return {
        "event_id": "event-asset-001",
        "event_type": "handover.issue.received",
        "event_version": "1.0",
        "occurred_at": "2026-08-20T00:00:00+00:00",
        "issue_id": "issue-asset-001",
        "owner": owner,
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-wheelchair-demo",
    }


class AssetDomainTests(unittest.TestCase):
    def test_standard_wheelchair_can_be_located(self) -> None:
        asset = find_available_asset("standard_wheelchair")

        self.assertEqual(asset["asset_id"], "WC-041")
        self.assertTrue(asset["available"])

    def test_unknown_asset_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported asset type",
        ):
            find_available_asset("iv_pump")


class AssetWorkflowTests(unittest.TestCase):
    @patch(
        "next_shift.workflows.asset_logistics.transition_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_received_asset_issue_can_be_triaged(
        self,
        mock_get_issue: Mock,
        mock_transition: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "RECEIVED",
        }
        mock_transition.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "TRIAGED",
        }

        result = triage_asset_issue("issue-asset-001")

        self.assertEqual(result["state"], "TRIAGED")

        mock_transition.assert_called_once_with(
            issue_id="issue-asset-001",
            new_state="TRIAGED",
            actor=WORKER_NAME,
            reason=(
                "AssetLogistics accepted the routed "
                "operational asset request."
            ),
        )

    @patch(
        "next_shift.workflows.asset_logistics.transition_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_wrong_owner_cannot_be_triaged(
        self,
        mock_get_issue: Mock,
        mock_transition: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-001",
            "owner": "Facilities",
            "state": "RECEIVED",
        }

        with self.assertRaisesRegex(
            ValueError,
            "AssetLogistics cannot process owner",
        ):
            triage_asset_issue("issue-001")

        mock_transition.assert_not_called()

    @patch(
        "next_shift.workflows.asset_logistics.find_available_asset"
    )
    @patch(
        "next_shift.workflows.asset_logistics.transition_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_wheelchair_location_produces_assignment(
        self,
        mock_get_issue: Mock,
        mock_transition: Mock,
        mock_find_asset: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "TRIAGED",
        }

        mock_find_asset.return_value = {
            "asset_id": "WC-041",
            "asset_type": "standard_wheelchair",
            "location": "Floor 3 - Lift Lobby",
            "available": True,
        }

        mock_transition.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "ASSIGNED",
        }

        result = locate_standard_wheelchair(
            "issue-asset-001"
        )

        self.assertEqual(
            result["asset"]["asset_id"],
            "WC-041",
        )
        self.assertEqual(
            result["issue"]["state"],
            "ASSIGNED",
        )

    @patch(
        "next_shift.workflows.asset_logistics.locate_standard_wheelchair"
    )
    @patch(
        "next_shift.workflows.asset_logistics.triage_asset_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_received_issue_advances_to_assigned(
        self,
        mock_get_issue: Mock,
        mock_triage: Mock,
        mock_locate: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "RECEIVED",
        }

        mock_triage.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "TRIAGED",
        }

        mock_locate.return_value = {
            "issue": {
                "id": "issue-asset-001",
                "owner": "AssetLogistics",
                "state": "ASSIGNED",
            },
            "asset": {
                "asset_id": "WC-041",
                "asset_type": "standard_wheelchair",
                "location": "Floor 3 - Lift Lobby",
                "available": True,
            },
        }

        result = advance_asset_issue("issue-asset-001")

        self.assertEqual(result["outcome"], "ASSIGNED")
        self.assertEqual(
            result["issue"]["state"],
            "ASSIGNED",
        )
        self.assertEqual(
            result["asset"]["asset_id"],
            "WC-041",
        )

        mock_triage.assert_called_once_with(
            "issue-asset-001"
        )
        mock_locate.assert_called_once_with(
            "issue-asset-001"
        )

    @patch(
        "next_shift.workflows.asset_logistics.locate_standard_wheelchair"
    )
    @patch(
        "next_shift.workflows.asset_logistics.triage_asset_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_triaged_issue_resumes_at_assignment(
        self,
        mock_get_issue: Mock,
        mock_triage: Mock,
        mock_locate: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "TRIAGED",
        }

        mock_locate.return_value = {
            "issue": {
                "id": "issue-asset-001",
                "owner": "AssetLogistics",
                "state": "ASSIGNED",
            },
            "asset": {
                "asset_id": "WC-041",
                "asset_type": "standard_wheelchair",
                "location": "Floor 3 - Lift Lobby",
                "available": True,
            },
        }

        result = advance_asset_issue("issue-asset-001")

        self.assertEqual(result["outcome"], "ASSIGNED")
        mock_triage.assert_not_called()
        mock_locate.assert_called_once_with(
            "issue-asset-001"
        )

    @patch(
        "next_shift.workflows.asset_logistics.locate_standard_wheelchair"
    )
    @patch(
        "next_shift.workflows.asset_logistics.triage_asset_issue"
    )
    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_assigned_issue_is_idempotent(
        self,
        mock_get_issue: Mock,
        mock_triage: Mock,
        mock_locate: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-asset-001",
            "owner": "AssetLogistics",
            "state": "ASSIGNED",
        }

        result = advance_asset_issue("issue-asset-001")

        self.assertEqual(result["outcome"], "ASSIGNED")
        self.assertEqual(
            result["issue"]["state"],
            "ASSIGNED",
        )
        self.assertIsNone(result["asset"])

        mock_triage.assert_not_called()
        mock_locate.assert_not_called()

    @patch("next_shift.workflows.asset_logistics.get_issue")
    def test_advance_rejects_wrong_owner(
        self,
        mock_get_issue: Mock,
    ) -> None:
        mock_get_issue.return_value = {
            "id": "issue-001",
            "owner": "Facilities",
            "state": "RECEIVED",
        }

        with self.assertRaisesRegex(
            ValueError,
            "AssetLogistics cannot process owner",
        ):
            advance_asset_issue("issue-001")


class AssetWorkerTests(unittest.TestCase):
    @patch(
        "workers.asset_logistics_worker.advance_asset_issue"
    )
    def test_worker_advances_routed_issue(
        self,
        mock_advance: Mock,
    ) -> None:
        mock_advance.return_value = {
            "outcome": "ASSIGNED",
        }

        result = process_asset_logistics_issue(
            "issue-asset-001"
        )

        self.assertEqual(result, "ASSIGNED")
        mock_advance.assert_called_once_with(
            "issue-asset-001"
        )

    @patch(
        "workers.asset_logistics_worker.record_processed_event"
    )
    @patch(
        "workers.asset_logistics_worker.process_asset_logistics_issue",
        return_value="ASSIGNED",
    )
    @patch(
        "workers.asset_logistics_worker.event_already_processed",
        return_value=False,
    )
    def test_asset_event_is_processed_and_acked(
        self,
        mock_already: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        message = FakeMessage(
            json.dumps(make_event()).encode("utf-8")
        )

        callback(message)

        mock_process.assert_called_once_with(
            "issue-asset-001"
        )

        mock_record.assert_called_once_with(
            event_id="event-asset-001",
            message_id="message-asset-001",
            issue_id="issue-asset-001",
            outcome="ASSIGNED",
            worker=WORKER_NAME,
        )

        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch(
        "workers.asset_logistics_worker.record_processed_event"
    )
    @patch(
        "workers.asset_logistics_worker.process_asset_logistics_issue"
    )
    @patch(
        "workers.asset_logistics_worker.event_already_processed"
    )
    def test_facilities_event_is_not_claimed(
        self,
        mock_already: Mock,
        mock_process: Mock,
        mock_record: Mock,
    ) -> None:
        message = FakeMessage(
            json.dumps(
                make_event(owner="Facilities")
            ).encode("utf-8")
        )

        callback(message)

        mock_already.assert_not_called()
        mock_process.assert_not_called()
        mock_record.assert_not_called()

        message.ack.assert_called_once()
        message.nack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
