import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_FILE = ROOT / "deploy_agent.py"
PYPROJECT_FILE = ROOT / "pyproject.toml"
GITIGNORE_FILE = ROOT / ".gitignore"


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

    def test_deploy_builds_installable_runtime_wheel(self) -> None:
        self.assertIn('"pip",', self.source)
        self.assertIn('"wheel",', self.source)
        self.assertIn('wheel_dir.glob("next_shift_runtime-*.whl")', self.source)
        self.assertIn("staged_wheel.name", self.source)

    def test_deploy_stages_wheel_as_top_level_relative_package(self) -> None:
        self.assertIn("staged_wheel = ROOT / wheel_path.name", self.source)
        self.assertIn('"extra_packages": [staged_wheel.name]', self.source)
        self.assertIn("os.chdir(ROOT)", self.source)
        self.assertIn("staged_wheel.unlink(missing_ok=True)", self.source)
        self.assertNotIn('"extra_packages": [str(wheel_path)]', self.source)

    def test_wheel_build_does_not_use_repo_as_build_source(self) -> None:
        self.assertIn('source_dir = work_dir / "source"', self.source)
        self.assertIn("shutil.copytree(", self.source)
        self.assertIn("str(source_dir)", self.source)

    def test_runtime_package_metadata_includes_next_shift(self) -> None:
        self.assertTrue(PYPROJECT_FILE.is_file())
        pyproject = PYPROJECT_FILE.read_text(encoding="utf-8")
        self.assertIn('name = "next-shift-runtime"', pyproject)
        self.assertIn('include = ["next_shift*"]', pyproject)

    def test_runtime_has_no_explicit_persistence_or_dispatch_sdks(self) -> None:
        self.assertNotIn("google-cloud-firestore", self.source)
        self.assertNotIn("google-cloud-pubsub", self.source)

    def test_deploy_matches_local_serialization_versions(self) -> None:
        self.assertIn("cloudpickle==3.1.2", self.source)
        self.assertIn("pydantic==2.13.4", self.source)

    def test_generated_packaging_artifacts_are_ignored(self) -> None:
        ignored = GITIGNORE_FILE.read_text(encoding="utf-8")
        self.assertIn("build/", ignored)
        self.assertIn("*.egg-info/", ignored)
        self.assertIn("*.whl", ignored)


if __name__ == "__main__":
    unittest.main()
