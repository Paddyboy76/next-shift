from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "services" / "human_reach_runtime"
OPERATIONS_DIR = ROOT / "services" / "operations_ui"
DEPLOY = ROOT / "deploy_human_reach.sh"

if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

spec = importlib.util.spec_from_file_location(
    "next_shift_rich_card",
    RUNTIME_DIR / "rich_card.py",
)
assert spec is not None
assert spec.loader is not None
rich_card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rich_card)


ROUTES = {
    "Facilities": "Next Shift - Facilities Ops",
    "AssetLogistics": "Next Shift - Facilities Ops",
    "EVSThroughput": "Next Shift - Facilities Ops",
    "LanguageAccess": "Next Shift - Patient Flow",
    "DischargeDME": "Next Shift - Patient Flow",
    "PatientTransport": "Next Shift - Patient Flow",
}


class RichHumanReachCardTests(unittest.TestCase):
    def delivery(self, status: str = "DELIVERED") -> dict[str, object]:
        return {
            "delivery_id": "issue-123",
            "owner": "Facilities",
            "issue_title": "Repair leaking sink in Room 614",
            "who": "Facilities Plumbing Team",
            "what": "Repair leaking sink in Room 614",
            "where": "Room 614",
            "work_order": "FAC-1234ABCD",
            "delivery_status": status,
            "workflow_state": "ACTION_PENDING",
        }

    def env(self):
        return patch.dict(
            os.environ,
            {
                "HUMAN_REACH_ROUTES_JSON": json.dumps(ROUTES),
                "OPERATIONS_UI_URL": (
                    "https://next-shift-operations.example.run.app"
                ),
            },
            clear=False,
        )

    def test_card_uses_google_native_visual_hierarchy(self) -> None:
        with self.env():
            card = rich_card.work_card(self.delivery())

        encoded = json.dumps(card)

        self.assertIn('"sectionDividerStyle": "SOLID_DIVIDER"', encoded)
        self.assertIn('"materialIcon"', encoded)
        self.assertIn('"type": "FILLED"', encoded)
        self.assertIn('"type": "FILLED_TONAL"', encoded)
        self.assertIn('"type": "OUTLINED"', encoded)
        self.assertIn('"loadIndicator": "SPINNER"', encoded)
        self.assertIn("Operational assignment", encoded)
        self.assertIn("Human Reach", encoded)
        self.assertIn("Governed completion", encoded)

    def test_card_links_back_to_exact_operations_issue(self) -> None:
        with self.env():
            card = rich_card.work_card(self.delivery())

        encoded = json.dumps(card)

        self.assertIn("Open in Operations Console", encoded)
        self.assertIn("/?issue=issue-123", encoded)

        deeplink = (
            OPERATIONS_DIR / "static" / "deeplink.js"
        ).read_text(encoding="utf-8")
        template = (
            OPERATIONS_DIR / "templates" / "index.html"
        ).read_text(encoding="utf-8")

        self.assertIn("URLSearchParams", deeplink)
        self.assertIn("openIssue(issueId)", deeplink)
        self.assertIn("/static/deeplink.js", template)

    def test_completion_claim_visibly_preserves_verification_boundary(self) -> None:
        with self.env():
            card = rich_card.work_card(
                self.delivery("COMPLETION_CLAIMED")
            )

        encoded = json.dumps(card)

        self.assertIn("Completion claimed", encoded)
        self.assertIn("does <b>not</b> close this issue", encoded)
        self.assertIn("trusted evidence", encoded)
        self.assertIn("independent verifier", encoded)
        self.assertNotIn("humanReach.completed", encoded)

    def test_card_escapes_operational_text_before_html_rendering(self) -> None:
        delivery = self.delivery()
        delivery["what"] = '<script>alert("x")</script>'

        with self.env():
            card = rich_card.work_card(delivery)

        encoded = json.dumps(card)

        self.assertNotIn("<script>", encoded)
        self.assertIn("&lt;script&gt;", encoded)

    def test_deploy_passes_operations_url_to_human_reach(self) -> None:
        deploy = DEPLOY.read_text(encoding="utf-8")
        entrypoint = (
            RUNTIME_DIR / "entrypoint.py"
        ).read_text(encoding="utf-8")

        self.assertIn("OPERATIONS_UI_URL=${OPERATIONS_URL}", deploy)
        self.assertIn("HUMAN_REACH_OPERATIONS_DEEPLINK_OK=1", deploy)
        self.assertIn("human_reach_runtime._work_card = work_card", entrypoint)
        self.assertIn('"card_renderer": "cards_v2_rich"', entrypoint)


if __name__ == "__main__":
    unittest.main()
