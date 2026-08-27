from pathlib import Path

from services.coverage_critic_runtime.main import _apply_scopes, normalize_review


ROOT = Path(__file__).resolve().parents[1]


def test_pass_may_keep_advisory_uncertainty():
    result = normalize_review(
        {
            "decision": "PASS",
            "summary": "Safe to route; one component is uncertain.",
            "findings": [
                {
                    "type": "UNCERTAIN",
                    "detail": "Exact source of the kitchen leak is unknown.",
                    "proposal_indexes": [1],
                    "suggested_owner": "Facilities",
                }
            ],
        },
        proposal_count=2,
    )

    assert result["decision"] == "PASS"
    assert result["findings"][0]["proposal_indexes"] == [1]


def test_blocking_or_missed_finding_cannot_remain_pass():
    result = normalize_review(
        {
            "decision": "PASS",
            "summary": "Second proposal is routed incorrectly.",
            "findings": [
                {
                    "type": "MISROUTED",
                    "detail": "Wrong owner.",
                    "proposal_indexes": [1],
                    "suggested_owner": "AssetLogistics",
                }
            ],
        },
        proposal_count=2,
    )

    assert result["decision"] == "REVIEW_REQUIRED"


def test_model_shape_noise_is_normalized_before_state_authority():
    result = normalize_review(
        {
            "decision": "review_required",
            "summary": "",
            "findings": [],
        },
        proposal_count=10,
    )

    assert result["decision"] == "REVIEW_REQUIRED"
    assert result["summary"]
    assert result["findings"][0]["type"] == "UNCERTAIN"


def test_unscoped_blocker_cannot_nuke_entire_handover_after_scoping_fails():
    review = {
        "decision": "REVIEW_REQUIRED",
        "summary": "Possible routing concern.",
        "findings": [
            {
                "type": "MISROUTED",
                "detail": "The critic did not identify which proposal is affected.",
                "proposal_indexes": [],
                "suggested_owner": "Facilities",
            }
        ],
    }

    result = _apply_scopes(review, scopes=[], proposal_count=4)

    assert result["decision"] == "PASS"
    assert result["findings"][0]["type"] == "UNCERTAIN"
    assert result["findings"][0]["proposal_indexes"] == []


def test_operations_intake_uses_bounded_arbitration_not_global_veto():
    source = (ROOT / "services" / "operations_ui" / "main.py").read_text(
        encoding="utf-8"
    )

    assert "arbitrate_coverage(proposals, coverage_review)" in source
    assert 'if coverage_review.get("decision") != "PASS":' not in source


def test_coverage_adapter_does_not_arbitrate_or_mutate_proposals():
    source = (ROOT / "services" / "operations_ui" / "critique.py").read_text(
        encoding="utf-8"
    )

    assert "arbitrate_coverage" not in source
    assert "proposals[:]" not in source


def test_intake_ui_names_created_and_held_outcomes():
    source = (ROOT / "services" / "operations_ui" / "static" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "intakeOutcomeText" in source
    assert "— created" in source
    assert "— held for review" in source
