from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from flask import Flask, jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

TRUSTED = "ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com"
app = Flask(__name__)

def _headers(url: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {id_token.fetch_id_token(Request(), url)}", "Content-Type": "application/json"}

def _time(value: Any):
    try: parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError: return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None

def inspection_reasons(issue: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    provenance = evidence.get("provenance")
    if (evidence.get("issue_id") != issue.get("id") or evidence.get("owner") != issue.get("owner")
        or evidence.get("recorded_by") != TRUSTED or not isinstance(provenance, dict)
        or provenance.get("authority") != "state_authority" or provenance.get("issuer") != TRUSTED
        or provenance.get("integration") != evidence.get("source")
        or provenance.get("observation_mode") != "synthetic_external_system"
        or provenance.get("workflow_state_observed") != "ACTION_PENDING"):
        return ["untrusted_evidence_provenance"]
    observed, created = _time(provenance.get("observed_at")), _time(evidence.get("created_at"))
    if observed is None or created is None or observed != created: return ["malformed_evidence"]
    if datetime.now(timezone.utc) - observed > timedelta(hours=24): return ["stale_evidence"]
    details = evidence.get("details", {})
    contracts = {
      "Facilities": ("facilities_repair_complete","synthetic_facilities_system","facilities_work_order_id","location","facilities_location","REPAIRED"),
      "AssetLogistics": ("asset_arrival","synthetic_rtls","assigned_asset_id","location","dispatch_destination","PRESENT"),
      "LanguageAccess": ("interpreter_attendance","synthetic_language_service","interpreter_booking_id","service_location","interpreter_service_location","PRESENT"),
      "DischargeDME": ("dme_delivery","synthetic_dme_vendor","dme_order_id","destination","dme_delivery_destination","DELIVERED"),
      "EVSThroughput": ("evs_cleaning_complete","synthetic_evs_system","evs_cleaning_id","room","evs_room","CLEAN"),
      "PatientTransport": ("transport_arrival","synthetic_transport_system","transport_request_id","destination","transport_destination","ARRIVED")}
    contract = contracts.get(issue.get("owner"))
    if contract is None or not isinstance(details, dict): return ["wrong_capability_evidence"]
    kind, source, subject, detail, expected, status = contract
    if not (evidence.get("evidence_type") == kind and evidence.get("source") == source
            and evidence.get("subject") == issue.get(subject) and details.get(detail) == issue.get(expected)
            and details.get("status") == status): return ["wrong_capability_evidence"]
    return ["coverage_complete"]

@app.get("/health")
def health(): return jsonify({"status":"ok","service":"next-shift-evidence-inspector"})

@app.post("/v1/issues/<issue_id>/inspect")
def inspect_issue(issue_id: str):
    url=os.environ["STATE_AUTHORITY_URL"].rstrip("/"); headers=_headers(url)
    response=requests.get(f"{url}/v1/issues/{issue_id}/inspection-context",headers=headers,timeout=20)
    if response.status_code >= 400: return jsonify(response.json()),response.status_code
    context=response.json(); items=context.get("evidence",[])
    evidence=next((x for x in reversed(items) if isinstance(x,dict)),None)
    if evidence is None: return jsonify({"error":"missing_evidence"}),409
    reasons=inspection_reasons(context.get("issue",{}),evidence); decision="PASS" if reasons==["coverage_complete"] else "FAIL"
    recorded=requests.post(f"{url}/v1/issues/{issue_id}/evidence-inspections",headers=headers,
        json={"evidence_id":evidence.get("id"),"decision":decision,"reasons":reasons},timeout=20)
    return jsonify(recorded.json()), (200 if recorded.status_code < 400 and decision=="PASS" else 409)
