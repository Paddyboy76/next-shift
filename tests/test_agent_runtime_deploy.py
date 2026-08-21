import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_FILE = ROOT / "deploy_agent.py"


class AgentRuntimeDeployTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = DEPLOY_FILE.read_text(encoding="utf-8")

    def test_deploy_updates_existing_runtime(self) -> None:
        self.assertIn("client.agent_engines.update(", self.source)
        self.assertNotIn("client.agent_engines.create(", self.source)

    def test_deploy_targets_canonical_runtime(self) -> None:
        self.assertIn("8140616966286082048", self.source)
        self.assertIn("963749706976", self.source)

    def test_deploy_preserves_managed_agent_identity(self) -> None:
        self.assertIn("types.IdentityType.AGENT_IDENTITY", self.source)


if __name__ == "__main__":
    unittest.main()
