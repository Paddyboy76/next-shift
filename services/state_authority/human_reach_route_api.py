from __future__ import annotations

import os
from typing import Any

from flask import Blueprint
from flask import jsonify
from flask import request

from human_reach_routes import authorize_and_deactivate_route
from human_reach_routes import authorize_and_register_route
from human_reach_routes import authorize_and_resolve_route
from identity import verified_principal
from security import AuthenticationError
from security import AuthorizationError


blueprint = Blueprint("human_reach_routes", __name__)


def _audience() -> str:
    audience = os.environ.get("STATE_AUTHORITY_AUDIENCE")

    if not audience:
        raise RuntimeError("STATE_AUTHORITY_AUDIENCE is required")

    return audience


def _authenticated_principal():
    try:
        principal, _claims = verified_principal(
            request.headers.get("Authorization"),
            audience=_audience(),
        )
        return principal, None
    except AuthenticationError:
        return None, (
            jsonify({"error": "authentication_required"}),
            401,
        )


def _route_error(error: AuthorizationError):
    if error.reason == "human_reach_route_not_registered":
        return jsonify({"error": "route_not_registered"}), 404

    if error.reason == "human_reach_route_conflict":
        return jsonify({"error": "route_conflict"}), 409

    return jsonify({"error": "not_authorized"}), 403


@blueprint.post("/v1/human-reach/routes/register")
def register_route():
    principal, auth_error = _authenticated_principal()

    if auth_error is not None:
        return auth_error

    payload: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400

    try:
        route = authorize_and_register_route(
            principal=principal,
            display_name=payload.get("display_name"),
            space_name=payload.get("space_name"),
        )
    except AuthorizationError as error:
        return _route_error(error)

    return jsonify(
        {
            "status": "route_registered",
            "route": route,
        }
    )


@blueprint.get("/v1/human-reach/routes/resolve")
def resolve_route():
    principal, auth_error = _authenticated_principal()

    if auth_error is not None:
        return auth_error

    try:
        route = authorize_and_resolve_route(
            principal=principal,
            display_name=request.args.get("display_name"),
        )
    except AuthorizationError as error:
        return _route_error(error)

    return jsonify(
        {
            "status": "route_resolved",
            "route": route,
        }
    )


@blueprint.post("/v1/human-reach/routes/deactivate")
def deactivate_route():
    principal, auth_error = _authenticated_principal()

    if auth_error is not None:
        return auth_error

    payload: dict[str, Any] | None = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400

    try:
        route = authorize_and_deactivate_route(
            principal=principal,
            display_name=payload.get("display_name"),
            space_name=payload.get("space_name"),
        )
    except AuthorizationError as error:
        return _route_error(error)

    return jsonify(
        {
            "status": "route_deactivated",
            "route": route,
        }
    )
