from __future__ import annotations

import json
from typing import Any

import google.auth
from google.auth.transport.requests import (
    Request as GoogleAuthRequest,
)
import requests


PROJECT_ID = "next-shift-506004"
LOCATION = "asia-southeast1"

REASONING_ENGINE_ID = (
    "8140616966286082048"
)

STREAM_URL = (
    "https://"
    f"{LOCATION}-aiplatform.googleapis.com"
    f"/v1/projects/{PROJECT_ID}"
    f"/locations/{LOCATION}"
    f"/reasoningEngines/"
    f"{REASONING_ENGINE_ID}:streamQuery"
)

OWNER_BUCKETS = {
    "facilities": "Facilities",
    "asset_logistics": "AssetLogistics",
    "language_access": "LanguageAccess",
    "discharge_dme": "DischargeDME",
    "evs_throughput": "EVSThroughput",
    "patient_transport": "PatientTransport",
}


def _access_token() -> str:
    credentials, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform"
        ]
    )
    credentials.refresh(GoogleAuthRequest())

    if not credentials.token:
        raise RuntimeError(
            "Unable to obtain Agent Runtime token"
        )

    return credentials.token


def _flatten_owner_buckets(
    value: dict[str, Any],
) -> list[dict[str, Any]] | None:
    issues: list[dict[str, Any]] = []

    for bucket, owner in OWNER_BUCKETS.items():
        bucket_items = value.get(bucket)

        if not isinstance(bucket_items, list):
            return None

        for item in bucket_items:
            if not isinstance(item, dict):
                return None

            proposal = dict(item)
            proposal["owner"] = owner
            issues.append(proposal)

    return issues


def _normalize_intake_result(
    value: Any,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    rejected = value.get(
        "rejected_clinical_requests"
    )
    summary = value.get("summary")

    if (
        not isinstance(rejected, list)
        or not all(
            isinstance(item, str)
            for item in rejected
        )
        or not isinstance(summary, str)
        or not summary.strip()
    ):
        return None

    issues = _flatten_owner_buckets(value)

    # Preserve compatibility with already-deployed structured outputs while
    # the canonical Agent Runtime moves to the stricter owner-bucket schema.
    if issues is None:
        legacy_issues = value.get("issues")

        if (
            not isinstance(legacy_issues, list)
            or not all(
                isinstance(item, dict)
                for item in legacy_issues
            )
        ):
            return None

        issues = [
            dict(item)
            for item in legacy_issues
        ]

    return {
        "issues": issues,
        "rejected_clinical_requests": [
            item.strip()
            for item in rejected
            if item.strip()
        ],
        "summary": summary.strip(),
    }


def _json_from_text(
    text: str,
) -> dict[str, Any] | None:
    candidate = text.strip()

    if candidate.startswith("```"):
        lines = candidate.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        candidate = "\n".join(lines).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    return _normalize_intake_result(parsed)


def _structured_results(
    value: Any,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    normalized = _normalize_intake_result(value)

    if normalized is not None:
        results.append(normalized)

    if isinstance(value, str):
        parsed = _json_from_text(value)

        if parsed is not None:
            results.append(parsed)

    elif isinstance(value, dict):
        for item in value.values():
            results.extend(
                _structured_results(item)
            )

    elif isinstance(value, list):
        for item in value:
            results.extend(
                _structured_results(item)
            )

    return results


def _event_from_stream_line(
    raw_line: str,
) -> Any | None:
    line = raw_line.strip()

    if not line or line.startswith(":"):
        return None

    if line.startswith("data:"):
        payload = line[5:].strip()
    elif line.startswith(
        (
            "event:",
            "id:",
            "retry:",
        )
    ):
        return None
    else:
        payload = line

    if not payload or payload == "[DONE]":
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _dedupe_proposals(
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()

    for proposal in proposals:
        key = json.dumps(
            proposal,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(proposal)

    return unique


def submit_handover(
    *,
    message: str,
    user_id: str,
) -> dict[str, Any]:
    response = requests.post(
        STREAM_URL,
        params={"alt": "sse"},
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        },
        json={
            "class_method": "async_stream_query",
            "input": {
                "user_id": user_id,
                "message": message,
            },
        },
        timeout=120,
        stream=True,
    )

    if response.status_code == 403:
        return {
            "blocked": True,
            "status": "blocked",
            "message": (
                "The governed intake policy blocked this request."
            ),
            "structured_output": True,
            "proposals": [],
            "rejected_clinical_requests": [],
        }

    response.raise_for_status()

    structured: list[dict[str, Any]] = []

    for raw_line in response.iter_lines(
        decode_unicode=True
    ):
        if not raw_line:
            continue

        event = _event_from_stream_line(raw_line)

        if event is None:
            continue

        structured.extend(
            _structured_results(event)
        )

    if not structured:
        return {
            "blocked": False,
            "status": "invalid_agent_output",
            "message": (
                "The Agent Runtime completed, but did not return the "
                "required structured intake result. No durable work was "
                "created."
            ),
            "structured_output": False,
            "proposals": [],
            "rejected_clinical_requests": [],
        }

    intake = structured[-1]
    rejected = intake[
        "rejected_clinical_requests"
    ]
    summary = intake["summary"]

    if rejected:
        summary = (
            summary
            + "\n\nRejected clinical request(s): "
            + "; ".join(rejected)
        )

    return {
        "blocked": False,
        "status": "analyzed",
        "message": summary,
        "structured_output": True,
        "proposals": _dedupe_proposals(
            intake["issues"]
        ),
        "rejected_clinical_requests": rejected,
    }
