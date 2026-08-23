from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask
from flask import jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


TIMEOUT_SECONDS = 20
EVIDENCE_SCHEMA_VERSION = "1.0"
MAX_EVIDENCE_AGE = timedelta(hours=24)
TRUSTED_EVIDENCE_PRINCIPAL = (
    "ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com"
)

app = Flask(__name__)


def _state_url() -> str:
    value = os.environ.get(
        "STATE_AUTHORITY_URL",
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            "STATE_AUTHORITY_URL is required"
        )

    return value.rstrip("/")


def _inspector_url() -> str:
    value = os.environ.get("EVIDENCE_INSPECTOR_URL", "").strip()
    if not value:
        raise RuntimeError("EVIDENCE_INSPECTOR_URL is required")
    return value.rstrip("/")


def _token(audience: str) -> str:
    token = id_token.fetch_id_token(
        Request(),
        audience,
    )

    if not token:
        raise RuntimeError(
            "Unable to obtain State Authority identity token"
        )

    return token


def _headers(state_url: str) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {_token(state_url)}"
        ),
        "Content-Type": "application/json",
    }


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _rejection_reason(
    issue: dict[str, Any],
    evidence: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str | None:
    owner = issue.get("owner")
    details = evidence.get("details")

    if not isinstance(details, dict):
        return "malformed_evidence"

    provenance = evidence.get("provenance")
    if (
        evidence.get("issue_id") != issue.get("id")
        or evidence.get("owner") != owner
        or evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION
        or evidence.get("recorded_by") != TRUSTED_EVIDENCE_PRINCIPAL
        or not isinstance(provenance, dict)
        or provenance.get("authority") != "state_authority"
        or provenance.get("issuer") != TRUSTED_EVIDENCE_PRINCIPAL
        or provenance.get("integration") != evidence.get("source")
        or provenance.get("observation_mode") != "synthetic_external_system"
        or provenance.get("workflow_state_observed") != "ACTION_PENDING"
    ):
        return "untrusted_evidence_provenance"

    observed_at = _parse_utc(provenance.get("observed_at"))
    created_at = _parse_utc(evidence.get("created_at"))
    current_time = now or datetime.now(timezone.utc)
    if observed_at is None or created_at is None or observed_at != created_at:
        return "malformed_evidence"
    if observed_at > current_time + timedelta(minutes=5):
        return "malformed_evidence"
    if current_time - observed_at > MAX_EVIDENCE_AGE:
        return "stale_evidence"

    matches = False
    if owner == "Facilities":
        matches = (
            evidence.get("evidence_type")
            == "facilities_repair_complete"
            and evidence.get("source")
            == "synthetic_facilities_system"
            and evidence.get("subject")
            == issue.get("facilities_work_order_id")
            and details.get("location")
            == issue.get("facilities_location")
            and details.get("status") == "REPAIRED"
        )

    if owner == "AssetLogistics":
        matches = (
            evidence.get("evidence_type")
            == "asset_arrival"
            and evidence.get("source") == "synthetic_rtls"
            and evidence.get("subject")
            == issue.get("assigned_asset_id")
            and details.get("location")
            == issue.get("dispatch_destination")
            and details.get("status") == "PRESENT"
        )

    if owner == "LanguageAccess":
        matches = (
            evidence.get("evidence_type")
            == "interpreter_attendance"
            and evidence.get("source")
            == "synthetic_language_service"
            and evidence.get("subject")
            == issue.get("interpreter_booking_id")
            and details.get("interpreter_id")
            == issue.get("interpreter_id")
            and details.get("service_location")
            == issue.get("interpreter_service_location")
            and details.get("status") == "PRESENT"
        )

    if owner == "DischargeDME":
        matches = (
            evidence.get("evidence_type") == "dme_delivery"
            and evidence.get("source") == "synthetic_dme_vendor"
            and evidence.get("subject") == issue.get("dme_order_id")
            and details.get("destination")
            == issue.get("dme_delivery_destination")
            and details.get("status") == "DELIVERED"
        )

    if owner == "EVSThroughput":
        matches = (
            evidence.get("evidence_type")
            == "evs_cleaning_complete"
            and evidence.get("source") == "synthetic_evs_system"
            and evidence.get("subject") == issue.get("evs_cleaning_id")
            and details.get("room") == issue.get("evs_room")
            and details.get("status") == "CLEAN"
            and isinstance(details.get("completed_at"), str)
        )

    if owner == "PatientTransport":
        matches = (
            evidence.get("evidence_type")
            == "transport_arrival"
            and evidence.get("source")
            == "synthetic_transport_system"
            and evidence.get("subject")
            == issue.get("transport_request_id")
            and details.get("destination")
            == issue.get("transport_destination")
            and details.get("status") == "ARRIVED"
        )

    return None if matches else "wrong_capability_evidence"


def _matches(issue: dict[str, Any], evidence: dict[str, Any]) -> bool:
    return _rejection_reason(issue, evidence) is None


def _matching_evidence(
    context: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    issue = context.get("issue")
    evidence = context.get("evidence")

    if not isinstance(issue, dict):
        return None, "malformed_evidence"

    if not isinstance(evidence, list):
        return None, "missing_evidence"

    if issue.get("state") != "VERIFYING":
        return None, "missing_evidence"

    rejection_reasons: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            rejection_reasons.append("malformed_evidence")
            continue
        reason = _rejection_reason(issue, item)
        if reason is None:
            return item, ""
        rejection_reasons.append(reason)

    priority = (
        "stale_evidence",
        "untrusted_evidence_provenance",
        "malformed_evidence",
        "wrong_capability_evidence",
    )
    for reason in priority:
        if reason in rejection_reasons:
            return None, reason
    return None, "missing_evidence"


def _record_rejection(
    state_url: str,
    headers: dict[str, str],
    issue_id: str,
    reason: str,
    evidence_id: str | None,
) -> requests.Response:
    return requests.post(
        f"{state_url}/v1/issues/{issue_id}/verification-rejection",
        headers=headers,
        json={"reason": reason, "evidence_id": evidence_id},
        timeout=TIMEOUT_SECONDS,
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "next-shift-independent-verifier",
        }
    )


@app.post("/v1/issues/<issue_id>/verify")
def verify_issue(issue_id: str):
    state_url = _state_url()
    headers = _headers(state_url)

    context_response = requests.get(
        (
            f"{state_url}/v1/issues/{issue_id}"
            "/verification-context"
        ),
        headers=headers,
        timeout=TIMEOUT_SECONDS,
    )

    try:
        context = context_response.json()
    except ValueError:
        context = {
            "error": "invalid_state_authority_response",
            "detail": context_response.text[:1000],
        }

    if context_response.status_code >= 400:
        return (
            jsonify(context),
            context_response.status_code,
        )

    evidence, rejection_reason = _matching_evidence(context)

    if evidence is None:
        items = context.get("evidence")
        candidate_id = None
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    candidate_id = item["id"]
                    break
        rejection_response = _record_rejection(
            state_url,
            headers,
            issue_id,
            rejection_reason,
            candidate_id,
        )
        try:
            rejection_payload = rejection_response.json()
        except ValueError:
            rejection_payload = {"error": "invalid_state_authority_response"}
        return (
            jsonify(
                {
                    "error": "trusted_evidence_not_verified",
                    "reason": rejection_reason,
                    "message": (
                        "Independent verifier found no matching "
                        "trusted evidence for this issue."
                    ),
                    "authoritative_rejection": rejection_payload,
                }
            ),
            409 if rejection_response.status_code < 400 else rejection_response.status_code,
        )

    evidence_id = evidence.get("id")

    if not isinstance(evidence_id, str):
        return (
            jsonify(
                {
                    "error": "invalid_evidence_record",
                }
            ),
            409,
        )

    inspector_url = _inspector_url()
    inspector_response = requests.post(
        f"{inspector_url}/v1/issues/{issue_id}/inspect",
        headers={"Authorization": f"Bearer {_token(inspector_url)}", "Content-Type": "application/json"},
        timeout=TIMEOUT_SECONDS,
    )
    if inspector_response.status_code >= 400:
        try:
            inspection = inspector_response.json()
        except ValueError:
            inspection = {"error": "invalid_inspector_response"}
        return jsonify({"error": "evidence_inspection_failed",
                        "message": "Independent Evidence Inspector did not approve closure.",
                        "inspection": inspection}), 409

    close_response = requests.post(
        f"{state_url}/v1/issues/{issue_id}/verify",
        headers=headers,
        json={
            "evidence_id": evidence_id,
        },
        timeout=TIMEOUT_SECONDS,
    )

    try:
        payload = close_response.json()
    except ValueError:
        payload = {
            "error": "invalid_state_authority_response",
            "detail": close_response.text[:1000],
        }

    return jsonify(payload), close_response.status_code
