import unittest

from next_shift.events.contracts import (
    HANDOVER_RECEIVED_EVENT_TYPE,
    HANDOVER_RECEIVED_EVENT_VERSION,
    validate_handover_received_event,
)


def valid_payload() -> dict[str, str]:
    return {
        "event_id": "event-001",
        "event_type": HANDOVER_RECEIVED_EVENT_TYPE,
        "event_version": HANDOVER_RECEIVED_EVENT_VERSION,
        "occurred_at": "2026-08-20T00:00:00+00:00",
        "issue_id": "issue-001",
        "owner": "Facilities",
        "state": "RECEIVED",
        "source_type": "handover_note",
        "source_reference": "synthetic-test-001",
    }


class HandoverReceivedEventContractTests(unittest.TestCase):
    def test_valid_event_is_accepted(self) -> None:
        validate_handover_received_event(valid_payload())

    def test_every_required_field_is_enforced(self) -> None:
        payload = valid_payload()

        for field in tuple(payload):
            with self.subTest(field=field):
                candidate = payload.copy()
                del candidate[field]

                with self.assertRaisesRegex(
                    ValueError,
                    "Missing required event fields",
                ):
                    validate_handover_received_event(candidate)

    def test_wrong_event_type_is_rejected(self) -> None:
        payload = valid_payload()
        payload["event_type"] = "unsupported.event"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported event_type",
        ):
            validate_handover_received_event(payload)

    def test_wrong_event_version_is_rejected(self) -> None:
        payload = valid_payload()
        payload["event_version"] = "999.0"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported event_version",
        ):
            validate_handover_received_event(payload)

    def test_extra_routing_metadata_does_not_break_contract(self) -> None:
        payload = valid_payload()
        payload["trace_id"] = "trace-001"

        validate_handover_received_event(payload)


if __name__ == "__main__":
    unittest.main()
