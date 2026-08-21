from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from audit import emit_security_event
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUE_COLLECTION = "handover_issues"
EVIDENCE_COLLECTION = "issue_evidence"
TRANSITION_COLLECTION = "issue_transition_events"

EVIDENCE_CAPABILITY = "evidence.record"
VERIFICATION_READ_CAPABILITY = "verification.read"
VERIFICATION_CLOSE_CAPABILITY = "verification.close"


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authorize_special_principal(
    *,
    principal: str,
    capability: str,
    expected_owner: str,
    issue_id: str,
) -> None:
    policy = PRINCIPAL_POLICIES.get(principal)

    if policy is None:
        error = AuthorizationError(reason="unknown_principal")
        _deny(error, principal, capability, issue_id)
        raise error

    if capability not in policy.capabilities:
        error = AuthorizationError(reason="capability_denied")
        _deny(error, principal, capability, issue_id)
        raise error

    if policy.owner != expected_owner:
        error = AuthorizationError(
            reason="principal_capability_owner_mismatch"
        )
        _deny(error, principal, capability, issue_id)
        raise error


def _deny(
    error: AuthorizationError,
    principal: str,
    capability: str,
    issue_id: str,
    target_owner: str = "UNKNOWN",
) -> None:
    emit_security_event(
        decision="DENY",
        principal=principal,
        capability=capability,
        issue_id=issue_id,
        target_owner=(
            error.target_owner
            if error.target_owner != "UNKNOWN"
            else target_owner
        ),
        reason=error.reason,
        details=error.details,
    )


def _required_text(
    issue: dict[str, Any],
    field: str,
    *,
    owner: str,
) -> str:
    value = issue.get(field)

    if not isinstance(value, str) or not value.strip():
        raise AuthorizationError(
            reason="evidence_context_invalid",
            target_owner=owner,
            details={"field": field},
        )

    return value.strip()


def _evidence_contract(
    issue: dict[str, Any],
    *,
    observed_at: str,
) -> dict[str, Any]:
    owner = str(issue.get("owner", "UNKNOWN"))

    if owner == "Facilities":
        work_order = _required_text(
            issue,
            "facilities_work_order_id",
            owner=owner,
        )
        location = _required_text(
            issue,
            "facilities_location",
            owner=owner,
        )
        return {
            "evidence_type": "facilities_repair_complete",
            "source": "synthetic_facilities_system",
            "subject": work_order,
            "details": {
                "location": location,
                "status": "REPAIRED",
            },
            "issue_updates": {
                "facilities_status": "REPAIRED",
            },
        }

    if owner == "AssetLogistics":
        asset_id = _required_text(
            issue,
            "assigned_asset_id",
            owner=owner,
        )
        destination = _required_text(
            issue,
            "dispatch_destination",
            owner=owner,
        )
        return {
            "evidence_type": "asset_arrival",
            "source": "synthetic_rtls",
            "subject": asset_id,
            "details": {
                "location": destination,
                "status": "PRESENT",
            },
            "issue_updates": {
                "dispatch_status": "ARRIVED",
            },
        }

    if owner == "LanguageAccess":
        booking_id = _required_text(
            issue,
            "interpreter_booking_id",
            owner=owner,
        )
        interpreter_id = _required_text(
            issue,
            "interpreter_id",
            owner=owner,
        )
        location = _required_text(
            issue,
            "interpreter_service_location",
            owner=owner,
        )
        return {
            "evidence_type": "interpreter_attendance",
            "source": "synthetic_language_service",
            "subject": booking_id,
            "details": {
                "interpreter_id": interpreter_id,
                "service_location": location,
                "status": "PRESENT",
            },
            "issue_updates": {
                "interpreter_status": "PRESENT",
            },
        }

    if owner == "DischargeDME":
        order_id = _required_text(
            issue,
            "dme_order_id",
            owner=owner,
        )
        destination = _required_text(
            issue,
            "dme_delivery_destination",
            owner=owner,
        )
        return {
            "evidence_type": "dme_delivery",
            "source": "synthetic_dme_vendor",
            "subject": order_id,
            "details": {
                "destination": destination,
                "status": "DELIVERED",
            },
            "issue_updates": {
                "dme_order_status": "DELIVERED",
            },
        }

    if owner == "EVSThroughput":
        cleaning_id = _required_text(
            issue,
            "evs_cleaning_id",
            owner=owner,
        )
        room = _required_text(
            issue,
            "evs_room",
            owner=owner,
        )
        return {
            "evidence_type": "evs_cleaning_complete",
            "source": "synthetic_evs_system",
            "subject": cleaning_id,
            "details": {
                "room": room,
                "status": "CLEAN",
                "completed_at": observed_at,
            },
            "issue_updates": {
                "evs_status": "CLEAN",
                "evs_completed_at": observed_at,
            },
        }

    if owner == "PatientTransport":
        request_id = _required_text(
            issue,
            "transport_request_id",
            owner=owner,
        )
        destination = _required_text(
            issue,
            "transport_destination",
            owner=owner,
        )
        return {
            "evidence_type": "transport_arrival",
            "source": "synthetic_transport_system",
            "subject": request_id,
            "details": {
                "destination": destination,
                "status": "ARRIVED",
            },
            "issue_updates": {
                "transport_status": "ARRIVED",
            },
        }

    raise AuthorizationError(
        reason="unsupported_evidence_owner",
        target_owner=owner,
    )


