from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_demo_scenario_is_synthetic_nonclinical_and_six_team() -> None:
    script = (ROOT / "services/operations_ui/static/app.js").read_text()
    scenario = script.split('const publicDemoHandover = "', 1)[1].split('";', 1)[0].lower()

    assert "synthetic" in scenario
    for operational_signal in (
        "wheelchair",
        "spanish interpreter",
        "home oxygen delivery",
        "evs turnaround",
        "sink",
        "patient transport",
    ):
        assert operational_signal in scenario
    for prohibited_public_demo_term in (
        "medication",
        "prescribe",
        "diagnosis",
        "dietary",
        "interview",
    ):
        assert prohibited_public_demo_term not in scenario


def test_public_demo_ui_states_real_governance_and_review_boundary() -> None:
    template = (ROOT / "services/operations_ui/templates/index.html").read_text()
    script = (ROOT / "services/operations_ui/static/app.js").read_text()
    plain_language = (
        ROOT / "services/operations_ui/static/plain-language.js"
    ).read_text()

    assert "Completion requires trusted evidence and independent verification." in template
    assert "Interpret" in template and "Verify" in template
    assert "Prepared synthetic text · review before sending" in script
    assert "Six operational teams represented" in script
    assert "Six operational teams ready · review before sending" in plain_language
    assert "Preparing operational work…" in plain_language
