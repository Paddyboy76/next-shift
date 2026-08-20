from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from policy import (
    CAPABILITY_POLICIES,
    FACILITY_TEAM_BY_TYPE,
    PRINCIPAL_POLICIES,
    CapabilityPolicy,
    PrincipalPolicy,
)
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"
TRANSITION_COLLECTION = "issue_transition_events"

WORK_ORDER_PATTERN = re.compile(
    r"^FAC-[A-F0-9]{8}$"
)


def _db() -> firestore.Client:
    return firestore.Client(
        project=PROJECT_ID
    )


def _authority_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def _authorize_capability(
    *,
    principal: str,
    capability: str,
    issue_id: str,
) -> tuple[
    PrincipalPolicy,
    CapabilityPolicy,
]:
    capability_policy = (
        CAPABILITY_POLICIES.get(
            capability
        )
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

    principal_policy = (
        PRINCIPAL_POLICIES.get(
            principal
        )
    )

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
            reason=(
                "principal_capability_owner_mismatch"
            ),
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    return (
        principal_policy,
        capability_policy,
    )


def _validate_text(
    value: Any,
    *,
    field: str,
    maximum: int,
) -> str:
    if not isinstance(value, str):
        raise AuthorizationError(
            reason="invalid_update_value",
            details={
                "field": field,
            },
        )

    cleaned = value.strip()

    if (
        not cleaned
        or len(cleaned) > maximum
        or any(
            ord(char) < 32
            for char in cleaned
        )
    ):
        raise AuthorizationError(
            reason="invalid_update_value",
            details={
                "field": field,
            },
        )

    return cleaned


def _validate_facilities_updates(
    updates: dict[str, Any],
) -> None:
    if "facility_type" in updates:
        facility_type = _validate_text(
            updates["facility_type"],
            field="facility_type",
            maximum=64,
        )

        if (
            facility_type
            not in FACILITY_TEAM_BY_TYPE
        ):
            raise AuthorizationError(
                reason="invalid_update_value",
                details={
                    "field": "facility_type",
                },
            )

    if "facilities_location" in updates:
        _validate_text(
            updates["facilities_location"],
            field="facilities_location",
            maximum=200,
        )

    if "facilities_work_order_id" in updates:
        work_order_id = _validate_text(
            updates[
                "facilities_work_order_id"
            ],
            field="facilities_work_order_id",
            maximum=32,
        )

        if not WORK_ORDER_PATTERN.fullmatch(
            work_order_id
        ):
            raise AuthorizationError(
                reason="invalid_update_value",
                details={
                    "field": (
                        "facilities_work_order_id"
                    ),
                },
            )

    if "facilities_team_id" in updates:
        _validate_text(
            updates["facilities_team_id"],
            field="facilities_team_id",
            maximum=64,
        )

    if "facilities_team_name" in updates:
        _validate_text(
            updates[
                "facilities_team_name"
            ],
            field="facilities_team_name",
            maximum=128,
        )

    if "facilities_status" in updates:
        status = _validate_text(
            updates["facilities_status"],
            field="facilities_status",
            maximum=64,
        )

        if status not in {
            "ASSIGNED",
            "REPAIR_PENDING",
        }:
            raise AuthorizationError(
                reason="invalid_update_value",
                details={
                    "field": "facilities_status",
                },
            )

    facility_type = updates.get(
        "facility_type"
    )

    if facility_type is not None:
        expected_team = (
            FACILITY_TEAM_BY_TYPE[
                facility_type
            ]
        )

        team_id = updates.get(
            "facilities_team_id"
        )
        team_name = updates.get(
            "facilities_team_name"
        )

        if (
            team_id is not None
            and team_id != expected_team[0]
        ):
            raise AuthorizationError(
                reason="facilities_team_mismatch",
            )

        if (
            team_name is not None
            and team_name != expected_team[1]
        ):
            raise AuthorizationError(
                reason="facilities_team_mismatch",
            )


def _validate_updates(
    *,
    capability: str,
    updates: dict[str, Any],
) -> None:
    if capability == "facilities.coordinate":
        _validate_facilities_updates(
            updates
        )


def authorize_and_update(
    *,
    principal: str,
    issue_id: str,
    capability: str,
    expected_state: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    (
        principal_policy,
        capability_policy,
    ) = _authorize_capability(
        principal=principal,
        capability=capability,
        issue_id=issue_id,
    )

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

    unauthorized_fields = (
        set(updates)
        - capability_policy.allowed_update_fields
    )

    if unauthorized_fields:
        error = AuthorizationError(
            reason="field_not_authorized",
            details={
                "fields": sorted(
                    unauthorized_fields
                ),
            },
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    try:
        _validate_updates(
            capability=capability,
            updates=updates,
        )
    except AuthorizationError as error:
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise

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
        result = _mutate(
            transaction
        )
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


def authorize_and_transition(
    *,
    principal: str,
    issue_id: str,
    capability: str,
    expected_state: str,
    new_state: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    (
        principal_policy,
        capability_policy,
    ) = _authorize_capability(
        principal=principal,
        capability=capability,
        issue_id=issue_id,
    )

    transition_policy = (
        capability_policy.transitions.get(
            (
                expected_state,
                new_state,
            )
        )
    )

    if transition_policy is None:
        error = AuthorizationError(
            reason="transition_not_authorized",
            details={
                "from": expected_state,
                "to": new_state,
            },
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    update_fields = set(
        updates
    )

    unauthorized_fields = (
        update_fields
        - transition_policy.allowed_update_fields
    )

    if unauthorized_fields:
        error = AuthorizationError(
            reason="field_not_authorized",
            details={
                "fields": sorted(
                    unauthorized_fields
                ),
            },
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    missing_fields = (
        transition_policy.required_update_fields
        - update_fields
    )

    if missing_fields:
        error = AuthorizationError(
            reason="required_field_missing",
            details={
                "fields": sorted(
                    missing_fields
                ),
            },
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    if (
        not isinstance(reason, str)
        or not reason.strip()
        or len(reason.strip()) > 500
    ):
        error = AuthorizationError(
            reason="invalid_transition_reason",
        )
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise error

    try:
        _validate_updates(
            capability=capability,
            updates=updates,
        )
    except AuthorizationError as error:
        _emit_denial(
            error=error,
            principal=principal,
            capability=capability,
            issue_id=issue_id,
        )
        raise

    db = _db()

    doc_ref = (
        db
        .collection(ISSUE_COLLECTION)
        .document(issue_id)
    )

    transition_ref = (
        db
        .collection(
            TRANSITION_COLLECTION
        )
        .document()
    )

    transaction = db.transaction()

    @firestore.transactional
    def _transition(
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

        history = issue.get(
            "history",
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            raise AuthorizationError(
                reason="invalid_history",
                target_owner=owner,
            )

        observed_at = _authority_now()

        history_entry = {
            "from": current_state,
            "to": new_state,
            "at": observed_at,
            "actor": principal,
            "reason": reason.strip(),
        }

        updated_history = [
            *history,
            history_entry,
        ]

        safe_updates = dict(
            updates
        )

        safe_updates.update(
            {
                "state": new_state,
                "history": updated_history,
                "updated_at": (
                    firestore.SERVER_TIMESTAMP
                ),
                "last_transition_at": (
                    firestore.SERVER_TIMESTAMP
                ),
            }
        )

        tx.update(
            doc_ref,
            safe_updates,
        )

        tx.set(
            transition_ref,
            {
                "id": transition_ref.id,
                "issue_id": issue_id,
                "owner": owner,
                "principal": principal,
                "capability": capability,
                "from_state": current_state,
                "to_state": new_state,
                "reason": reason.strip(),
                "update_fields": sorted(
                    updates
                ),
                "authority_observed_at": (
                    observed_at
                ),
                "committed_at": (
                    firestore.SERVER_TIMESTAMP
                ),
            },
        )

        return {
            "owner": owner,
            "from_state": current_state,
            "to_state": new_state,
            "transition_event_id": (
                transition_ref.id
            ),
        }

    try:
        result = _transition(
            transaction
        )
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
        reason="transition_authorized",
        details={
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
        },
    )

    return result
