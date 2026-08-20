from __future__ import annotations

import os
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token


class StateAuthorityError(Exception):
    pass


def _state_authority_url() -> str:
    url = os.environ.get("STATE_AUTHORITY_URL")

    if not url:
        raise RuntimeError(
            "STATE_AUTHORITY_URL is required"
        )

    return url.rstrip("/")


def _identity_token() -> str:
    audience = _state_authority_url()

    return id_token.fetch_id_token(
        Request(),
        audience,
    )


def transition_issue(
    *,
    issue_id: str,
    expected_state: str,
    new_state: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    url = (
        f"{_state_authority_url()}"
        f"/v1/issues/{issue_id}/transition"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": (
                f"Bearer {_identity_token()}"
            ),
            "Content-Type": "application/json",
        },
        json={
            "capability": "facilities.coordinate",
            "expected_state": expected_state,
            "new_state": new_state,
            "reason": reason,
            "updates": updates,
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise StateAuthorityError(
            "State Authority rejected Facilities "
            f"transition with HTTP "
            f"{response.status_code}"
        )

    result = response.json()

    if not isinstance(result, dict):
        raise StateAuthorityError(
            "Invalid State Authority response"
        )

    return result
