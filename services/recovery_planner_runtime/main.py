from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


app = Flask(__name__)
TIMEOUT_SECONDS = 20


def _state_url() -> str:
    value = os.environ.get("STATE_AUTHORITY_URL", "").strip()
    if not value:
        raise RuntimeError("STATE_AUTHORITY_URL is required")
    return value.rstrip("/")


def _headers(url: str) -> dict[str, str]:
    token = id_token.fetch_id_token(Request(), url)
    if not token:
        raise RuntimeError("Unable to obtain State Authority identity token")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = _state_url()
    response = requests.request(method, f"{url}{path}", headers=_headers(url),
                                json=payload, timeout=TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise RuntimeError(f"State Authority rejected recovery operation: {response.status_code} {response.text[:300]}")
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("State Authority returned invalid recovery payload")
    return body


def _proposal(context: dict[str, Any]) -> dict[str, Any]:
    issue = context.get("issue") or {}
    failure = context.get("latest_verification_failure") or {}
    state = str(issue.get("state", ""))
    history = issue.get("history") if isinstance(issue.get("history"), list) else []
    if state == "ACTION_PENDING":
        action = "REQUEST_FRESH_EVIDENCE"
        reason = str(failure.get("reason") or issue.get("verification_status") or "evidence_delayed")
        recommendation = (
            "Request a fresh observation from the existing trusted evidence integration, "
            "then submit it to the independent verifier. Do not reuse rejected evidence."
        )
    elif state == "BLOCKED":
        action = "HUMAN_REVIEW"
        reason = "blocked_dependency"
        recommendation = (
            "Escalate the blocking dependency to an authorized operator. Preserve the "
            "existing owner and require new trusted evidence before verification."
        )
    else:
        action = "RETRY_SPECIALIST"
        reason = "authorized_review_required"
        recommendation = (
            "After an authorized human decision, return work to the same least-privilege "
            "specialist. Trusted evidence and independent verification remain mandatory."
        )
    return {
        "failure_reason": reason[:500],
        "recommended_action": action,
        "recommendation": recommendation,
        "historical_context": [{"source": "authoritative_issue_history",
                                "transition_count": len(history),
                                "advisory_only": True}],
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "controlled-recovery-planner",
                    "authority": "ADVISORY_NO_STATE_MUTATION_NO_CLOSURE"})


@app.post("/v1/issues/<issue_id>/plan")
def plan(issue_id: str):
    try:
        context = _request("GET", f"/v1/issues/{issue_id}/recovery-context")
        result = _request("POST", f"/v1/issues/{issue_id}/recovery-plans",
                          _proposal(context))
    except RuntimeError as error:
        return jsonify({"error": "recovery_planning_failed", "message": str(error)}), 502
    return jsonify(result), 201
