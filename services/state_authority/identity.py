from __future__ import annotations

from typing import Any

from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token

from security import AuthenticationError


def verified_principal(
    authorization_header: str | None,
    *,
    audience: str,
) -> tuple[str, dict[str, Any]]:
    if not authorization_header:
        raise AuthenticationError(
            "Authentication required"
        )

    parts = authorization_header.split(" ", 1)

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
        or not parts[1].strip()
    ):
        raise AuthenticationError(
            "Authentication required"
        )

    token = parts[1].strip()

    try:
        claims = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            audience=audience,
        )
    except GoogleAuthError as exc:
        raise AuthenticationError(
            "Authentication required"
        ) from exc
    except ValueError as exc:
        raise AuthenticationError(
            "Authentication required"
        ) from exc

    email = claims.get("email")

    if (
        not isinstance(email, str)
        or not email.endswith(
            ".iam.gserviceaccount.com"
        )
    ):
        raise AuthenticationError(
            "Authentication required"
        )

    if claims.get("email_verified") is not True:
        raise AuthenticationError(
            "Authentication required"
        )

    return email, claims
