from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "services" / "state_authority"
RUNTIME_DIR = ROOT / "services" / "human_reach_runtime"
DEPLOY = ROOT / "deploy_human_reach.sh"

if str(STATE_DIR) not in sys.path:
    sys.path.insert(0, str(STATE_DIR))

from human_reach_contract import build_delivery_request  # noqa: E402
from human_reach_privacy import pseudonymous_responder  # noqa: E402
from security import AuthorizationError  # noqa: E402


spec = importlib.util.spec_from_file_location(
    "next_shift_human_reach_runtime",
    RUNTIME_DIR / "main.py",
)
assert spec is not None
assert spec.loader is not None
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


ROUTES = {
    "Facilities": "Next Shift - Facilities Ops",
    "AssetLogistics": "Next Shift - Facilities Ops",
    "EVSThroughput": "Next Shift - Facilities Ops",
    "LanguageAccess": "Next Shift - Patient Flow",
    "DischargeDME": "Next Shift - Patient Flow",
    "PatientTransport": "Next Shift - Patient Flow",
}


def base_issue(owner: str) -> dict[str, object]:
    return {
        "owner": owner,
        "title": f"{owner} test work",
        "description": "Synthetic unresolved operational work.",
        "state": "ACTION_PENDING",
    }


class HumanReachTests(unittest.TestCase):
    def test_contract_builds_all_six_owner_work_cards(self) -> None:
        fixtures = {
            "Facilities": {
                "facilities_team_name": "Facilities Plumbing Team",
                "facilities_location": "Room 512",
                "facilities_work_order_id": "FAC-1234ABCD",
            },
            "AssetLogistics": {
                "dispatch_destination": "Room 512",
                "assigned_asset_id": "WC-041",
            },
            "LanguageAccess": {
                "interpreter_name": "Elena Ruiz",
                "interpreter_service_location": "Room 512",
                "interpreter_booking_id": "LANG-1234ABCD",
            },
            "DischargeDME": {
                "dme_provider_name": "Metro Home Medical",
                "dme_delivery_destination": "Discharge Lounge",
                "dme_order_id": "DME-1234ABCD",
            },
            "EVSThroughput": {
                "evs_team_name": "Environmental Services Team A",
                "evs_room": "Room 512",
                "evs_cleaning_id": "EVS-1234ABCD",
            },
            "PatientTransport": {
                "transporter_name": "Transport Team 17",
                "transport_origin": "Room 512",
                "transport_destination": "Discharge Lounge",
                "transport_request_id": "TRN-1234ABCD",
            },
        }

        for owner, fields in fixtures.items():
            with self.subTest(owner=owner):
                issue = {
                    **base_issue(owner),
                    **fields,
                }
                delivery = build_delivery_request(
                    issue_id=f"issue-{owner}",
                    issue=issue,
                    requested_at="2026-08-21T08:00:00+00:00",
                )

                self.assertEqual(delivery["owner"], owner)
                self.assertEqual(delivery["routing_key"], owner)
                self.assertEqual(
                    delivery["schema_version"],
                    "human-reach.delivery.v1",
                )
                self.assertEqual(
                    delivery["delivery_status"],
                    "PENDING",
                )
                self.assertTrue(delivery["who"])
                self.assertTrue(delivery["what"])
                self.assertTrue(delivery["where"])
                self.assertTrue(delivery["work_order"])

    def test_contract_rejects_missing_persisted_assignment_context(self) -> None:
        with self.assertRaises(AuthorizationError):
            build_delivery_request(
                issue_id="bad-facilities",
                issue=base_issue("Facilities"),
                requested_at="2026-08-21T08:00:00+00:00",
            )

    def test_routes_require_exact_canonical_owner_map(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HUMAN_REACH_ROUTES_JSON": json.dumps(ROUTES),
            },
            clear=False,
        ):
            self.assertEqual(runtime._routes(), ROUTES)

        incomplete = dict(ROUTES)
        incomplete.pop("Facilities")

        with patch.dict(
            os.environ,
            {
                "HUMAN_REACH_ROUTES_JSON": json.dumps(incomplete),
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                runtime._routes()

    def test_google_chat_card_preserves_human_state_boundaries(self) -> None:
        delivery = {
            "delivery_id": "issue-123",
            "owner": "Facilities",
            "issue_title": "Repair leaking sink in Room 512",
            "who": "Facilities Plumbing Team",
            "what": "Repair leaking sink in Room 512",
            "where": "Room 512",
            "work_order": "FAC-1234ABCD",
            "delivery_status": "DELIVERED",
        }

        card = runtime._work_card(delivery)
        encoded = json.dumps(card)

        self.assertIn("WHO", encoded)
        self.assertIn("WHAT", encoded)
        self.assertIn("WHERE", encoded)
        self.assertIn("WORK ORDER", encoded)
        self.assertIn("humanReach.acknowledge", encoded)
        self.assertIn("humanReach.blocked", encoded)
        self.assertIn("humanReach.completed", encoded)
        self.assertIn('"loadIndicator": "SPINNER"', encoded)

        claimed = runtime._work_card(
            {
                **delivery,
                "delivery_status": "COMPLETION_CLAIMED",
            }
        )
        claimed_text = json.dumps(claimed)

        self.assertIn("trusted evidence", claimed_text)
        self.assertIn("independent verification", claimed_text)
        self.assertNotIn("humanReach.completed", claimed_text)

    def test_pubsub_contract_is_versioned_and_rejects_wrong_event(self) -> None:
        event = {
            "event_id": "event-1",
            "event_type": "human_reach.delivery.requested",
            "schema_version": "human-reach.delivery.v1",
            "delivery_id": "issue-123",
            "issue_id": "issue-123",
            "owner": "Facilities",
            "routing_key": "Facilities",
        }
        envelope = {
            "message": {
                "data": base64.b64encode(
                    json.dumps(event).encode("utf-8")
                ).decode("ascii")
            }
        }

        decoded = runtime._decode_pubsub_event(envelope)
        self.assertEqual(decoded["delivery_id"], "issue-123")

        event["schema_version"] = "bad-version"
        envelope["message"]["data"] = base64.b64encode(
            json.dumps(event).encode("utf-8")
        ).decode("ascii")

        with self.assertRaises(ValueError):
            runtime._decode_pubsub_event(envelope)

    def test_chat_message_and_request_ids_are_deterministic(self) -> None:
        first = runtime._message_id("issue-123")
        second = runtime._message_id("issue-123")
        other = runtime._message_id("issue-456")

        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("client-next-shift-"))
        self.assertEqual(
            runtime._request_id("issue-123"),
            runtime._request_id("issue-123"),
        )

    def test_real_chat_identity_is_pseudonymized_before_persistence(self) -> None:
        first, first_label = pseudonymous_responder(
            "users/123456789"
        )
        again, _ = pseudonymous_responder(
            "users/123456789"
        )
        second, _ = pseudonymous_responder(
            "users/987654321"
        )

        self.assertEqual(first, again)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("chat-user-"))
        self.assertEqual(first_label, "Frontline responder")
        self.assertNotIn("123456789", first)

    def test_human_reach_runtime_has_no_direct_firestore_or_closure(self) -> None:
        source = (RUNTIME_DIR / "main.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("google.cloud.firestore", source)
        self.assertNotIn("handover_issues", source)
        self.assertNotIn("issue_evidence", source)
        self.assertNotIn("verification.close", source)
        self.assertNotIn("new_state", source)

    def test_state_authority_owns_delivery_mutations_and_transition_hook(self) -> None:
        policy = (STATE_DIR / "policy.py").read_text(
            encoding="utf-8"
        )
        main = (STATE_DIR / "main.py").read_text(
            encoding="utf-8"
        )
        wrapper = (
            STATE_DIR / "human_reach_transition.py"
        ).read_text(encoding="utf-8")
        freshness = (
            STATE_DIR / "human_reach_freshness.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"ns-human-reach@"', policy)
        self.assertIn('"human_reach.read_delivery"', policy)
        self.assertIn('"human_reach.delivery_update"', policy)
        self.assertIn("authorize_and_mark_delivered", main)
        self.assertIn("authorize_and_record_response", main)
        self.assertIn("authorize_and_get_fresh_delivery", main)
        self.assertIn("pseudonymous_responder", main)
        self.assertIn('new_state != "ACTION_PENDING"', wrapper)
        self.assertIn("ensure_delivery_for_action_pending", wrapper)
        self.assertIn('"delivery_status": "CANCELLED"', freshness)
        self.assertIn('current_state == "ACTION_PENDING"', freshness)

    def test_deployment_keeps_human_reach_private_and_data_less(self) -> None:
        source = DEPLOY.read_text(encoding="utf-8")

        self.assertIn("--no-allow-unauthenticated", source)
        self.assertIn("chat@system.gserviceaccount.com", source)
        self.assertIn("ns-push-human-reach", source)
        self.assertIn("roles/iam.serviceAccountTokenCreator", source)
        self.assertIn("HUMAN_REACH_NO_DIRECT_DATA_ROLES=1", source)
        self.assertIn("next-shift-human-reach-requested", source)
        self.assertIn("next-shift-human-reach-push", source)


if __name__ == "__main__":
    unittest.main()
