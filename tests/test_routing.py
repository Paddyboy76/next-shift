import unittest

from next_shift.domain.routing import (
    OWNER_TO_WORKER,
    VALID_OPERATIONAL_OWNERS,
    validate_operational_owner,
    worker_for_owner,
)
from next_shift.events.contracts import (
    HANDOVER_RECEIVED_EVENT_TYPE,
    HANDOVER_RECEIVED_EVENT_VERSION,
)
from next_shift.events.routing import (
    route_handover_received_event,
)


def valid_payload(
    *,
    owner: str = "Facilities",
) -> dict[str, str]:
    return {
        "event_id": "event-001",
        "event_type": HANDOVER_RECEIVED_EVENT_TYPE,
        "event_version": HANDOVER_RECEIVED_EVENT_VERSION,
        "occurred_at": "2026-08-20T00:00:00+00:00",
        "issue_id": "issue-001",
        "owner": owner,
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-test-001",
    }


class OperationalOwnerTests(unittest.TestCase):
    def test_owner_set_is_canonical(self) -> None:
        self.assertEqual(
            VALID_OPERATIONAL_OWNERS,
            {
                "Facilities",
                "AssetLogistics",
                "LanguageAccess",
                "DischargeDME",
                "EVSThroughput",
                "PatientTransport",
            },
        )

    def test_every_owner_has_exactly_one_worker(self) -> None:
        self.assertEqual(
            set(OWNER_TO_WORKER),
            VALID_OPERATIONAL_OWNERS,
        )

    def test_facilities_route_is_preserved(self) -> None:
        self.assertEqual(
            worker_for_owner("Facilities"),
            "facilities_worker",
        )

    def test_asset_logistics_has_distinct_worker(self) -> None:
        self.assertEqual(
            worker_for_owner("AssetLogistics"),
            "asset_logistics_worker",
        )

    def test_unknown_owner_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported operational owner",
        ):
            validate_operational_owner("RandomDepartment")


class DispatcherContractTests(unittest.TestCase):
    def test_valid_facilities_event_routes_deterministically(
        self,
    ) -> None:
        route = route_handover_received_event(
            valid_payload(owner="Facilities")
        )

        self.assertEqual(
            route,
            {
                "issue_id": "issue-001",
                "event_id": "event-001",
                "owner": "Facilities",
                "worker": "facilities_worker",
            },
        )

    def test_asset_logistics_event_routes_deterministically(
        self,
    ) -> None:
        route = route_handover_received_event(
            valid_payload(owner="AssetLogistics")
        )

        self.assertEqual(
            route["worker"],
            "asset_logistics_worker",
        )

    def test_blank_owner_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Operational owner is required",
        ):
            route_handover_received_event(
                valid_payload(owner="")
            )

    def test_unknown_owner_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported operational owner",
        ):
            route_handover_received_event(
                valid_payload(owner="WheelchairTeam")
            )

    def test_invalid_event_contract_is_rejected_first(self) -> None:
        payload = valid_payload()
        payload["event_version"] = "999.0"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported event_version",
        ):
            route_handover_received_event(payload)


if __name__ == "__main__":
    unittest.main()


class WorkerSubscriptionTests(unittest.TestCase):
    def test_facilities_worker_uses_filtered_subscription(self) -> None:
        from workers.facilities_worker import SUBSCRIPTION_ID

        self.assertEqual(
            SUBSCRIPTION_ID,
            "next-shift-facilities",
        )

    def test_asset_logistics_worker_uses_filtered_subscription(
        self,
    ) -> None:
        from workers.asset_logistics_worker import SUBSCRIPTION_ID

        self.assertEqual(
            SUBSCRIPTION_ID,
            "next-shift-asset-logistics",
        )
