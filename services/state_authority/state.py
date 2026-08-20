from __future__ import annotations

from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from policy import (
    CAPABILITY_POLICIES,
    PRINCIPAL_POLICIES,
)
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"


def _db() -> firestore.Client:
    return firestore.Client(
        project=PROJECT_ID
    )


def authorize_and_update(
    *,
    principal: str,
    issue_id: str,
    capability: str,
    expected_state: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    principal_policy = (
        PRINCIPAL_POLICIES.get(principal)
    )

    capability_policy = (
        CAPABILITY_POLICIES.get(capability)
    )

    if capability_policy is None:
        error = AuthorizationError(
            reason="unknown_capability",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    if principal_policy is None:
        error = AuthorizationError(
            reason="unknown_principal",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    if (
        capability
        not in principal_policy.capabilities
    ):
        error = AuthorizationError(
            reason="capability_denied",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    if (
        principal_policy.owner
        != capability_policy.owner
    ):
        error = AuthorizationError(
            reason="principal_capability_owner_mismatch",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    if not updates:
        error = AuthorizationError(
            reason="empty_mutation",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    update_fields = set(
        updates.keys()
    )

    unauthorized_fields = (
        update_fields
        - capability_policy.allowed_update_fields
    )

    if unauthorized_fields:
        error = AuthorizationError(
            reason="field_not_authorized",
            details={
                "fields": sorted(
                    unauthorized_fields
                )
            },
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    db = _db()

    doc_ref = (
        db
        .collection(ISSUE_COLLECTION)
        .document(issue_id)
    )

    transaction = db.transaction()

    @firestore.transactional
    def _mutate(
        tx: firestore.Transaction,
    ) -> dict[str, Any]:
        snapshot = doc_ref.get(
            transaction=tx
        )

        if not snapshot.exists:
            raise AuthorizationError(
                reason="issue_not_found",
            )

        issue = snapshot.to_dict()

        owner = str(
            issue.get(
                "owner",
                "UNKNOWN",
            )
        )

        if owner != principal_policy.owner:
            raise AuthorizationError(
                reason="owner_mismatch",
                target_owner=owner,
            )

        current_state = issue.get(
            "state"
        )

        if current_state != expected_state:
            raise AuthorizationError(
                reason="state_mismatch",
                target_owner=owner,
                details={
                    "expected_state": expected_state,
                    "current_state": current_state,
                },
            )

        safe_updates = dict(updates)

        safe_updates["updated_at"] = (
            firestore.SERVER_TIMESTAMP
        )

        tx.update(
            doc_ref,
            safe_updates,
        )

        return {
            "owner": owner,
        }

    try:
        result = _mutate(transaction)
    except AuthorizationError as error:
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=capability,
        issue_id=issue_id,
        target_owner=result["owner"],
        reason="authorized",
    )

    return result


def _emit_denial(
    *,
    error: AuthorizationError,
    principal: str,
    capability: str,
    issue_id: str,
) -> None:
    emit_security_event(
        decision="DENY",
        principal=principal,
        capability=capability,
        issue_id=issue_id,
        target_owner=error.target_owner,
        reason=error.reason,
        details=error.details,
    )
