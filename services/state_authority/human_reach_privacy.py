from __future__ import annotations

import hashlib
from typing import Any

from security import AuthorizationError


def pseudonymous_responder(
    actor_user: Any,
) -> tuple[str, str]:
    if not isinstance(actor_user, str) or not actor_user.strip():
        raise AuthorizationError(
            reason="human_reach_actor_invalid"
        )

    digest = hashlib.sha256(
        actor_user.strip().encode("utf-8")
    ).hexdigest()[:20]

    return (
        f"chat-user-{digest}",
        "Frontline responder",
    )
