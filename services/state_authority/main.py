from __future__ import annotations

import os
from typing import Any

from flask import Flask
from flask import jsonify
from flask import request

from evidence import (
    authorize_and_close_verified_issue,
    authorize_and_get_verification_context,
    authorize_and_record_evidence,
    authorize_and_reject_verification,
)
from human_reach import (
    authorize_and_mark_delivered,
    authorize_and_record_response,
)
from human_reach_freshness import (
    authorize_and_get_fresh_delivery,
)
from human_reach_privacy import (
    pseudonymous_responder,
)
from human_reach_transition import (
    authorize_and_transition,
)
from recovery import recovery_context as get_recovery_context
from recovery import record_plan as persist_recovery_plan
from recovery import sanction_plan as approve_recovery_plan
from identity import verified_principal
from critique import authorize_and_record_coverage_review
from inspection import (
    authorize_and_get_inspection_context,
    authorize_and_record_inspection,
)
from intake import authorize_and_create
from security import (
    AuthenticationError,
    AuthorizationError,
)
from state import authorize_and_update


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


def _authenticated_principal():
    try:
        return _principal(), None
    except AuthenticationError:
        return None, (
            jsonify(
                {
                    "error": (
                        "authentication_required"
                    )
                }
            ),
            401,
        )


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


@app.get("/v1/issues/<issue_id>/recovery-context")
def recovery_context_route(issue_id: str):
    try:
        result = get_recovery_context(principal=_principal(), issue_id=issue_id)
    except AuthenticationError:
        return jsonify({"error": "authentication_required"}), 401
    except AuthorizationError as error:
        return jsonify({"error": error.reason, "details": error.details}), 403
    return jsonify(result)


