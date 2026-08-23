from __future__ import annotations

import unittest

from services.operations_ui.intelligence import analyze_issues


class OperationalIntelligenceTests(unittest.TestCase):
    def test_analysis_is_advisory_history_without_state_mutation(self) -> None:
        issues = [
            {
                "id": "one",
                "owner": "Facilities",
                "state": "CLOSED",
                "created_at": "2026-08-23T00:00:00+00:00",
                "closed_at": "2026-08-23T00:20:00+00:00",
                "workflow_input": {"room": "Room 402"},
            },
            {
                "id": "two",
                "owner": "Facilities",
                "state": "ACTION_PENDING",
                "workflow_input": {"room": "Room 402"},
            },
        ]
        before = [dict(item) for item in issues]

        result = analyze_issues(issues)

        self.assertEqual(result["sample_size"], 2)
        self.assertEqual(result["owner_counts"], {"Facilities": 2})
        self.assertEqual(result["mean_closure_minutes_by_owner"], {"Facilities": 20.0})
        self.assertEqual(result["repeated_locations"][0]["location"], "Room 402")
        self.assertEqual(issues, before)


if __name__ == "__main__":
    unittest.main()
