from __future__ import annotations

from typing import Any


class SecurityError(Exception):
    pass


class AuthenticationError(SecurityError):
    pass


class AuthorizationError(SecurityError):
    def __init__(
        self,
        *,
        reason: str,
        target_owner: str = "UNKNOWN",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("Not authorized")
        self.reason = reason
        self.target_owner = target_owner
        self.details = details or {}
