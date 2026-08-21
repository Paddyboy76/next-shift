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

    def test_deploy_bundles_local_next_shift_package(self) -> None:
        self.assertIn('NEXT_SHIFT_PACKAGE = ROOT / "next_shift"', self.source)
        self.assertIn('"extra_packages": [str(NEXT_SHIFT_PACKAGE)]', self.source)

    def test_deploy_includes_runtime_cloud_dependencies(self) -> None:
        self.assertIn("google-cloud-firestore==2.28.1", self.source)
        self.assertIn("google-cloud-pubsub==2.39.0", self.source)

    def test_deploy_matches_local_serialization_versions(self) -> None:
        self.assertIn("cloudpickle==3.1.2", self.source)
        self.assertIn("pydantic==2.13.4", self.source)


if __name__ == "__main__":
    unittest.main()
