import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_FILE = ROOT / "next_shift" / "agent.py"
TOOLS_FILE = ROOT / "next_shift" / "tools.py"
CANONICAL_OWNERS = {
    "Facilities",
    "AssetLogistics",
    "LanguageAccess",
    "DischargeDME",
    "EVSThroughput",
    "PatientTransport",
}


class IntakeAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = AGENT_FILE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_agent_file_exists_at_canonical_path(self) -> None:
        self.assertTrue(AGENT_FILE.is_file())

    def test_intake_imports_only_proposal_tool(self) -> None:
        imported_names: set[str] = set()

        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "next_shift.tools"
            ):
                imported_names.update(
                    alias.name for alias in node.names
                )

        self.assertEqual(
            imported_names,
            {"create_handover_issue"},
        )

    def test_intake_does_not_import_mutation_or_read_capability(self) -> None:
        self.assertNotIn(
            "advance_handover_issue",
            self.source,
        )
        self.assertNotIn(
            "read_handover_issue",
            self.source,
        )

    def test_agent_tools_list_contains_only_proposal_capability(
        self,
    ) -> None:
        tools_lists: list[set[str]] = []

        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue

            for keyword in node.keywords:
                if keyword.arg != "tools":
                    continue

                if not isinstance(keyword.value, ast.List):
                    continue

                tools_lists.append(
                    {
                        element.id
                        for element in keyword.value.elts
                        if isinstance(element, ast.Name)
                    }
                )

        self.assertEqual(
            tools_lists,
            [{"create_handover_issue"}],
        )

    def test_intake_instruction_names_every_canonical_owner(self) -> None:
        for owner in CANONICAL_OWNERS:
            with self.subTest(owner=owner):
                self.assertIn(owner, self.source)

    def test_intake_explicitly_defers_persistence_to_state_authority(
        self,
    ) -> None:
        self.assertIn(
            "State Authority",
            self.source,
        )
        self.assertIn(
            "Do not invent durable issue IDs",
            self.source,
        )

    def test_proposal_tool_has_no_top_level_firestore_workflow_imports(
        self,
    ) -> None:
        tools_source = TOOLS_FILE.read_text(encoding="utf-8")
        top_level = ast.parse(tools_source)

        imported_modules = {
            node.module
            for node in top_level.body
            if isinstance(node, ast.ImportFrom)
        }

        self.assertNotIn(
            "next_shift.workflows.handover",
            imported_modules,
        )
        self.assertNotIn(
            "next_shift.persistence.firestore",
            imported_modules,
        )


if __name__ == "__main__":
    unittest.main()
