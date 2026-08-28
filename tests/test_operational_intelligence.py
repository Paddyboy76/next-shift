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

    def test_recommendations_match_operations_advisor_card_contract(self) -> None:
        """static/deeplink.js renders item.pattern / why_it_matters / recommended_change /
        confidence / affected_scope. A list of plain strings renders as blank cards."""
        required = {
            "pattern",
            "why_it_matters",
            "recommended_change",
            "affected_scope",
            "expected_improvement",
            "confidence",
        }

        for issues in ([], [{"id": "one", "owner": "Facilities", "state": "ACTION_PENDING"}]):
            with self.subTest(sample_size=len(issues)):
                recommendations = analyze_issues(issues)["recommendations"]

                self.assertTrue(recommendations)
                for recommendation in recommendations:
                    self.assertIsInstance(recommendation, dict)
                    self.assertTrue(required.issubset(recommendation))
                    for key in required:
                        self.assertIsInstance(recommendation[key], str)
                        self.assertTrue(recommendation[key].strip())

    def test_local_analysis_is_not_presented_as_gemini_output(self) -> None:
        self.assertEqual(
            analyze_issues([])["recommendation_source"],
            "LOCAL_DETERMINISTIC_FALLBACK",
        )


if __name__ == "__main__":
    unittest.main()
