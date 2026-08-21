import unittest
from unittest.mock import patch

from services.operations_ui import data


class OperationsSummaryTests(unittest.TestCase):
    def test_summary_tolerates_malformed_dimensions(self) -> None:
        issues = [
            {
                "state": "ACTION_PENDING",
                "owner": "Facilities",
            },
            {
                "state": ["VERIFYING"],
                "owner": {"name": "AssetLogistics"},
            },
            {
                "state": "",
                "owner": None,
            },
        ]

        with patch.object(
            data,
            "list_issues",
            return_value=issues,
        ):
            summary = data.dashboard_summary()

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["open"], 3)
        self.assertEqual(summary["states"]["ACTION_PENDING"], 1)
        self.assertEqual(summary["states"]["UNKNOWN"], 2)
        self.assertEqual(summary["owners"]["Facilities"], 1)
        self.assertEqual(summary["owners"]["Unknown"], 2)

    def test_summary_preserves_valid_terminal_counts(self) -> None:
        issues = [
            {
                "state": "CLOSED",
                "owner": "Facilities",
            },
            {
                "state": "FAILED",
                "owner": "PatientTransport",
            },
            {
                "state": "VERIFYING",
                "owner": "LanguageAccess",
            },
        ]

        with patch.object(
            data,
            "list_issues",
            return_value=issues,
        ):
            summary = data.dashboard_summary()

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["closed"], 1)
        self.assertEqual(summary["verifying"], 1)


if __name__ == "__main__":
    unittest.main()
