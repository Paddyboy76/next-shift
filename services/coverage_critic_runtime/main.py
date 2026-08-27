from __future__ import annotations

import json
import os
from typing import Any

import google.auth
from flask import Flask, jsonify, request
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import id_token
import requests


PROJECT = "next-shift-506004"
MODEL = os.environ.get("CRITIC_MODEL", "gemini-3.5-flash")
OWNERS = {
    "Facilities",
    "AssetLogistics",
    "LanguageAccess",
    "DischargeDME",
    "EVSThroughput",
    "PatientTransport",
}
FINDING_TYPES = {
    "MISSED",
    "DUPLICATED",
    "CONFLATED",
    "MISROUTED",
    "UNCERTAIN",
}
BLOCKING_OR_MISSING_TYPES = FINDING_TYPES - {"UNCERTAIN"}
app = Flask(__name__)


def _access():
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(AuthRequest())
    return creds.token


def _clean_text(value: Any, *, maximum: int, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()[:maximum]


def normalize_review(value: Any, *, proposal_count: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("critic_result_not_object")

    raw_decision = str(value.get("decision") or "").strip().upper()
    decision = raw_decision if raw_decision in {"PASS", "REVIEW_REQUIRED"} else "REVIEW_REQUIRED"
    summary = _clean_text(
        value.get("summary"),
        maximum=1200,
        fallback="Coverage review completed.",
    )

    raw_findings = value.get("findings")
    if not isinstance(raw_findings, list):
        raw_findings = []

    findings: list[dict[str, Any]] = []
    for raw in raw_findings[:50]:
        if not isinstance(raw, dict):
            continue
        finding_type = str(raw.get("type") or "").strip().upper()
        if finding_type not in FINDING_TYPES:
            continue

        raw_indexes = raw.get("proposal_indexes")
        indexes: list[int] = []
        if isinstance(raw_indexes, list):
            for index in raw_indexes:
                if (
                    isinstance(index, int)
                    and not isinstance(index, bool)
                    and 0 <= index < proposal_count
                    and index not in indexes
                ):
                    indexes.append(index)

        suggested_owner = raw.get("suggested_owner")
        if suggested_owner not in OWNERS:
            suggested_owner = None

        findings.append(
            {
                "type": finding_type,
                "detail": _clean_text(
                    raw.get("detail"),
                    maximum=800,
                    fallback="Coverage Critic identified an operational coverage concern.",
                ),
                "proposal_indexes": indexes,
                "suggested_owner": suggested_owner,
            }
        )

    if decision == "PASS" and any(
        finding["type"] in BLOCKING_OR_MISSING_TYPES
        for finding in findings
    ):
        decision = "REVIEW_REQUIRED"

    if decision == "REVIEW_REQUIRED" and not findings:
        findings = [
            {
                "type": "UNCERTAIN",
                "detail": "Coverage Critic requested review but did not identify a blocking proposal-level defect.",
                "proposal_indexes": [],
                "suggested_owner": None,
            }
        ]

    return {
        "decision": decision,
        "summary": summary,
        "findings": findings,
    }


def model_review(
    message: str,
    proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    prompt = (
        "Act as an independent coverage critic for messy, human-written, non-clinical "
        "operational handovers. Compare the raw handover and proposed work. Find missed, "
        "duplicated, conflated, misrouted, or uncertain work. Never propose clinical work. "
        "Owners are Facilities, AssetLogistics, LanguageAccess, DischargeDME, "
        "EVSThroughput, PatientTransport.\n\n"
        "IMPORTANT DECISION RULES:\n"
        "- Human shorthand, imperfect grammar, vague object names, or uncertainty about the "
        "exact failed component are normal handover conditions and are NOT by themselves a "
        "reason to stop safe operational work.\n"
        "- If the owner, location, and safe next operational action are clear enough for the "
        "specialist to investigate, use an UNCERTAIN finding if useful but the overall "
        "decision may still be PASS.\n"
        "- Use REVIEW_REQUIRED only when dispatching a proposal as written could materially "
        "send work to the wrong owner, merge distinct jobs, duplicate work, miss an unresolved "
        "job, or otherwise create unsafe/incorrect operational action.\n"
        "- A clearly actionable proposal must not be rejected merely because another part "
        "of the same handover is ambiguous. Scope findings to proposal indexes whenever "
        "possible.\n"
        "- proposal_indexes are ZERO-BASED indexes into the PROPOSALS array.\n"
        "- Use an empty string for suggested_owner when no owner correction is needed.\n\n"
        "Return only the requested JSON object.\nRAW:\n"
        + message
        + "\nPROPOSALS:\n"
        + json.dumps(proposals, sort_keys=True)
    )
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/"
        f"publishers/google/models/{MODEL}:generateContent"
    )
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {_access()}",
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "decision": {
                            "type": "STRING",
                            "enum": ["PASS", "REVIEW_REQUIRED"],
                        },
                        "summary": {"type": "STRING"},
                        "findings": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "type": {
                                        "type": "STRING",
                                        "enum": [
                                            "MISSED",
                                            "DUPLICATED",
                                            "CONFLATED",
                                            "MISROUTED",
                                            "UNCERTAIN",
                                        ],
                                    },
                                    "detail": {"type": "STRING"},
                                    "proposal_indexes": {
                                        "type": "ARRAY",
                                        "items": {"type": "INTEGER"},
                                    },
                                    "suggested_owner": {"type": "STRING"},
                                },
                                "required": [
                                    "type",
                                    "detail",
                                    "proposal_indexes",
                                    "suggested_owner",
                                ],
                            },
                        },
                    },
                    "required": ["decision", "summary", "findings"],
                },
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    raw = json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
    return normalize_review(raw, proposal_count=len(proposals))


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "next-shift-coverage-critic",
            "model": MODEL,
        }
    )


@app.post("/v1/review")
def review():
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("message"), str)
        or not isinstance(data.get("proposals"), list)
    ):
        return jsonify({"error": "invalid_request"}), 400

    state = os.environ["STATE_AUTHORITY_URL"].rstrip("/")
    try:
        result = model_review(data["message"], data["proposals"])
        token = id_token.fetch_id_token(AuthRequest(), state)
        saved = requests.post(
            f"{state}/v1/coverage-reviews",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                **result,
                "message": data["message"],
                "proposal_count": len(data["proposals"]),
                "source_reference": data.get("source_reference"),
                "model": MODEL,
            },
            timeout=20,
        )
        if saved.status_code >= 400:
            print(
                json.dumps(
                    {
                        "event_type": "coverage_critic.state_authority_rejection",
                        "status": saved.status_code,
                        "body": saved.text[:500],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            return (
                jsonify(
                    {
                        "error": "coverage_review_failed",
                        "detail": "state_authority_rejected_review",
                        "state_status": saved.status_code,
                        "state_body": saved.text[:500],
                    }
                ),
                502,
            )
    except (
        requests.RequestException,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            json.dumps(
                {
                    "event_type": "coverage_critic.failure",
                    "detail": type(exc).__name__,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return jsonify({"error": "coverage_review_failed", "detail": type(exc).__name__}), 502

    return jsonify(saved.json())
