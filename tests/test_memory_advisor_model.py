from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_MAIN = ROOT / "services" / "memory_sync_runtime" / "main.py"
DEPLOY = ROOT / "deploy_memory_advisor.sh"


def test_memory_advisor_uses_gemini_35_global_model_path():
    source = MEMORY_MAIN.read_text(encoding="utf-8")
    assert 'MODEL_LOCATION = "global"' in source
    assert 'MODEL = os.environ.get("ADVISOR_MODEL", "gemini-3.5-flash")' in source
    assert "vertexai.init(project=PROJECT, location=MODEL_LOCATION)" in source
    assert '"model": MODEL' in source


def test_memory_advisor_deploy_pins_gemini_35():
    source = DEPLOY.read_text(encoding="utf-8")
    assert 'MODEL="gemini-3.5-flash"' in source
    assert 'ADVISOR_MODEL=${MODEL}' in source
    assert "MEMORY_ADVISOR_DEPLOY_OK=1" in source
