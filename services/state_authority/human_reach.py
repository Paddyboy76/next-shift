from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from human_reach_contract import DELIVERY_COLLECTION
from human_reach_contract import build_delivery_request
from human_reach_dispatch import publish_delivery_request
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"
READ_CAPABILITY = "human_reach.read_delivery"
UPDATE_CAPABILITY = "human_reach.delivery_update"
EXPECTED_OWNER = "HumanReach"

ALLOWED_ACTIONS = frozenset(
    {
        "acknowledge",
        "blocked",
        "completed",
    }
)

ACTION_STATUS = {
    "acknowledge": "ACKNOWLEDGED",
    "blocked": "BLOCKED",
    "completed": "COMPLETION_CLAIMED",
}


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deny(
    *,
    error: AuthorizationError,
    principal: str,
    capability: str,
    delivery_id: str,
    target_owner: str = "UNKNOWN",
) -> None:
    emit_security_event(
        decision="DENY",
        principal=principal,
        capability=capability,
        issue_id=delivery_id,
        target_owner=(
            error.target_owner
            if error.target_owner != "UNKNOWN"
            else target_owner
        ),
        reason=error.reason,
        details=error.details,
    )


def _authorize(
    *,
    principal: str,
    capability: str,
    delivery_id: str,
) -> None:
    policy = PRINCIPAL_POLICIES.get(principal)

    if policy is None:
        error = AuthorizationError(reason="unknown_principal")
        _deny(
            error=error,
            principal=principal,
            capability=capability,
            delivery_id=delivery_id,
        )
        raise error

    if capability not in policy.capabilities:
        error = AuthorizationError(reason="capability_denied")
        _deny(
            error=error,
            principal=principal,
            capability=capability,
            delivery_id=delivery_id,
        )
        raise error

    if policy.owner != EXPECTED_OWNER:
        error = AuthorizationError(
            reason="principal_capability_owner_mismatch"
        )
        _deny(
            error=error,
            principal=principal,
            capability=capability,
            delivery_id=delivery_id,
        )
        raise error


def _clean_text(
    value: Any,
    *,
    field: str,
    maximum: int = 500,
) -> str:
    if not isinstance(value, str):
        raise AuthorizationError(
            reason="invalid_human_reach_value",
            details={"field": field},
        )

    cleaned = value.strip()

    if not cleaned or len(cleaned) > maximum:
        raise AuthorizationError(
            reason="invalid_human_reach_value",
            details={"field": field},
        )

    return cleaned


def stage_delivery_request(
    *,
    transaction: firestore.Transaction,
    db: firestore.Client,
    issue_id: str,
    issue: dict[str, Any],
    requested_at: str,
) -> dict[str, Any]:
    delivery = build_delivery_request(
        issue_id=issue_id,
        issue=issue,
        requested_at=requested_at,
    )

    delivery_ref = (
        db.collection(DELIVERY_COLLECTION)
        .document(delivery["delivery_id"])
    )

    transaction.set(
        delivery_ref,
        delivery,
    )

    return delivery


def dispatch_staged_delivery(
    delivery: dict[str, Any],
) -> dict[str, Any]:
    delivery_id = str(delivery["delivery_id"])
    ref = (
        _db().collection(DELIVERY_COLLECTION)
        .document(delivery_id)
    )

    try:
        event = publish_delivery_request(delivery)
    except Exception as exc:
        ref.update(
            {
                "event_dispatch_status": "FAILED",
                "event_dispatch_error": type(exc).__name__,
                "event_dispatch_updated_at": _now_iso(),
            }
        )

        return {
            "delivery_id": delivery_id,
            "event_dispatch_status": "FAILED",
            "event_dispatch_error": type(exc).__name__,
        }

    updates = {
        "event_dispatch_status": "PUBLISHED",
        "human_reach_event_id": event["event_id"],
        "human_reach_message_id": event["message_id"],
        "event_dispatch_updated_at": _now_iso(),
    }
    ref.update(updates)

    return {
        "delivery_id": delivery_id,
        **updates,
    }


