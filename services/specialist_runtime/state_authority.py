from __future__ import annotations

import os
from typing import Any

import requests
from google.auth.transport.requests import (
    Request as GoogleAuthRequest,
)
from google.oauth2 import id_token


class StateAuthorityError(Exception):
    pass


def _base_url() -> str:
    value = os.environ.get(
        "STATE_AUTHORITY_URL"
    )

    if not value:
        raise RuntimeError(
            "STATE_AUTHORITY_URL is required"
        )

    return value.rstrip("/")


def transition_issue(
    *,
    issue_id: str,
    capability: str,
    expected_state: str,
    new_state: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    base_url = _base_url()

    token = id_token.fetch_id_token(
        GoogleAuthRequest(),
        base_url,
    )

    response = requests.post(
        (
            f"{base_url}/v1/issues/"
            f"{issue_id}/transition"
        ),
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
        json={
            "capability": capability,
            "expected_state": expected_state,
            "new_state": new_state,
            "reason": reason,
            "updates": updates,
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise StateAuthorityError(
            "State Authority rejected "
            f"transition: HTTP "
            f"{response.status_code}"
        )

    result = response.json()

    if not isinstance(result, dict):
        raise StateAuthorityError(
            "Invalid State Authority response"
        )

    return result