def _evidence_matches(
    issue: dict[str, Any],
    evidence: dict[str, Any],
) -> bool:
    try:
        contract = _evidence_contract(
            issue,
            observed_at=str(
                evidence.get("created_at")
                or "verification"
            ),
        )
    except AuthorizationError:
        return False

    details = evidence.get("details")

    if not isinstance(details, dict):
        return False

    expected_details = contract["details"]

    for key, expected in expected_details.items():
        if key == "completed_at":
            if not isinstance(details.get(key), str):
                return False
            continue

        if details.get(key) != expected:
            return False

    return (
        evidence.get("evidence_type")
        == contract["evidence_type"]
        and evidence.get("source")
        == contract["source"]
        and evidence.get("subject")
        == contract["subject"]
    )


def authorize_and_record_evidence(
    *,
    principal: str,
    issue_id: str,
) -> dict[str, Any]:
    _authorize_special_principal(
        principal=principal,
        capability=EVIDENCE_CAPABILITY,
        expected_owner="TrustedEvidence",
        issue_id=issue_id,
    )

    db = _db()
    issue_ref = db.collection(ISSUE_COLLECTION).document(issue_id)
    evidence_ref = db.collection(EVIDENCE_COLLECTION).document()
    transition_ref = db.collection(TRANSITION_COLLECTION).document()
    transaction = db.transaction()

    @firestore.transactional
    def _record(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = issue_ref.get(transaction=tx)

        if not snapshot.exists:
            raise AuthorizationError(reason="issue_not_found")

        issue = snapshot.to_dict() or {}
        owner = str(issue.get("owner", "UNKNOWN"))

        if issue.get("state") != "ACTION_PENDING":
            raise AuthorizationError(
                reason="state_mismatch",
                target_owner=owner,
                details={
                    "expected_state": "ACTION_PENDING",
                    "current_state": issue.get("state"),
                },
            )

        observed_at = _now_iso()
        contract = _evidence_contract(
            issue,
            observed_at=observed_at,
        )

        evidence = {
            "id": evidence_ref.id,
            "issue_id": issue_id,
            "owner": owner,
            "evidence_type": contract["evidence_type"],
            "source": contract["source"],
            "subject": contract["subject"],
            "details": contract["details"],
            "recorded_by": principal,
            "created_at": observed_at,
        }

        history = issue.get("history", [])
        if not isinstance(history, list):
            raise AuthorizationError(
                reason="invalid_history",
                target_owner=owner,
            )

        reason = (
            f"Trusted evidence from {contract['source']} "
            f"moved the issue to verification."
        )
        history_entry = {
            "from": "ACTION_PENDING",
            "to": "VERIFYING",
            "at": observed_at,
            "actor": principal,
            "reason": reason,
        }

        issue_updates = dict(contract["issue_updates"])
        issue_updates.update(
            {
                "state": "VERIFYING",
                "history": [*history, history_entry],
                "updated_at": firestore.SERVER_TIMESTAMP,
                "last_transition_at": firestore.SERVER_TIMESTAMP,
                "latest_evidence_id": evidence_ref.id,
                "latest_evidence_source": contract["source"],
            }
        )

        tx.set(evidence_ref, evidence)
        tx.update(issue_ref, issue_updates)
        tx.set(
            transition_ref,
            {
                "id": transition_ref.id,
                "issue_id": issue_id,
                "owner": owner,
                "principal": principal,
                "capability": EVIDENCE_CAPABILITY,
                "from_state": "ACTION_PENDING",
                "to_state": "VERIFYING",
                "reason": reason,
                "update_fields": sorted(issue_updates),
                "authority_observed_at": observed_at,
                "committed_at": firestore.SERVER_TIMESTAMP,
            },
        )

        return {
            "owner": owner,
            "evidence": evidence,
            "transition_event_id": transition_ref.id,
        }

    try:
        result = _record(transaction)
    except AuthorizationError as error:
        _deny(
            error,
            principal,
            EVIDENCE_CAPABILITY,
            issue_id,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=EVIDENCE_CAPABILITY,
        issue_id=issue_id,
        target_owner=result["owner"],
        reason="trusted_evidence_recorded",
        details={
            "evidence_id": result["evidence"]["id"],
            "transition_event_id": result["transition_event_id"],
        },
    )

    return result


def authorize_and_get_verification_context(
    *,
    principal: str,
    issue_id: str,
) -> dict[str, Any]:
    _authorize_special_principal(
        principal=principal,
        capability=VERIFICATION_READ_CAPABILITY,
        expected_owner="IndependentVerifier",
        issue_id=issue_id,
    )

    db = _db()
    snapshot = db.collection(ISSUE_COLLECTION).document(issue_id).get()

    if not snapshot.exists:
        error = AuthorizationError(reason="issue_not_found")
        _deny(
            error,
            principal,
            VERIFICATION_READ_CAPABILITY,
            issue_id,
        )
        raise error

    issue = snapshot.to_dict() or {}
    owner = str(issue.get("owner", "UNKNOWN"))

    evidence = [
        item.to_dict() or {}
        for item in (
            db.collection(EVIDENCE_COLLECTION)
            .where(
                filter=FieldFilter(
                    "issue_id",
                    "==",
                    issue_id,
                )
            )
            .stream()
        )
    ]

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=VERIFICATION_READ_CAPABILITY,
        issue_id=issue_id,
        target_owner=owner,
        reason="verification_context_authorized",
        details={"evidence_count": len(evidence)},
    )

    return {
        "issue": issue,
        "evidence": evidence,
    }


