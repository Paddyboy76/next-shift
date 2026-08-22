from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "services" / "state_authority"
RUNTIME_DIR = ROOT / "services" / "human_reach_runtime"

if str(STATE_DIR) not in sys.path:
    sys.path.insert(0, str(STATE_DIR))

from security import AuthorizationError  # noqa: E402


spec = importlib.util.spec_from_file_location(
    "next_shift_human_reach_routes",
    STATE_DIR / "human_reach_routes.py",
)
assert spec is not None
assert spec.loader is not None
state_routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state_routes)


class HumanReachEventBoundRouteTests(unittest.TestCase):
    def test_only_canonical_chat_destinations_can_be_registered(self) -> None:
        self.assertEqual(
            state_routes.route_id_for_display_name(
                "Next Shift - Facilities Ops"
            ),
            "facilities-ops",
        )
        self.assertEqual(
            state_routes.route_id_for_display_name(
                "Next Shift - Patient Flow"
            ),
            "patient-flow",
        )

        with self.assertRaises(AuthorizationError):
            state_routes.route_id_for_display_name(
                "Untrusted Chat Space"
            )

    def test_state_authority_owns_durable_route_storage(self) -> None:
        source = (
            STATE_DIR / "human_reach_routes.py"
        ).read_text(encoding="utf-8")
        api = (
            STATE_DIR / "human_reach_route_api.py"
        ).read_text(encoding="utf-8")
        procfile = (
            STATE_DIR / "Procfile"
        ).read_text(encoding="utf-8")

        self.assertIn('ROUTE_COLLECTION = "human_reach_routes"', source)
        self.assertIn("human_reach_route_conflict", source)
        self.assertIn(
            '"source": "google_chat_interaction_event"',
            source,
        )
        self.assertIn("/v1/human-reach/routes/register", api)
        self.assertIn("/v1/human-reach/routes/resolve", api)
        self.assertIn("/v1/human-reach/routes/deactivate", api)
        self.assertIn("entrypoint:app", procfile)

    def test_human_reach_learns_routes_without_direct_firestore(self) -> None:
        durable = (
            RUNTIME_DIR / "durable_routes.py"
        ).read_text(encoding="utf-8")
        entrypoint = (
            RUNTIME_DIR / "entrypoint.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("google.cloud.firestore", durable)
        self.assertIn('space.get("name")', durable)
        self.assertIn('space.get("displayName")', durable)
        self.assertIn("/v1/human-reach/routes/register", durable)
        self.assertIn("/v1/human-reach/routes/resolve", durable)
        self.assertIn("ADDED_TO_SPACE", entrypoint)
        self.assertIn("MESSAGE", entrypoint)
        self.assertIn("REMOVED_FROM_SPACE", entrypoint)

    def test_delivery_and_readiness_use_state_authority_routes(self) -> None:
        durable = (
            RUNTIME_DIR / "durable_routes.py"
        ).read_text(encoding="utf-8")
        entrypoint = (
            RUNTIME_DIR / "entrypoint.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "human_reach_runtime._resolve_space = durable_routes.resolve_space",
            entrypoint,
        )
        self.assertIn('"route_source": "state_authority"', entrypoint)
        self.assertNotIn("chat.googleapis.com/v1/spaces", durable)
        self.assertNotIn("_list_named_spaces", durable)


if __name__ == "__main__":
    unittest.main()
