from __future__ import annotations

import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


DEFAULT_TIMEOUT_SECONDS = 20


def _authority_url() -> str:
    value = os.environ.get(
        "STATE_AUTHORITY_URL",
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            "STATE_AUTHORITY_URL is required"
        )

    return value.rstrip("/")


def _identity_token(
    audience: str,
) -> str:
    token = id_token.fetch_id_token(
        Request(),
        audience,
    )

    if not token:
        raise RuntimeError(
            "Unable to obtain State Authority identity token"
        )

    return token


def persist_handover_proposals(
    *,
    proposals: list[dict[str, Any]],
    source_reference: str,
) -> list[dict[str, Any]]:
    if not proposals:
        return []

    authority_url = _authority_url()
    token = _identity_token(
        authority_url
    )

    created: list[dict[str, Any]] = []

    for proposal in proposals:
        response = requests.post(
            f"{authority_url}/v1/issues",
            headers={
                "Authorization": (
                    f"Bearer {token}"
                ),
                "Content-Type": "application/json",
            },
            json={
                "proposal": proposal,
                "source_type": "operations_ui",
                "source_reference": source_reference,
            },
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        if response.status_code >= 400:
            body = response.text[:1000]
            raise RuntimeError(
                "State Authority rejected intake proposal: "
                f"status={response.status_code} body={body}"
            )

        payload = response.json()
        issue = payload.get("issue")

        if not isinstance(issue, dict):
            raise RuntimeError(
                "State Authority returned an invalid create response"
            )

        created.append(issue)

    return created
