from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "services" / "operations_ui" / "templates" / "index.html"
RECOVERY_JS = ROOT / "services" / "operations_ui" / "static" / "recovery-controls.js"


def test_recovery_controls_are_loaded_by_operations_ui():
    html = INDEX.read_text(encoding="utf-8")
    assert '/static/recovery-controls.js' in html


def test_recovery_controls_expose_plan_and_sanction_endpoints():
    source = RECOVERY_JS.read_text(encoding="utf-8")
    assert "Generate controlled recovery plan" in source
    assert "Sanction recovery plan" in source
    assert "/recovery-plan" in source
    assert "/recovery-plans/${encodeURIComponent(planId)}/sanction" in source
    assert "The planner cannot mutate work, record evidence, or close the issue." in source
