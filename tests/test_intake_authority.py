import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_FILE = ROOT / "next_shift" / "agent.py"
CONTRACT_FILE = ROOT / "next_shift" / "intake_contract.py"
CANONICAL_BUCKETS = {
    "facilities",
    "asset_logistics",
    "language_access",
    "discharge_dme",
    "evs_throughput",
    "patient_transport",
}


class IntakeAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = AGENT_FILE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_agent_file_exists_at_canonical_path(self) -> None:
        self.assertTrue(AGENT_FILE.is_file())
        self.assertTrue(CONTRACT_FILE.is_file())

    def test_intake_has_no_tool_dependency(self) -> None:
        imported_modules = {
            node.module
            for node in ast.walk(self.tree)
            if isinstance(node, ast.ImportFrom)
        }

        self.assertNotIn("next_shift.tools", imported_modules)
        self.assertNotIn("next_shift.workflows.handover", imported_modules)
        self.assertNotIn("next_shift.persistence.firestore", imported_modules)

    def test_intake_uses_typed_output_schema(self) -> None:
        self.assertIn(
            "from next_shift.intake_contract import IntakeResult",
            self.source,
        )
        self.assertIn("output_schema=IntakeResult", self.source)

    def test_agent_exposes_no_tools(self) -> None:
        tools_keywords = []

        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue

            for keyword in node.keywords:
                if keyword.arg == "tools":
                    tools_keywords.append(keyword)

        self.assertEqual(tools_keywords, [])

    def test_intake_instruction_names_every_owner_bucket(self) -> None:
        for bucket in CANONICAL_BUCKETS:
            with self.subTest(bucket=bucket):
                self.assertIn(bucket, self.source)

    def test_intake_explicitly_defers_persistence_to_state_authority(
        self,
    ) -> None:
        self.assertIn("State Authority", self.source)
        self.assertIn("Never invent issue IDs", self.source)

    def test_contract_has_owner_specific_required_workflow_models(self) -> None:
        contract = CONTRACT_FILE.read_text(encoding="utf-8")

        for bucket in CANONICAL_BUCKETS:
            with self.subTest(bucket=bucket):
                self.assertIn(f"    {bucket}: list[", contract)

        self.assertIn("class FacilitiesWorkflowInput(BaseModel):", contract)
        self.assertIn("facility_type: Literal[", contract)
        self.assertIn("location: str = Field(", contract)
        self.assertIn("class LanguageAccessWorkflowInput(BaseModel):", contract)
        self.assertIn("language: str = Field(", contract)
        self.assertIn("service_location: str = Field(", contract)
        self.assertIn("class PatientTransportWorkflowInput(BaseModel):", contract)
        self.assertIn("origin: str = Field(", contract)
        self.assertIn("destination: str = Field(", contract)
        self.assertIn("transport_type: Literal[", contract)
        self.assertIn('ConfigDict(extra="forbid")', contract)


if __name__ == "__main__":
    unittest.main()
