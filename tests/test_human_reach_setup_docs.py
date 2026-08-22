import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "docs" / "human-reach-google-chat-setup.md"
DEPLOY = ROOT / "deploy_human_reach.sh"


class HumanReachSetupDocsTests(unittest.TestCase):
    def test_setup_uses_root_cloud_run_url_and_exact_spaces(self) -> None:
        setup = SETUP.read_text(encoding="utf-8")
        deploy = DEPLOY.read_text(encoding="utf-8")

        self.assertIn("Do not append `/chat` or `/pubsub`", setup)
        self.assertIn("Next Shift - Facilities Ops", setup)
        self.assertIn("Next Shift - Patient Flow", setup)
        self.assertIn("HUMAN_REACH_ROUTES_JSON", setup)
        self.assertIn("CHAT_HTTP_ENDPOINT=${HUMAN_REACH_URL}", deploy)


if __name__ == "__main__":
    unittest.main()
