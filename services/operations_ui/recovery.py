from __future__ import annotations

import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


TIMEOUT_SECONDS = 20


def _url(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value.rstrip("/")


def _post(url: str, path: str) -> dict[str, Any]:
    token = id_token.fetch_id_token(Request(), url)
    response = requests.post(f"{url}{path}", headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"}, json={}, timeout=TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise RuntimeError(f"Recovery service rejected request: {response.status_code} {response.text[:300]}")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("Recovery service returned invalid JSON")
    return result


def create_plan(issue_id: str) -> dict[str, Any]:
    return _post(_url("RECOVERY_PLANNER_URL"), f"/v1/issues/{issue_id}/plan")


def sanction_plan(issue_id: str, plan_id: str) -> dict[str, Any]:
    return _post(_url("STATE_AUTHORITY_URL"),
                 f"/v1/issues/{issue_id}/recovery-plans/{plan_id}/sanction")