def ensure_delivery_for_action_pending(
    *,
    issue_id: str,
) -> dict[str, Any]:
    db = _db()
    issue_ref = db.collection(ISSUE_COLLECTION).document(issue_id)
    delivery_ref = db.collection(DELIVERY_COLLECTION).document(issue_id)
    transaction = db.transaction()

    @firestore.transactional
    def _ensure(tx: firestore.Transaction) -> dict[str, Any]:
        issue_snapshot = issue_ref.get(transaction=tx)
        delivery_snapshot = delivery_ref.get(transaction=tx)

        if not issue_snapshot.exists:
            raise AuthorizationError(reason="issue_not_found")

        issue = issue_snapshot.to_dict() or {}
        owner = str(issue.get("owner", "UNKNOWN"))

        if issue.get("state") != "ACTION_PENDING":
            raise AuthorizationError(
                reason="human_reach_issue_state_mismatch",
                target_owner=owner,
                details={
                    "expected": "ACTION_PENDING",
                    "current": issue.get("state"),
                },
            )

        if delivery_snapshot.exists:
            return delivery_snapshot.to_dict() or {}

        delivery = build_delivery_request(
            issue_id=issue_id,
            issue=issue,
            requested_at=_now_iso(),
        )
        tx.set(delivery_ref, delivery)
        return delivery

    delivery = _ensure(transaction)

    if delivery.get("event_dispatch_status") == "PUBLISHED":
        return {
            "delivery_id": issue_id,
            "event_dispatch_status": "PUBLISHED",
            "reused": True,
        }

    dispatch = dispatch_staged_delivery(delivery)
    dispatch["reused"] = bool(
        delivery.get("event_dispatch_status")
        not in {None, "PENDING"}
    )
    return dispatch


def authorize_and_get_delivery(
    *,
    principal: str,
    delivery_id: str,
) -> dict[str, Any]:
    _authorize(
        principal=principal,
        capability=READ_CAPABILITY,
        delivery_id=delivery_id,
    )

    snapshot = (
        _db().collection(DELIVERY_COLLECTION)
        .document(delivery_id)
        .get()
    )

    if not snapshot.exists:
        error = AuthorizationError(reason="delivery_not_found")
        _deny(
            error=error,
            principal=principal,
            capability=READ_CAPABILITY,
            delivery_id=delivery_id,
        )
        raise error

    delivery = snapshot.to_dict() or {}

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=READ_CAPABILITY,
        issue_id=str(delivery.get("issue_id", delivery_id)),
        target_owner=str(delivery.get("owner", "UNKNOWN")),
        reason="human_reach_delivery_read",
        details={"delivery_id": delivery_id},
    )

    return delivery


