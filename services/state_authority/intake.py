from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud import pubsub_v1

from audit import emit_security_event
from policy import INTAKE_OWNERS
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"
HANDOVER_TOPIC = "next-shift-handover-received"
HANDOVER_EVENT_TYPE = "handover.issue.received"
HANDOVER_EVENT_VERSION = "1.0"
INTAKE_CAPABILITY = "intake.create"

ALLOWED_PROPOSAL_FIELDS = frozenset(
    {
        "title",
        "description",
        "owner",
        "workflow_input",
        "human_approval_required",
    }
)


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


def _validated_text(
    value: Any,
    *,
    field: str,
    maximum: int,
) -> str:
    if not isinstance(value, str):
        raise AuthorizationError(
            reason="invalid_intake_value",
            details={"field": field},
        )

    cleaned = value.strip()

    if (
        not cleaned
        or len(cleaned) > maximum
        or any(
            ord(char) < 32
            and char not in "\n\r\t"
            for char in cleaned
        )
    ):
        raise AuthorizationError(
            reason="invalid_intake_value",
            details={"field": field},
        )

    return cleaned


def _validate_proposal(
    proposal: dict[str, Any],
) -> dict[str, Any]:
    extra_fields = (
        set(proposal)
        - ALLOWED_PROPOSAL_FIELDS
    )

    if extra_fields:
        raise AuthorizationError(
            reason="intake_field_not_authorized",
            details={
                "fields": sorted(extra_fields),
            },
        )

    title = _validated_text(
        proposal.get("title"),
        field="title",
        maximum=200,
    )
    description = _validated_text(
        proposal.get("description"),
        field="description",
        maximum=4000,
    )
    owner = _validated_text(
        proposal.get("owner"),
        field="owner",
        maximum=64,
    )

    if owner not in INTAKE_OWNERS:
        raise AuthorizationError(
            reason="invalid_intake_owner",
            target_owner=owner,
        )

    workflow_input = proposal.get(
        "workflow_input",
        {},
    )

    if not isinstance(workflow_input, dict):
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        )

    try:
        serialized_workflow_input = json.dumps(
            workflow_input,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        ) from exc

    if len(serialized_workflow_input) > 8000:
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        )

    human_approval_required = proposal.get(
        "human_approval_required",
        False,
    )

    if not isinstance(
        human_approval_required,
        bool,
    ):
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "human_approval_required",
            },
        )

    return {
        "title": title,
        "description": description,
        "owner": owner,
        "workflow_input": dict(workflow_input),
        "human_approval_required": (
            human_approval_required
        ),
    }


def _publish_received(
    issue: dict[str, Any],
) -> dict[str, str]:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        PROJECT_ID,
        HANDOVER_TOPIC,
    )

    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": HANDOVER_EVENT_TYPE,
        "event_version": HANDOVER_EVENT_VERSION,
        "occurred_at": _now_iso(),
        "issue_id": issue["id"],
        "owner": issue["owner"],
        "state": issue["state"],
        "source_type": issue["source_type"],
        "source_reference": issue[
            "source_reference"
        ],
        "workflow_input": dict(
            issue.get(
                "workflow_input",
                {},
            )
        ),
    }

    future = publisher.publish(
        topic_path,
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8"),
        event_type=HANDOVER_EVENT_TYPE,
        event_version=HANDOVER_EVENT_VERSION,
        issue_id=issue["id"],
        owner=issue["owner"],
    )

    return {
        "event_id": event_id,
        "message_id": future.result(),
    }


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
        validated = _validate_proposal(
            proposal
        )
        validated_source_type = _validated_text(
            source_type,
            field="source_type",
            maximum=64,
        )
        validated_source_reference = (
            _validated_text(
                source_reference,
                field="source_reference",
                maximum=200,
            )
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
    db = _db()
    doc_ref = (
        db
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
        event = _publish_received(issue)
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
