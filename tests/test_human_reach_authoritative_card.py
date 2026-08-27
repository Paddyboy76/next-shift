import json

from services.human_reach_runtime.rich_card import work_card


def _delivery(**overrides):
    value = {
        "delivery_id": "issue-123",
        "owner": "Facilities",
        "issue_title": "Repair leaking sink",
        "who": "Facilities Plumbing Team",
        "what": "Repair leaking sink",
        "where": "Room 406",
        "work_order": "FAC-123",
        "delivery_status": "DELIVERED",
        "authoritative_issue_state": "ACTION_PENDING",
    }
    value.update(overrides)
    return value


def test_action_pending_card_keeps_frontline_response_buttons():
    encoded = json.dumps(work_card(_delivery()))
    assert "humanReach.acknowledge" in encoded
    assert "humanReach.completed" in encoded


def test_closed_card_shows_verified_truth_and_no_stale_buttons():
    encoded = json.dumps(work_card(_delivery(authoritative_issue_state="CLOSED")))
    assert "Verified complete" in encoded
    assert "humanReach.acknowledge" not in encoded
    assert "humanReach.blocked" not in encoded
    assert "humanReach.completed" not in encoded
