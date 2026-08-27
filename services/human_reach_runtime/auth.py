from __future__ import annotations

import os
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token


CHAT_ISSUER = "chat@system.gserviceaccount.com"
OPERATIONS_ISSUER = "ns-operations-ui@next-shift-506004.iam.gserviceaccount.com"


def _audience() -> str:
    value = os.environ.get(
        "HUMAN_REACH_AUDIENCE",
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            "HUMAN_REACH_AUDIENCE is required"
        )

    return value


def _push_service_account() -> str:
    value = os.environ.get(
        "PUBSUB_PUSH_SERVICE_ACCOUNT",
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            "PUBSUB_PUSH_SERVICE_ACCOUNT is required"
        )

    return value


def _bearer(
    authorization_header: str | None,
) -> str | None:
    if not isinstance(
        authorization_header,
        str,
    ):
        return None

    scheme, separator, token = (
        authorization_header.strip().partition(" ")
    )

    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        return None

    return token.strip()


def _verified_claims(
    authorization_header: str | None,
) -> dict[str, Any] | None:
    token = _bearer(
        authorization_header
    )

    if token is None:
        return None

    try:
        claims = id_token.verify_oauth2_token(
            token,
            GoogleAuthRequest(),
            _audience(),
        )
    except Exception:
        return None

    if not isinstance(
        claims,
        dict,
    ):
        return None

    if claims.get("email_verified") is not True:
        return None

    return claims


def authorize_chat_request(
    authorization_header: str | None,
) -> bool:
    claims = _verified_claims(
        authorization_header
    )

    return bool(
        claims is not None
        and claims.get("email") == CHAT_ISSUER
    )


def authorize_pubsub_request(
    authorization_header: str | None,
) -> bool:
    claims = _verified_claims(
        authorization_header
    )

    return bool(
        claims is not None
        and claims.get("email")
        == _push_service_account()
    )


def authorize_operations_request(
    authorization_header: str | None,
) -> bool:
    claims = _verified_claims(
        authorization_header
    )

    return bool(
        claims is not None
        and claims.get("email") == OPERATIONS_ISSUER
    )
