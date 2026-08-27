from pathlib import Path

import pytest

from services.operations_ui import photo_evidence


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "services" / "operations_ui" / "templates" / "index.html"
PHOTO_JS = ROOT / "services" / "operations_ui" / "static" / "photo-evidence.js"
MAIN = ROOT / "services" / "operations_ui" / "main.py"


def test_photo_evidence_uses_gemini_35_and_rejects_bad_files():
    assert photo_evidence.MODEL == "gemini-3.5-flash"
    assert photo_evidence.MAX_IMAGE_BYTES == 8 * 1024 * 1024
    with pytest.raises(ValueError):
        photo_evidence._clean_image(b"x", "application/pdf", "Before")


def test_photo_evidence_is_facilities_supporting_evidence_not_closure():
    source = MAIN.read_text(encoding="utf-8")
    assert 'issue.get("owner") != "Facilities"' in source
    assert 'issue.get("state") != "ACTION_PENDING"' in source
    assert "record_trusted_completion(issue_id)" in source
    module = (ROOT / "services" / "operations_ui" / "photo_evidence.py").read_text(encoding="utf-8")
    assert '"authority": "SUPPORTING_VISUAL_EVIDENCE_ONLY"' in module
    assert '"may_close_work": False' in module


def test_photo_ui_loads_once_and_has_no_recovery_controls():
    html = INDEX.read_text(encoding="utf-8")
    source = PHOTO_JS.read_text(encoding="utf-8")
    assert '/static/photo-evidence.js' in html
    assert "root.dataset.photoEvidenceIssue = issueId" in source
    assert "Submit before & after photo proof" in source
    assert "recovery" not in source.lower()
