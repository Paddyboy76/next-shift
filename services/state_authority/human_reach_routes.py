from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ROUTE_COLLECTION = "human_reach_routes"
READ_CAPABILITY = "human_reach.read_delivery"
UPDATE_CAPABILITY = "human_reach.delivery_update"
EXPECTED_OWNER = "HumanReach"

ROUTE_IDS = {
    "Next Shift - Facilities Ops": "facilities-ops",
    "Next Shift - Patient Flow": "patient-flow",
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
    route_id: str,
    display_name: str = "UNKNOWN",
) -> None:
    emit_security_event(
        decision="DENY",
        principal=principal,
        capability=capability,
        issue_id=f"human-reach-route:{route_id}",
        target_owner="HumanReach",
        reason=error.reason,
        details={
            "route_id": route_id,
            "display_name": display_name,
            **error.details,
        },
    )


def _authorize(
    *,
    principal: str,
    capability: str,
    route_id: str,
    display_name: str = "UNKNOWN",
) -> None:
    policy = PRINCIPAL_POLICIES.get(principal)

    if policy is None:
        error = AuthorizationError(reason="unknown_principal")
        _deny(
            error=error,
            principal=principal,
            capability=capability,
            route_id=route_id,
            display_name=display_name,
        )
        raise error

    if capability not in policy.capabilities:
        error = AuthorizationError(reason="capability_denied")
        _deny(
            error=error,
            principal=principal,
            capability=capability,
            route_id=route_id,
            display_name=display_name,
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
            route_id=route_id,
            display_name=display_name,
        )
        raise error


def route_id_for_display_name(display_name: Any) -> str:
    if not isinstance(display_name, str):
        raise AuthorizationError(
            reason="human_reach_route_not_allowed"
        )

    cleaned = display_name.strip()
    route_id = ROUTE_IDS.get(cleaned)

    if route_id is None:
        raise AuthorizationError(
            reason="human_reach_route_not_allowed",
            details={"display_name": cleaned[:200]},
        )

    return route_id


def _space_name(value: Any) -> str:
    if not isinstance(value, str):
        raise AuthorizationError(
            reason="invalid_human_reach_space"
        )

    cleaned = value.strip()

    if (
        not cleaned.startswith("spaces/")
        or len(cleaned) > 200
        or cleaned.count("/") != 1
    ):
        raise AuthorizationError(
            reason="invalid_human_reach_space"
        )

    return cleaned


def authorize_and_register_route(
    *,
    principal: str,
    display_name: Any,
    space_name: Any,
) -> dict[str, Any]:
    route_id = route_id_for_display_name(display_name)
    display_name = str(display_name).strip()
    space_name = _space_name(space_name)

    _authorize(
        principal=principal,
        capability=UPDATE_CAPABILITY,
        route_id=route_id,
        display_name=display_name,
    )

    db = _db()
    ref = db.collection(ROUTE_COLLECTION).document(route_id)
    transaction = db.transaction()

    @firestore.transactional
    def _register(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = ref.get(transaction=tx)
        existing = snapshot.to_dict() or {} if snapshot.exists else {}

        if (
            existing.get("active") is True
            and existing.get("space_name") != space_name
        ):
            raise AuthorizationError(
                reason="human_reach_route_conflict",
                details={
                    "existing_space_name": existing.get("space_name"),
                    "proposed_space_name": space_name,
                },
            )

        now = _now_iso()
        route = {
            "route_id": route_id,
            "display_name": display_name,
            "space_name": space_name,
            "active": True,
            "source": "google_chat_interaction_event",
            "registered_at": existing.get("registered_at") or now,
            "last_seen_at": now,
        }
        tx.set(ref, route)
        return route

    try:
        route = _register(transaction)
    except AuthorizationError as error:
        _deny(
            error=error,
            principal=principal,
            capability=UPDATE_CAPABILITY,
            route_id=route_id,
            display_name=display_name,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=UPDATE_CAPABILITY,
        issue_id=f"human-reach-route:{route_id}",
        target_owner="HumanReach",
        reason="human_reach_route_registered",
        details={
            "route_id": route_id,
            "display_name": display_name,
            "space_name": space_name,
        },
    )

    return route


def authorize_and_resolve_route(
    *,
    principal: str,
    display_name: Any,
) -> dict[str, Any]:
    route_id = route_id_for_display_name(display_name)
    display_name = str(display_name).strip()

    _authorize(
        principal=principal,
        capability=READ_CAPABILITY,
        route_id=route_id,
        display_name=display_name,
    )

    snapshot = (
        _db()
        .collection(ROUTE_COLLECTION)
        .document(route_id)
        .get()
    )

    if not snapshot.exists:
        raise AuthorizationError(
            reason="human_reach_route_not_registered"
        )

    route = snapshot.to_dict() or {}

    if (
        route.get("active") is not True
        or route.get("display_name") != display_name
        or not isinstance(route.get("space_name"), str)
        or not str(route.get("space_name")).startswith("spaces/")
    ):
        raise AuthorizationError(
            reason="human_reach_route_not_registered"
        )

    return route


def authorize_and_deactivate_route(
    *,
    principal: str,
    display_name: Any,
    space_name: Any,
) -> dict[str, Any]:
    route_id = route_id_for_display_name(display_name)
    display_name = str(display_name).strip()
    space_name = _space_name(space_name)

    _authorize(
        principal=principal,
        capability=UPDATE_CAPABILITY,
        route_id=route_id,
        display_name=display_name,
    )

    db = _db()
    ref = db.collection(ROUTE_COLLECTION).document(route_id)
    transaction = db.transaction()

    @firestore.transactional
    def _deactivate(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = ref.get(transaction=tx)

        if not snapshot.exists:
            return {
                "route_id": route_id,
                "display_name": display_name,
                "space_name": space_name,
                "active": False,
            }

        route = snapshot.to_dict() or {}

        if route.get("space_name") != space_name:
            raise AuthorizationError(
                reason="human_reach_route_source_mismatch"
            )

        now = _now_iso()
        updates = {
            "active": False,
            "last_seen_at": now,
            "deactivated_at": now,
        }
        tx.update(ref, updates)
        route.update(updates)
        return route

    try:
        route = _deactivate(transaction)
    except AuthorizationError as error:
        _deny(
            error=error,
            principal=principal,
            capability=UPDATE_CAPABILITY,
            route_id=route_id,
            display_name=display_name,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=UPDATE_CAPABILITY,
        issue_id=f"human-reach-route:{route_id}",
        target_owner="HumanReach",
        reason="human_reach_route_deactivated",
        details={
            "route_id": route_id,
            "display_name": display_name,
            "space_name": space_name,
        },
    )

    return route