@app.post("/v1/issues/<issue_id>/recovery-plans")
def recovery_plan_route(issue_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400
    try:
        result = persist_recovery_plan(principal=_principal(), issue_id=issue_id,
                                       proposal=payload)
    except AuthenticationError:
        return jsonify({"error": "authentication_required"}), 401
    except AuthorizationError as error:
        return jsonify({"error": error.reason, "details": error.details}), 403
    return jsonify({"status": "recovery_plan_proposed", "plan": result}), 201


@app.post("/v1/issues/<issue_id>/recovery-plans/<plan_id>/sanction")
def recovery_sanction_route(issue_id: str, plan_id: str):
    try:
        result = approve_recovery_plan(principal=_principal(), issue_id=issue_id,
                                       plan_id=plan_id)
    except AuthenticationError:
        return jsonify({"error": "authentication_required"}), 401
    except AuthorizationError as error:
        return jsonify({"error": error.reason, "details": error.details}), 403
    return jsonify({"status": "recovery_plan_sanctioned", "plan": result})


@app.post("/v1/issues")
def create_issue():
    principal, auth_error = (
        _authenticated_principal()
    )


    if auth_error is not None:
        return auth_error

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
                {"error": "invalid_request"}
            ),
            400,
        )

    proposal = payload.get("proposal")
    source_type = payload.get(
        "source_type"
    )
    source_reference = payload.get(
        "source_reference"
    )

    if (
        not isinstance(proposal, dict)
        or not isinstance(source_type, str)
        or not source_type.strip()
        or not isinstance(
            source_reference,
            str,
        )
        or not source_reference.strip()
    ):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    try:
        issue = authorize_and_create(
            principal=principal,
            proposal=proposal,
            source_type=source_type,
            source_reference=source_reference,
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return (
        jsonify(
            {
                "status": "created",
                "issue": issue,
            }
        ),
        201,
    )


@app.post("/v1/coverage-reviews")
def coverage_review():
    principal, auth_error = _authenticated_principal()
    if auth_error is not None:
        return auth_error
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400
    try:
        record = authorize_and_record_coverage_review(principal=principal, payload=payload)
    except AuthorizationError:
        return jsonify({"error": "not_authorized"}), 403
    return jsonify({"status": "coverage_review_recorded", "review": record}), 201


@app.get("/v1/issues/<issue_id>/inspection-context")
def inspection_context(issue_id: str):
    principal, auth_error = _authenticated_principal()
    if auth_error is not None:
        return auth_error
    try:
        result = authorize_and_get_inspection_context(principal=principal, issue_id=issue_id)
    except AuthorizationError:
        return jsonify({"error": "not_authorized"}), 403
    return jsonify({"status": "inspection_context", **result})


@app.post("/v1/issues/<issue_id>/evidence-inspections")
def evidence_inspection(issue_id: str):
    principal, auth_error = _authenticated_principal()
    if auth_error is not None:
        return auth_error
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400
    try:
        record = authorize_and_record_inspection(
            principal=principal, issue_id=issue_id,
            evidence_id=payload.get("evidence_id"), decision=payload.get("decision"),
            reasons=payload.get("reasons"))
    except AuthorizationError:
        return jsonify({"error": "not_authorized"}), 403
    return jsonify({"status": "evidence_inspection_recorded", "inspection": record}), 201


@app.get(
    "/v1/human-reach/deliveries/<delivery_id>"
)
def human_reach_delivery(
    delivery_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    try:
        delivery = authorize_and_get_fresh_delivery(
            principal=principal,
            delivery_id=delivery_id,
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return jsonify(
        {
            "status": "delivery",
            "delivery": delivery,
        }
    )


@app.post(
    "/v1/human-reach/deliveries/<delivery_id>/delivered"
)
def human_reach_delivered(
    delivery_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    try:
        delivery = authorize_and_mark_delivered(
            principal=principal,
            delivery_id=delivery_id,
            destination_space=payload.get(
                "destination_space"
            ),
            destination_display_name=payload.get(
                "destination_display_name"
            ),
            message_name=payload.get(
                "message_name"
            ),
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return jsonify(
        {
            "status": "delivered",
            "delivery": delivery,
        }
    )


@app.post(
    "/v1/human-reach/deliveries/<delivery_id>/respond"
)
def human_reach_respond(
    delivery_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    try:
        (
            actor_user,
            actor_display_name,
        ) = pseudonymous_responder(
            payload.get("actor_user")
        )
        delivery = authorize_and_record_response(
            principal=principal,
            delivery_id=delivery_id,
            action=payload.get("action"),
            actor_user=actor_user,
            actor_display_name=actor_display_name,
            source_space=payload.get("source_space"),
            source_message=payload.get("source_message"),
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return jsonify(
        {
            "status": "response_recorded",
            "delivery": delivery,
        }
    )


@app.post(
    "/v1/issues/<issue_id>/evidence"
)
def record_evidence(
    issue_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    try:
        result = authorize_and_record_evidence(
            principal=principal,
            issue_id=issue_id,
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return (
        jsonify(
            {
                "status": "evidence_recorded",
                "issue_id": issue_id,
                "state": "VERIFYING",
                "owner": result["owner"],
                "evidence": result["evidence"],
                "transition_event_id": (
                    result["transition_event_id"]
                ),
            }
        ),
        201,
    )


@app.get(
    "/v1/issues/<issue_id>/verification-context"
)
def verification_context(
    issue_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    try:
        result = (
            authorize_and_get_verification_context(
                principal=principal,
                issue_id=issue_id,
            )
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return jsonify(
        {
            "status": "verification_context",
            **result,
        }
    )


@app.post(
    "/v1/issues/<issue_id>/verify"
)
def verify_issue(
    issue_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    evidence_id = payload.get(
        "evidence_id"
    )

    if (
        not isinstance(evidence_id, str)
        or not evidence_id.strip()
    ):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    try:
        result = (
            authorize_and_close_verified_issue(
                principal=principal,
                issue_id=issue_id,
                evidence_id=evidence_id,
            )
        )
    except AuthorizationError:
        return (
            jsonify(
                {"error": "not_authorized"}
            ),
            403,
        )

    return jsonify(
        {
            "status": "verified_closed",
            "issue_id": issue_id,
            "state": "CLOSED",
            "owner": result["owner"],
            "evidence": result["evidence"],
            "transition_event_id": (
                result["transition_event_id"]
            ),
        }
    )


@app.post("/v1/issues/<issue_id>/verification-rejection")
def reject_verification(issue_id: str):
    principal, auth_error = _authenticated_principal()
    if auth_error is not None:
        return auth_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("reason"), str):
        return jsonify({"error": "invalid_request"}), 400

    try:
        result = authorize_and_reject_verification(
            principal=principal,
            issue_id=issue_id,
            reason=payload["reason"],
            evidence_id=payload.get("evidence_id"),
        )
    except AuthorizationError:
        return jsonify({"error": "not_authorized"}), 403

    return jsonify({
        "status": "verification_rejected",
        "issue_id": issue_id,
        "state": "ACTION_PENDING",
        "owner": result["owner"],
        "verification_attempt": result["attempt"],
        "transition_event_id": result["transition_event_id"],
    }), 201


@app.post(
    "/v1/issues/<issue_id>/mutate"
)
def mutate_issue(
    issue_id: str,
):
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

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
    principal, auth_error = (
        _authenticated_principal()
    )

    if auth_error is not None:
        return auth_error

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

    response = {
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

    if "human_reach" in result:
        response["human_reach"] = result[
            "human_reach"
        ]

    return jsonify(response)