def authorize_and_close_verified_issue(
    *,
    principal: str,
    issue_id: str,
    evidence_id: str,
) -> dict[str, Any]:
    _authorize_special_principal(
        principal=principal,
        capability=VERIFICATION_CLOSE_CAPABILITY,
        expected_owner="IndependentVerifier",
        issue_id=issue_id,
    )

    if not isinstance(evidence_id, str) or not evidence_id.strip():
        error = AuthorizationError(reason="invalid_evidence_id")
        _deny(
            error,
            principal,
            VERIFICATION_CLOSE_CAPABILITY,
            issue_id,
        )
        raise error

    db = _db()
    issue_ref = db.collection(ISSUE_COLLECTION).document(issue_id)
    evidence_ref = db.collection(EVIDENCE_COLLECTION).document(
        evidence_id.strip()
    )
    transition_ref = db.collection(TRANSITION_COLLECTION).document()
    transaction = db.transaction()

    @firestore.transactional
    def _close(tx: firestore.Transaction) -> dict[str, Any]:
        issue_snapshot = issue_ref.get(transaction=tx)
        evidence_snapshot = evidence_ref.get(transaction=tx)

        if not issue_snapshot.exists:
            raise AuthorizationError(reason="issue_not_found")

        if not evidence_snapshot.exists:
            raise AuthorizationError(reason="evidence_not_found")

        issue = issue_snapshot.to_dict() or {}
        evidence = evidence_snapshot.to_dict() or {}
        owner = str(issue.get("owner", "UNKNOWN"))

        if issue.get("state") != "VERIFYING":
            raise AuthorizationError(
                reason="state_mismatch",
                target_owner=owner,
                details={
                    "expected_state": "VERIFYING",
                    "current_state": issue.get("state"),
                },
            )

        if evidence.get("issue_id") != issue_id:
            raise AuthorizationError(
                reason="evidence_issue_mismatch",
                target_owner=owner,
            )

        if not _evidence_matches(issue, evidence):
            raise AuthorizationError(
                reason="trusted_evidence_mismatch",
                target_owner=owner,
            )

        observed_at = _now_iso()
        history = issue.get("history", [])

        if not isinstance(history, list):
            raise AuthorizationError(
                reason="invalid_history",
                target_owner=owner,
            )

        reason = (
            f"Independent verifier accepted trusted evidence "
            f"{evidence_id.strip()} and closed the issue."
        )
        history_entry = {
            "from": "VERIFYING",
            "to": "CLOSED",
            "at": observed_at,
            "actor": principal,
            "reason": reason,
        }

        tx.update(
            issue_ref,
            {
                "state": "CLOSED",
                "history": [*history, history_entry],
                "updated_at": firestore.SERVER_TIMESTAMP,
                "last_transition_at": firestore.SERVER_TIMESTAMP,
                "verification_status": "VERIFIED",
                "verification_evidence_id": evidence_id.strip(),
                "verified_by": principal,
            },
        )
        tx.update(
            evidence_ref,
            {
                "verified_at": firestore.SERVER_TIMESTAMP,
                "verified_by": principal,
            },
        )
        tx.set(
            transition_ref,
            {
                "id": transition_ref.id,
                "issue_id": issue_id,
                "owner": owner,
                "principal": principal,
                "capability": VERIFICATION_CLOSE_CAPABILITY,
                "from_state": "VERIFYING",
                "to_state": "CLOSED",
                "reason": reason,
                "update_fields": [
                    "verification_evidence_id",
                    "verification_status",
                    "verified_by",
                ],
                "authority_observed_at": observed_at,
                "committed_at": firestore.SERVER_TIMESTAMP,
            },
        )

        return {
            "owner": owner,
            "evidence": evidence,
            "transition_event_id": transition_ref.id,
        }

    try:
        result = _close(transaction)
    except AuthorizationError as error:
        _deny(
            error,
            principal,
            VERIFICATION_CLOSE_CAPABILITY,
            issue_id,
        )
        raise

    emit_security_event(
        decision="ALLOW",
        principal=principal,
        capability=VERIFICATION_CLOSE_CAPABILITY,
        issue_id=issue_id,
        target_owner=result["owner"],
        reason="verification_closed",
        details={
            "evidence_id": evidence_id.strip(),
            "transition_event_id": result["transition_event_id"],
        },
    )

    return result
