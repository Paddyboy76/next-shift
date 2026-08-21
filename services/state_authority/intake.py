from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from intake_dispatch import publish_received
from intake_validation import (
    validate_proposal,
    validate_source,
)
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"
INTAKE_CAPABILITY = "intake.create"


def _now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _db() -> firestore.Client:
    return firestore.Client(
        project=PROJECT_ID
    )


def _emit_denial(
    *,
    error: AuthorizationError,
    principal: str,
    target_owner: str = "UNKNOWN",
) -> None:
    emit_security_event(
        decision="DENY",
        principal=principal,
        capability=INTAKE_CAPABILITY,
        issue_id="pending",
        target_owner=(
            target_owner
            if target_owner != "UNKNOWN"
            else error.target_owner
        ),
        reason=error.reason,
        details=error.details,
    )


def _authorize_intake(
    *,
    principal: str,
    target_owner: str,
) -> None:
    principal_policy = (
        PRINCIPAL_POLICIES.get(
            principal
        )
    )

    if principal_policy is None:
        error = AuthorizationError(
            reason="unknown_principal",
            target_owner=target_owner,
        )
        _emit_denial(
            error=error,
            principal=principal,
            target_owner=target_owner,
        )
        raise error

    if (
        INTAKE_CAPABILITY
        not in principal_policy.capabilities
    ):
        error = AuthorizationError(
            reason="capability_denied",
            target_owner=target_owner,
        )
        _emit_denial(
            error=error,
            principal=principal,
            target_owner=target_owner,
        )
        raise error

    if principal_policy.owner != "Intake":
        error = AuthorizationError(
            reason="principal_capability_owner_mismatch",
            target_owner=target_owner,
        )
        _emit_denial(
            error=error,
            principal=principal,
            target_owner=target_owner,
        )
        raise error


def authorize_and_create(
    *,
    principal: str,
    proposal: dict[str, Any],
    source_type: str,
    source_reference: str,
) -> dict[str, Any]:
    if not isinstance(proposal, dict):
        error = AuthorizationError(
            reason="invalid_intake_value",
            details={"field": "proposal"},
        )
        _emit_denial(
            error=error,
            principal=principal,
        )
        raise error

    try:
        validated = validate_proposal(
            proposal
        )
        (
            validated_source_type,
            validated_source_reference,
        ) = validate_source(
            source_type=source_type,
            source_reference=source_reference,
        )
    except AuthorizationError as error:
        _emit_denial(
            error=error,
            principal=principal,
            target_owner=str(
                proposal.get(
                    "owner",
                    "UNKNOWN",
                )
            ),
        )
        raise

    owner = validated["owner"]

    _authorize_intake(
        principal=principal,
        target_owner=owner,
    )

    now = _now_iso()
    doc_ref = (
        _db()
        .collection(ISSUE_COLLECTION)
        .document()
    )

    issue = {
        "id": doc_ref.id,
        "title": validated["title"],
        "description": validated[
            "description"
        ],
        "source_type": validated_source_type,
        "source_reference": (
            validated_source_reference
        ),
        "owner": owner,
        "workflow_input": validated[
            "workflow_input"
        ],
        "human_approval_required": validated[
            "human_approval_required"
        ],
        "state": "RECEIVED",
        "created_at": now,
        "updated_at": now,
        "history": [
            {
                "from": None,
                "to": "RECEIVED",
                "at": now,
                "actor": principal,
                "reason": (
                    "Issue created through State Authority"
                ),
            }
        ],
        "intake_principal": principal,
        "dispatch_status": "PENDING",
    }

    doc_ref.set(issue)

    try:
        event = publish_received(issue)
    except Exception as exc:
        doc_ref.update(
            {
                "dispatch_status": "FAILED",
                "dispatch_error": (
                    type(exc).__name__
                ),
                "updated_at": _now_iso(),
            }
        )
        raise

    event_updates = {
        "handover_received_event_id": (
            event["event_id"]
        ),
        "handover_received_message_id": (
            event["message_id"]
        ),
        "dispatch_status": "PUBLISHED",
        "updated_at": _now_iso(),
    }

    doc_ref.update(event_updates)
    issue.update(event_updates)

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=INTAKE_CAPABILITY,
        issue_id=issue["id"],
        target_owner=owner,
        reason="authorized",
    )

    return issue
