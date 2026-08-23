from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from audit import emit_security_event
from evidence import EVIDENCE_COLLECTION, ISSUE_COLLECTION
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
COLLECTION = "evidence_inspections"
READ = "evidence_inspection.read"
RECORD = "evidence_inspection.record"


def _authorize(principal: str, capability: str) -> None:
    policy = PRINCIPAL_POLICIES.get(principal)
    if policy is None or capability not in policy.capabilities or policy.owner != "EvidenceInspector":
        raise AuthorizationError(reason="capability_denied")


def authorize_and_get_inspection_context(*, principal: str, issue_id: str) -> dict[str, Any]:
    _authorize(principal, READ)
    db = firestore.Client(project=PROJECT_ID)
    snapshot = db.collection(ISSUE_COLLECTION).document(issue_id).get()
    if not snapshot.exists:
        raise AuthorizationError(reason="issue_not_found")
    issue = snapshot.to_dict() or {}
    evidence = [item.to_dict() or {} for item in db.collection(EVIDENCE_COLLECTION).where(
        filter=FieldFilter("issue_id", "==", issue_id)).stream()]
    emit_security_event(decision="ALLOW", principal=principal, capability=READ,
                        issue_id=issue_id, target_owner=str(issue.get("owner", "UNKNOWN")),
                        reason="inspection_context_authorized",
                        details={"evidence_count": len(evidence)})
    return {"issue": issue, "evidence": evidence}


def authorize_and_record_inspection(*, principal: str, issue_id: str,
                                    evidence_id: str, decision: str,
                                    reasons: list[str]) -> dict[str, Any]:
    _authorize(principal, RECORD)
    if decision not in {"PASS", "FAIL"} or not isinstance(evidence_id, str) or not evidence_id:
        raise AuthorizationError(reason="invalid_evidence_inspection")
    allowed = {"coverage_complete", "missing_evidence", "malformed_evidence",
               "stale_evidence", "wrong_capability_evidence", "untrusted_evidence_provenance"}
    if not isinstance(reasons, list) or not reasons or any(reason not in allowed for reason in reasons):
        raise AuthorizationError(reason="invalid_evidence_inspection")
    db = firestore.Client(project=PROJECT_ID)
    issue = db.collection(ISSUE_COLLECTION).document(issue_id).get().to_dict() or {}
    if issue.get("state") != "VERIFYING":
        raise AuthorizationError(reason="state_mismatch")
    ref = db.collection(COLLECTION).document()
    record = {"id": ref.id, "issue_id": issue_id, "evidence_id": evidence_id,
              "owner": issue.get("owner"), "decision": decision, "reasons": reasons,
              "inspector": principal, "created_at": datetime.now(timezone.utc).isoformat()}
    ref.set(record)
    emit_security_event(decision="ALLOW", principal=principal, capability=RECORD,
                        issue_id=issue_id, target_owner=str(issue.get("owner", "UNKNOWN")),
                        reason="evidence_inspection_recorded",
                        details={"inspection_id": ref.id, "inspection_decision": decision})
    return record


def latest_passing_inspection(db: firestore.Client, issue_id: str, evidence_id: str) -> dict[str, Any] | None:
    matches = [snap.to_dict() or {} for snap in db.collection(COLLECTION).where(
        filter=FieldFilter("issue_id", "==", issue_id)).stream()]
    passing = [item for item in matches if item.get("evidence_id") == evidence_id and item.get("decision") == "PASS"]
    return max(passing, key=lambda item: str(item.get("created_at", "")), default=None)
