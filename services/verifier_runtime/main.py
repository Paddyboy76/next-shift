from __future__ import annotations

import os
from typing import Any

from flask import Flask
from flask import jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests


TIMEOUT_SECONDS = 20

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


def _matches(
    issue: dict[str, Any],
    evidence: dict[str, Any],
) -> bool:
    owner = issue.get("owner")
    details = evidence.get("details")

    if not isinstance(details, dict):
        return False

    if owner == "Facilities":
        return (
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
        return (
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
        return (
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
        return (
            evidence.get("evidence_type") == "dme_delivery"
            and evidence.get("source") == "synthetic_dme_vendor"
            and evidence.get("subject") == issue.get("dme_order_id")
            and details.get("destination")
            == issue.get("dme_delivery_destination")
            and details.get("status") == "DELIVERED"
        )

    if owner == "EVSThroughput":
        return (
            evidence.get("evidence_type")
            == "evs_cleaning_complete"
            and evidence.get("source") == "synthetic_evs_system"
            and evidence.get("subject") == issue.get("evs_cleaning_id")
            and details.get("room") == issue.get("evs_room")
            and details.get("status") == "CLEAN"
            and isinstance(details.get("completed_at"), str)
        )

    if owner == "PatientTransport":
        return (
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

    return False


def _matching_evidence(
    context: dict[str, Any],
) -> dict[str, Any] | None:
    issue = context.get("issue")
    evidence = context.get("evidence")

    if not isinstance(issue, dict):
        return None

    if not isinstance(evidence, list):
        return None

    if issue.get("state") != "VERIFYING":
        return None

    for item in evidence:
        if (
            isinstance(item, dict)
            and _matches(issue, item)
        ):
            return item

    return None


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

    evidence = _matching_evidence(context)

    if evidence is None:
        return (
            jsonify(
                {
                    "error": "trusted_evidence_not_verified",
                    "message": (
                        "Independent verifier found no matching "
                        "trusted evidence for this issue."
                    ),
                }
            ),
            409,
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
