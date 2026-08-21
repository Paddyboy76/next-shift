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


def _access_token() -> str:
    credentials, _ = (
        google.auth.default(
            scopes=[
                "https://www.googleapis.com/"
                "auth/cloud-platform"
            ]
        )
    )

    credentials.refresh(
        GoogleAuthRequest()
    )

    if not credentials.token:
        raise RuntimeError(
            "Unable to obtain Agent Runtime token"
        )

    return credentials.token


def _extract_text(
    value: Any,
) -> list[str]:
    results: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if (
                key == "text"
                and isinstance(item, str)
                and item.strip()
            ):
                results.append(
                    item.strip()
                )
            else:
                results.extend(
                    _extract_text(item)
                )

    elif isinstance(value, list):
        for item in value:
            results.extend(
                _extract_text(item)
            )

    return results


def _extract_proposals(
    value: Any,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if isinstance(value, dict):
        if value.get("proposal_type") == "handover_issue":
            proposal = value.get("proposal")

            if isinstance(proposal, dict):
                results.append(dict(proposal))

        for item in value.values():
            results.extend(
                _extract_proposals(item)
            )

    elif isinstance(value, list):
        for item in value:
            results.extend(
                _extract_proposals(item)
            )

    return results


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
        params={
            "alt": "sse",
        },
        headers={
            "Authorization": (
                f"Bearer {_access_token()}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
        json={
            "class_method": (
                "async_stream_query"
            ),
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
                "The governed intake policy "
                "blocked this request."
            ),
            "proposals": [],
        }

    response.raise_for_status()

    text_parts: list[str] = []
    proposals: list[dict[str, Any]] = []

    for raw_line in response.iter_lines(
        decode_unicode=True
    ):
        if not raw_line:
            continue

        line = raw_line.strip()

        if not line.startswith("data:"):
            continue

        data = line[5:].strip()

        if not data:
            continue

        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue

        text_parts.extend(
            _extract_text(event)
        )
        proposals.extend(
            _extract_proposals(event)
        )

    unique_text: list[str] = []

    for text in text_parts:
        if (
            text
            and text not in unique_text
        ):
            unique_text.append(text)

    return {
        "blocked": False,
        "status": "accepted",
        "message": (
            "\n\n".join(unique_text[-6:])
            or (
                "Handover analyzed. "
                "Validated operational proposals are being persisted."
            )
        ),
        "proposals": _dedupe_proposals(
            proposals
        ),
    }
