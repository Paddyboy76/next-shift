from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from audit import emit_security_event
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
ISSUES = "handover_issues"
ATTEMPTS = "verification_attempts"
PLANS = "recovery_plans"
RECOVERABLE_STATES = frozenset({"ACTION_PENDING", "BLOCKED", "HUMAN_REVIEW"})
ALLOWED_ACTIONS = {
    "ACTION_PENDING": frozenset({"REQUEST_FRESH_EVIDENCE", "HUMAN_REVIEW"}),
    "BLOCKED": frozenset({"RETRY_SPECIALIST", "HUMAN_REVIEW"}),
    "HUMAN_REVIEW": frozenset({"RETRY_SPECIALIST"}),
}


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authorize(principal: str, capability: str, issue_id: str) -> None:
    policy = PRINCIPAL_POLICIES.get(principal)
    if policy is None or capability not in policy.capabilities:
        reason = "unknown_principal" if policy is None else "capability_denied"
        emit_security_event(decision="DENY", principal=principal, capability=capability,
                            issue_id=issue_id, target_owner="UNKNOWN", reason=reason)
        raise AuthorizationError(reason=reason)


def _clean(value: Any, field: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise AuthorizationError(reason="invalid_recovery_plan", details={"field": field})
    return value.strip()


def recovery_context(*, principal: str, issue_id: str) -> dict[str, Any]:
    _authorize(principal, "recovery.read", issue_id)
    db = _db()
    snapshot = db.collection(ISSUES).document(issue_id).get()
    if not snapshot.exists:
        raise AuthorizationError(reason="issue_not_found")
    issue = snapshot.to_dict()
    state = str(issue.get("state", ""))
    if state not in RECOVERABLE_STATES:
        raise AuthorizationError(reason="issue_not_recoverable", details={"state": state})
    attempts = [item.to_dict() for item in db.collection(ATTEMPTS).where(
        filter=FieldFilter("issue_id", "==", issue_id)).stream()]
    attempts.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    emit_security_event(decision="ALLOW", principal=principal, capability="recovery.read",
                        issue_id=issue_id, target_owner=str(issue.get("owner", "UNKNOWN")),
                        reason="authoritative_recovery_context")
    return {
        "issue": {key: issue.get(key) for key in (
            "id", "owner", "title", "state", "verification_status", "history",
            "created_at", "updated_at", "last_transition_at")},
        "latest_verification_failure": attempts[0] if attempts else None,
        "authority": "Firestore via State Authority",
        "allowed_actions": sorted(ALLOWED_ACTIONS[state]),
    }


def record_plan(*, principal: str, issue_id: str, proposal: dict[str, Any]) -> dict[str, Any]:
    _authorize(principal, "recovery.plan", issue_id)
    action = _clean(proposal.get("recommended_action"), "recommended_action", 64)
    reason = _clean(proposal.get("failure_reason"), "failure_reason")
    recommendation = _clean(proposal.get("recommendation"), "recommendation", 1000)
    db = _db()
    issue_ref = db.collection(ISSUES).document(issue_id)
    plan_ref = db.collection(PLANS).document()
    transaction = db.transaction()

    @firestore.transactional
    def commit(tx: firestore.Transaction) -> dict[str, Any]:
        snapshot = issue_ref.get(transaction=tx)
        if not snapshot.exists:
            raise AuthorizationError(reason="issue_not_found")
        issue = snapshot.to_dict()
        state = str(issue.get("state", ""))
        if action not in ALLOWED_ACTIONS.get(state, frozenset()):
            raise AuthorizationError(reason="recovery_action_not_allowed",
                                     details={"state": state, "action": action})
        created_at = _now()
        plan = {
            "id": plan_ref.id, "issue_id": issue_id, "owner": issue.get("owner"),
            "state_observed": state, "failure_reason": reason,
            "recommended_action": action, "recommendation": recommendation,
            "planner": principal, "status": "PROPOSED", "created_at": created_at,
            "authority_boundary": "ADVISORY_NO_STATE_MUTATION_NO_CLOSURE",
            "historical_context": proposal.get("historical_context") or [],
        }
        tx.set(plan_ref, plan)
        return plan

    plan = commit(transaction)
    emit_security_event(decision="ALLOW", principal=principal, capability="recovery.plan",
                        issue_id=issue_id, target_owner=str(plan.get("owner", "UNKNOWN")),
                        reason="advisory_plan_persisted", details={"plan_id": plan["id"]})
    return plan


def sanction_plan(*, principal: str, issue_id: str, plan_id: str) -> dict[str, Any]:
    _authorize(principal, "recovery.sanction", issue_id)
    db = _db()
    issue_ref = db.collection(ISSUES).document(issue_id)
    plan_ref = db.collection(PLANS).document(plan_id)
    transaction = db.transaction()

    @firestore.transactional
    def commit(tx: firestore.Transaction) -> dict[str, Any]:
        issue_snapshot = issue_ref.get(transaction=tx)
        plan_snapshot = plan_ref.get(transaction=tx)
        if not issue_snapshot.exists or not plan_snapshot.exists:
            raise AuthorizationError(reason="recovery_plan_not_found")
        issue = issue_snapshot.to_dict()
        plan = plan_snapshot.to_dict()
        if plan.get("issue_id") != issue_id or plan.get("status") != "PROPOSED":
            raise AuthorizationError(reason="recovery_plan_not_actionable")
        if issue.get("state") != plan.get("state_observed"):
            raise AuthorizationError(reason="stale_recovery_plan")
        sanctioned_at = _now()
        tx.update(plan_ref, {"status": "SANCTIONED", "sanctioned_by": principal,
                             "sanctioned_at": sanctioned_at})
        return {**plan, "status": "SANCTIONED", "sanctioned_by": principal,
                "sanctioned_at": sanctioned_at}

    plan = commit(transaction)
    emit_security_event(decision="ALLOW", principal=principal, capability="recovery.sanction",
                        issue_id=issue_id, target_owner=str(plan.get("owner", "UNKNOWN")),
                        reason="recovery_action_sanctioned", details={"plan_id": plan_id,
                        "action": plan.get("recommended_action")})
    return plan
