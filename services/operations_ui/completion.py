from __future__ import annotations

import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


TIMEOUT_SECONDS = 20


def _service_url(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value.rstrip("/")


def _token(audience: str) -> str:
    token = id_token.fetch_id_token(Request(), audience)
    if not token:
        raise RuntimeError("Unable to obtain service identity token")
    return token


def _post(*, service_url: str, path: str) -> dict[str, Any]:
    response = requests.post(
        f"{service_url}{path}",
        headers={"Authorization": f"Bearer {_token(service_url)}", "Content-Type": "application/json"},
        json={},
        timeout=TIMEOUT_SECONDS,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Downstream service returned invalid JSON") from exc
    if response.status_code >= 400:
        raise RuntimeError(str(payload.get("message") or payload.get("error") or f"Downstream status {response.status_code}"))
    if not isinstance(payload, dict):
        raise RuntimeError("Downstream service returned invalid payload")
    return payload


def _refresh_human_reach(issue_id: str) -> None:
    url = os.environ.get("HUMAN_REACH_URL", "").strip().rstrip("/")
    if not url:
        return
    try:
        _post(service_url=url, path=f"/v1/human-reach/deliveries/{issue_id}/refresh")
    except RuntimeError:
        # Chat is a communication surface, not workflow authority. A refresh
        # failure must never roll back trusted evidence or independent closure.
        return


def record_trusted_completion(issue_id: str) -> dict[str, Any]:
    result = _post(
        service_url=_service_url("EVIDENCE_SERVICE_URL"),
        path=f"/v1/issues/{issue_id}/complete",
    )
    _refresh_human_reach(issue_id)
    return result


def run_independent_verifier(issue_id: str) -> dict[str, Any]:
    result = _post(
        service_url=_service_url("VERIFIER_SERVICE_URL"),
        path=f"/v1/issues/{issue_id}/verify",
    )
    _refresh_human_reach(issue_id)
    return result
