from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from typing import Any

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.cloud import storage
import requests


PROJECT_ID = "next-shift-506004"
MODEL = os.environ.get("PHOTO_EVIDENCE_MODEL", "gemini-3.5-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


class PhotoEvidenceError(RuntimeError):
    pass


def _bucket_name() -> str:
    value = os.environ.get("PHOTO_EVIDENCE_BUCKET", "").strip()
    if not value:
        raise PhotoEvidenceError("PHOTO_EVIDENCE_BUCKET is required")
    return value


def _access_token() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise PhotoEvidenceError("Unable to obtain Vertex AI credentials")
    return credentials.token


def _clean_image(data: bytes, mime_type: str, label: str) -> tuple[bytes, str]:
    normalized = mime_type.split(";", 1)[0].strip().lower()
    if normalized not in ALLOWED_TYPES:
        raise ValueError(f"{label} image must be JPEG, PNG, or WebP")
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"{label} image must be between 1 byte and 8 MiB")
    return data, normalized


def _schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "same_subject": {"type": "BOOLEAN"},
            "defect_visible_before": {"type": "BOOLEAN"},
            "repair_visible_after": {"type": "BOOLEAN"},
            "completion_supported": {"type": "BOOLEAN"},
            "confidence": {"type": "NUMBER"},
            "summary": {"type": "STRING"},
            "concerns": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": [
            "same_subject",
            "defect_visible_before",
            "repair_visible_after",
            "completion_supported",
            "confidence",
            "summary",
            "concerns",
        ],
    }


def inspect_images(*, issue: dict[str, Any], before: bytes, before_type: str,
                   after: bytes, after_type: str) -> dict[str, Any]:
    before, before_type = _clean_image(before, before_type, "Before")
    after, after_type = _clean_image(after, after_type, "After")
    location = str(issue.get("facilities_location") or (issue.get("workflow_input") or {}).get("location") or "unknown location")
    prompt = (
        "Act as a visual evidence reviewer for a synthetic non-clinical Facilities workflow. "
        "Image 1 is BEFORE work and image 2 is AFTER work. Compare only what is visibly "
        "supported. Do not infer hidden repairs, identity, safety certification, or completion "
        "from text alone. completion_supported may be true only when both images appear to "
        "show the same subject/location, a defect/problem is visible before, and the after "
        "image visibly supports that the described physical problem was corrected. If the "
        "images are ambiguous, unrelated, too different in framing, or do not visibly support "
        "repair, set completion_supported=false and explain why. This visual result is only "
        "supporting evidence; it cannot close operational work.\n\n"
        f"Issue title: {issue.get('title', '')}\n"
        f"Issue description: {issue.get('description', '')}\n"
        f"Facilities location: {location}"
    )
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/"
        f"publishers/google/models/{MODEL}:generateContent"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        json={
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": before_type, "data": base64.b64encode(before).decode("ascii")}},
                    {"inlineData": {"mimeType": after_type, "data": base64.b64encode(after).decode("ascii")}},
                ],
            }],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _schema(),
            },
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise PhotoEvidenceError(f"Gemini photo inspection failed with status {response.status_code}")
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise PhotoEvidenceError("Gemini returned invalid photo inspection output") from exc
    if not isinstance(result, dict):
        raise PhotoEvidenceError("Gemini returned invalid photo inspection output")
    return result


def store_photo_evidence(*, issue: dict[str, Any], before: bytes, before_type: str,
                         after: bytes, after_type: str, inspection: dict[str, Any]) -> dict[str, Any]:
    issue_id = str(issue.get("id") or "")
    if not issue_id:
        raise PhotoEvidenceError("Issue ID is required")
    evidence_id = f"visual-{uuid.uuid4()}"
    prefix = f"{issue_id}/{evidence_id}"
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(_bucket_name())
    before_name = f"{prefix}/before"
    after_name = f"{prefix}/after"
    metadata_name = f"{prefix}/inspection.json"
    bucket.blob(before_name).upload_from_string(before, content_type=before_type)
    bucket.blob(after_name).upload_from_string(after, content_type=after_type)
    record = {
        "id": evidence_id,
        "issue_id": issue_id,
        "owner": issue.get("owner"),
        "model": MODEL,
        "provider": "Vertex AI Gemini",
        "authority": "SUPPORTING_VISUAL_EVIDENCE_ONLY",
        "may_close_work": False,
        "before_object": before_name,
        "after_object": after_name,
        "before_mime_type": before_type,
        "after_mime_type": after_type,
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest(),
        "inspection": inspection,
    }
    bucket.blob(metadata_name).upload_from_string(
        json.dumps(record, sort_keys=True, separators=(",", ":")),
        content_type="application/json",
    )
    return record


def inspect_and_store(*, issue: dict[str, Any], before: bytes, before_type: str,
                      after: bytes, after_type: str) -> dict[str, Any]:
    inspection = inspect_images(
        issue=issue,
        before=before,
        before_type=before_type,
        after=after,
        after_type=after_type,
    )
    return store_photo_evidence(
        issue=issue,
        before=before,
        before_type=before_type,
        after=after,
        after_type=after_type,
        inspection=inspection,
    )


def list_photo_evidence(issue_id: str) -> list[dict[str, Any]]:
    client = storage.Client(project=PROJECT_ID)
    records: list[dict[str, Any]] = []
    for blob in client.list_blobs(_bucket_name(), prefix=f"{issue_id}/"):
        if not blob.name.endswith("/inspection.json"):
            continue
        try:
            value = json.loads(blob.download_as_text())
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            records.append(value)
    records.sort(key=lambda item: str(item.get("id", "")), reverse=True)
    return records


def image_bytes(issue_id: str, evidence_id: str, kind: str) -> tuple[bytes, str]:
    if kind not in {"before", "after"}:
        raise KeyError(kind)
    records = list_photo_evidence(issue_id)
    record = next((item for item in records if item.get("id") == evidence_id), None)
    if record is None:
        raise KeyError(evidence_id)
    object_name = record.get(f"{kind}_object")
    mime_type = record.get(f"{kind}_mime_type")
    if not isinstance(object_name, str) or not isinstance(mime_type, str):
        raise KeyError(kind)
    blob = storage.Client(project=PROJECT_ID).bucket(_bucket_name()).blob(object_name)
    return blob.download_as_bytes(), mime_type