def authorize_and_mark_delivered(
    *,
    principal: str,
    delivery_id: str,
    destination_space: str,
    destination_display_name: str,
    message_name: str,
) -> dict[str, Any]:
    _authorize(
        principal=principal,
        capability=UPDATE_CAPABILITY,
        delivery_id=delivery_id,
    )

    destination_space = _clean_text(
        destination_space,
        field="destination_space",
        maximum=200,
    )
    destination_display_name = _clean_text(
        destination_display_name,
        field="destination_display_name",
        maximum=200,
    )
    message_name = _clean_text(
        message_name,
        field="message_name",
        maximum=300,
    )

    db = _db()
    ref = db.collection(DELIVERY_COLLECTION).document(delivery_id)
    transaction = db.transaction()

    @firestore.transactional
    def _mark(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = ref.get(transaction=tx)

        if not snapshot.exists:
            raise AuthorizationError(reason="delivery_not_found")

        delivery = snapshot.to_dict() or {}
        status = delivery.get("delivery_status")

        if status == "DELIVERED":
            if (
                delivery.get("destination_space") == destination_space
                and delivery.get("chat_message_name") == message_name
            ):
                return delivery

            raise AuthorizationError(
                reason="delivery_destination_mismatch",
                target_owner=str(delivery.get("owner", "UNKNOWN")),
            )

        if status != "PENDING":
            raise AuthorizationError(
                reason="delivery_state_mismatch",
                target_owner=str(delivery.get("owner", "UNKNOWN")),
                details={
                    "expected": "PENDING",
                    "current": status,
                },
            )

        now = _now_iso()
        updates = {
            "delivery_status": "DELIVERED",
            "destination_space": destination_space,
            "destination_display_name": destination_display_name,
            "chat_message_name": message_name,
            "delivered_at": now,
            "last_delivery_update_at": now,
        }
        tx.update(ref, updates)
        delivery.update(updates)
        return delivery

    try:
        result = _mark(transaction)
    except AuthorizationError as error:
        _deny(
            error=error,
            principal=principal,
            capability=UPDATE_CAPABILITY,
            delivery_id=delivery_id,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=UPDATE_CAPABILITY,
        issue_id=str(result.get("issue_id", delivery_id)),
        target_owner=str(result.get("owner", "UNKNOWN")),
        reason="human_reach_delivered",
        details={
            "delivery_id": delivery_id,
            "destination_space": destination_space,
        },
    )

    return result


def authorize_and_record_response(
    *,
    principal: str,
    delivery_id: str,
    action: str,
    actor_user: str,
    actor_display_name: str,
    source_space: str,
    source_message: str,
) -> dict[str, Any]:
    _authorize(
        principal=principal,
        capability=UPDATE_CAPABILITY,
        delivery_id=delivery_id,
    )

    action = _clean_text(
        action,
        field="action",
        maximum=40,
    ).lower()

    if action not in ALLOWED_ACTIONS:
        error = AuthorizationError(
            reason="human_reach_action_not_allowed",
            details={"action": action},
        )
        _deny(
            error=error,
            principal=principal,
            capability=UPDATE_CAPABILITY,
            delivery_id=delivery_id,
        )
        raise error

    actor_user = _clean_text(
        actor_user,
        field="actor_user",
        maximum=200,
    )
    actor_display_name = _clean_text(
        actor_display_name,
        field="actor_display_name",
        maximum=200,
    )
    source_space = _clean_text(
        source_space,
        field="source_space",
        maximum=200,
    )
    source_message = _clean_text(
        source_message,
        field="source_message",
        maximum=300,
    )

    db = _db()
    ref = db.collection(DELIVERY_COLLECTION).document(delivery_id)
    transaction = db.transaction()

    @firestore.transactional
    def _record(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = ref.get(transaction=tx)

        if not snapshot.exists:
            raise AuthorizationError(reason="delivery_not_found")

        delivery = snapshot.to_dict() or {}
        owner = str(delivery.get("owner", "UNKNOWN"))

        if delivery.get("destination_space") != source_space:
            raise AuthorizationError(
                reason="human_reach_source_space_mismatch",
                target_owner=owner,
            )

        if delivery.get("chat_message_name") != source_message:
            raise AuthorizationError(
                reason="human_reach_source_message_mismatch",
                target_owner=owner,
            )

        current = str(delivery.get("delivery_status", "UNKNOWN"))
        target = ACTION_STATUS[action]

        if current == target:
            return delivery

        allowed_from = {
            "acknowledge": {"DELIVERED"},
            "blocked": {"DELIVERED", "ACKNOWLEDGED"},
            "completed": {"DELIVERED", "ACKNOWLEDGED"},
        }[action]

        if current not in allowed_from:
            raise AuthorizationError(
                reason="human_reach_response_state_mismatch",
                target_owner=owner,
                details={
                    "action": action,
                    "current": current,
                },
            )

        history = delivery.get("response_history", [])

        if not isinstance(history, list):
            raise AuthorizationError(
                reason="human_reach_history_invalid",
                target_owner=owner,
            )

        now = _now_iso()
        entry = {
            "action": action,
            "from_status": current,
            "to_status": target,
            "at": now,
            "actor_user": actor_user,
            "actor_display_name": actor_display_name,
        }

        updates = {
            "delivery_status": target,
            "response_history": [*history, entry],
            "last_response_action": action,
            "last_response_at": now,
            "last_response_user": actor_user,
            "last_response_display_name": actor_display_name,
            "last_delivery_update_at": now,
        }

        tx.update(ref, updates)
        delivery.update(updates)
        return delivery

    try:
        result = _record(transaction)
    except AuthorizationError as error:
        _deny(
            error=error,
            principal=principal,
            capability=UPDATE_CAPABILITY,
            delivery_id=delivery_id,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=UPDATE_CAPABILITY,
        issue_id=str(result.get("issue_id", delivery_id)),
        target_owner=str(result.get("owner", "UNKNOWN")),
        reason="human_reach_response_recorded",
        details={
            "delivery_id": delivery_id,
            "action": action,
            "delivery_status": result.get("delivery_status"),
            "actor_user": actor_user,
        },
    )

    return result
