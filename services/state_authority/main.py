from __future__ import annotations

import os
from typing import Any

from flask import Flask
from flask import jsonify
from flask import request

from identity import verified_principal
from security import (
    AuthenticationError,
    AuthorizationError,
)
from state import (
    authorize_and_transition,
    authorize_and_update,
)


app = Flask(__name__)


def _audience() -> str:
    audience = os.environ.get(
        "STATE_AUTHORITY_AUDIENCE"
    )

    if not audience:
        raise RuntimeError(
            "STATE_AUTHORITY_AUDIENCE is required"
        )

    return audience


def _principal() -> str:
    principal, _claims = (
        verified_principal(
            request.headers.get(
                "Authorization"
            ),
            audience=_audience(),
        )
    )

    return principal


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": (
                "next-shift-state-authority"
            ),
        }
    )


@app.post(
    "/v1/issues/<issue_id>/mutate"
)
def mutate_issue(
    issue_id: str,
):
    try:
        principal = _principal()
    except AuthenticationError:
        return (
            jsonify(
                {
                    "error": (
                        "authentication_required"
                    )
                }
            ),
            401,
        )

    payload: dict[str, Any] | None = (
        request.get_json(
            silent=True
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            jsonify(
                {
                    "error": "invalid_request"
                }
            ),
            400,
        )

    capability = payload.get(
        "capability"
    )

    expected_state = payload.get(
        "expected_state"
    )

    updates = payload.get(
        "updates"
    )

    if (
        not isinstance(
            capability,
            str,
        )
        or not capability
        or not isinstance(
            expected_state,
            str,
        )
        or not expected_state
        or not isinstance(
            updates,
            dict,
        )
    ):
        return (
            jsonify(
                {
                    "error": "invalid_request"
                }
            ),
            400,
        )

    try:
        authorize_and_update(
            principal=principal,
            issue_id=issue_id,
            capability=capability,
            expected_state=expected_state,
            updates=updates,
        )
    except AuthorizationError:
        return (
            jsonify(
                {
                    "error": "not_authorized"
                }
            ),
            403,
        )

    return jsonify(
        {
            "status": "updated",
            "issue_id": issue_id,
        }
    )


@app.post(
    "/v1/issues/<issue_id>/transition"
)
def transition_issue(
    issue_id: str,
):
    try:
        principal = _principal()
    except AuthenticationError:
        return (
            jsonify(
                {
                    "error": (
                        "authentication_required"
                    )
                }
            ),
            401,
        )

    payload: dict[str, Any] | None = (
        request.get_json(
            silent=True
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            jsonify(
                {
                    "error": "invalid_request"
                }
            ),
            400,
        )

    capability = payload.get(
        "capability"
    )

    expected_state = payload.get(
        "expected_state"
    )

    new_state = payload.get(
        "new_state"
    )

    reason = payload.get(
        "reason"
    )

    updates = payload.get(
        "updates",
        {},
    )

    if (
        not isinstance(
            capability,
            str,
        )
        or not capability
        or not isinstance(
            expected_state,
            str,
        )
        or not expected_state
        or not isinstance(
            new_state,
            str,
        )
        or not new_state
        or not isinstance(
            reason,
            str,
        )
        or not reason.strip()
        or not isinstance(
            updates,
            dict,
        )
    ):
        return (
            jsonify(
                {
                    "error": "invalid_request"
                }
            ),
            400,
        )

    try:
        result = authorize_and_transition(
            principal=principal,
            issue_id=issue_id,
            capability=capability,
            expected_state=expected_state,
            new_state=new_state,
            reason=reason,
            updates=updates,
        )
    except AuthorizationError:
        return (
            jsonify(
                {
                    "error": "not_authorized"
                }
            ),
            403,
        )

    return jsonify(
        {
            "status": "transitioned",
            "issue_id": issue_id,
            "from_state": (
                result["from_state"]
            ),
            "to_state": (
                result["to_state"]
            ),
            "transition_event_id": (
                result[
                    "transition_event_id"
                ]
            ),
        }
    )
