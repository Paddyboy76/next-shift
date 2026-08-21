from __future__ import annotations

import os

from flask import Flask
from flask import jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


TIMEOUT_SECONDS = 20

app = Flask(__name__)


def _state_url() -> str:
    value = os.environ.get(
        "STATE_AUTHORITY_URL",
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            "STATE_AUTHORITY_URL is required"
        )

    return value.rstrip("/")


def _token(audience: str) -> str:
    token = id_token.fetch_id_token(
        Request(),
        audience,
    )

    if not token:
        raise RuntimeError(
            "Unable to obtain State Authority identity token"
        )

    return token


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "next-shift-trusted-evidence",
        }
    )


@app.post("/v1/issues/<issue_id>/complete")
def complete_issue(issue_id: str):
    state_url = _state_url()
    response = requests.post(
        f"{state_url}/v1/issues/{issue_id}/evidence",
        headers={
            "Authorization": (
                f"Bearer {_token(state_url)}"
            ),
            "Content-Type": "application/json",
        },
        json={},
        timeout=TIMEOUT_SECONDS,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {
            "error": "invalid_state_authority_response",
            "detail": response.text[:1000],
        }

    return jsonify(payload), response.status_code
