from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from audit import emit_security_event
from policy import PRINCIPAL_POLICIES
from security import AuthorizationError


PROJECT_ID = "next-shift-506004"
COLLECTION = "coverage_reviews"
CAPABILITY = "coverage.review"
ALLOWED_DECISIONS = frozenset({"PASS", "REVIEW_REQUIRED"})
ALLOWED_FINDING_TYPES = frozenset(
    {"MISSED", "DUPLICATED", "CONFLATED", "MISROUTED", "UNCERTAIN"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise AuthorizationError(reason="invalid_coverage_review")
    return value.strip()


def authorize_and_record_coverage_review(
    *, principal: str, payload: dict[str, Any]
) -> dict[str, Any]:
    policy = PRINCIPAL_POLICIES.get(principal)
    if policy is None or CAPABILITY not in policy.capabilities or policy.owner != "CoverageCritic":
        raise AuthorizationError(reason="capability_denied")

    source_reference = _text(payload.get("source_reference"), 300)
    message = _text(payload.get("message"), 8000)
    decision = payload.get("decision")
    summary = _text(payload.get("summary"), 1200)
    model = _text(payload.get("model"), 100)
    findings = payload.get("findings")
    proposal_count = payload.get("proposal_count")
    if decision not in ALLOWED_DECISIONS or not isinstance(findings, list):
        raise AuthorizationError(reason="invalid_coverage_review")
    if not isinstance(proposal_count, int) or proposal_count < 0 or proposal_count > 50:
        raise AuthorizationError(reason="invalid_coverage_review")

    cleaned = []
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("type") not in ALLOWED_FINDING_TYPES:
            raise AuthorizationError(reason="invalid_coverage_review")
        cleaned.append({
            "type": finding["type"],
            "detail": _text(finding.get("detail"), 800),
            "proposal_indexes": finding.get("proposal_indexes", []),
            "suggested_owner": finding.get("suggested_owner"),
        })
    if decision == "PASS" and cleaned:
        raise AuthorizationError(reason="invalid_coverage_review")
    if decision == "REVIEW_REQUIRED" and not cleaned:
        raise AuthorizationError(reason="invalid_coverage_review")

    ref = firestore.Client(project=PROJECT_ID).collection(COLLECTION).document()
    record = {
        "id": ref.id,
        "source_reference": source_reference,
        "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
        "decision": decision,
        "summary": summary,
        "findings": cleaned,
        "proposal_count": proposal_count,
        "critic": principal,
        "model": model,
        "created_at": _now_iso(),
    }
    ref.set(record)
    emit_security_event(decision="ALLOW", principal=principal, capability=CAPABILITY,
                        issue_id="pending", target_owner="Intake",
                        reason="coverage_review_recorded",
                        details={"review_id": ref.id, "review_decision": decision})
    return record
