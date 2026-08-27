from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "services" / "human_reach_runtime" / "photo_proof.py"
SPEC = importlib.util.spec_from_file_location("chat_photo_proof_test_module", MODULE_PATH)
photo_proof = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(photo_proof)


def _base_card():
    return {
        "card": {
            "sections": [
                {"widgets": []},
                {"widgets": []},
                {"widgets": []},
            ]
        }
    }


def test_issue_thread_key_round_trips_delivery_id():
    delivery_id = "abc123XYZ"
    key = photo_proof.thread_key(delivery_id)
    event = {
        "threadKey": key,
        "message": {"attachment": []},
    }

    assert photo_proof.delivery_id_from_event(event) == delivery_id


def test_facilities_completion_claim_prompts_for_chat_before_after_photos():
    card = photo_proof.decorate_card(
        {
            "delivery_id": "issue-1",
            "owner": "Facilities",
            "delivery_status": "COMPLETION_CLAIMED",
            "authoritative_issue_state": "ACTION_PENDING",
        },
        _base_card(),
    )
    rendered = str(card)

    assert "PHOTO PROOF" in rendered
    assert "BEFORE" in rendered
    assert "AFTER" in rendered
    assert "@mention Next Shift" in rendered

    other = photo_proof.decorate_card(
        {
            "delivery_id": "issue-2",
            "owner": "AssetLogistics",
            "delivery_status": "COMPLETION_CLAIMED",
            "authoritative_issue_state": "ACTION_PENDING",
        },
        _base_card(),
    )
    assert "PHOTO PROOF" not in str(other)


def test_operations_photo_evidence_is_read_only():
    source = (
        ROOT
        / "services"
        / "operations_ui"
        / "static"
        / "photo-evidence.js"
    ).read_text(encoding="utf-8")

    assert 'type="file"' not in source
    assert "data-photo-submit" not in source
    assert "Captured through Google Chat Human Reach" in source
