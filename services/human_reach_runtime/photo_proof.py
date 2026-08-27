from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from typing import Any
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
import requests


PROJECT_ID = "next-shift-506004"
CHAT_API = "https://chat.googleapis.com/v1"
MODEL = os.environ.get("PHOTO_EVIDENCE_MODEL", "gemini-3.5-flash")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
THREAD_PREFIX = "next-shift-work-"


class PhotoProofError(RuntimeError):
    pass


def thread_key(delivery_id: str) -> str:
    return f"{THREAD_PREFIX}{delivery_id}"


def delivery_id_from_event(event: dict[str, Any]) -> str | None:
    candidates: list[Any] = [event.get("threadKey")]
    thread = event.get("thread")
    if isinstance(thread, dict):
        candidates.append(thread.get("threadKey"))
    message = event.get("message")
    if isinstance(message, dict):
        message_thread = message.get("thread")
        if isinstance(message_thread, dict):
            candidates.append(message_thread.get("threadKey"))

    for value in candidates:
        if isinstance(value, str) and value.startswith(THREAD_PREFIX):
            delivery_id = value[len(THREAD_PREFIX):].strip()
            if delivery_id and len(delivery_id) <= 128:
                return delivery_id
    return None


def decorate_card(delivery: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    if (
        delivery.get("owner") != "Facilities"
        or str(delivery.get("authoritative_issue_state") or "ACTION_PENDING") != "ACTION_PENDING"
        or str(delivery.get("delivery_status") or "") != "COMPLETION_CLAIMED"
    ):
        return card

    result = json.loads(json.dumps(card))
    sections = result.get("card", {}).get("sections")
    if not isinstance(sections, list) or len(sections) < 2:
        return result

    widgets = sections[1].get("widgets")
    if not isinstance(widgets, list):
        return result

    widgets.append(
        {
            "decoratedText": {
                "startIcon": {
                    "materialIcon": {
                        "name": "photo_camera",
                        "fill": True,
                        "weight": 400,
                    },
                    "altText": "Photo proof",
                },
                "topLabel": "PHOTO PROOF",
                "text": (
                    "<b>Completion reported.</b> Reply in this thread with exactly "
                    "two images and @mention Next Shift: first the <b>BEFORE</b> "
                    "photo, then the <b>AFTER</b> photo."
                ),
                "bottomLabel": (
                    "Gemini compares visible change only. Photos support evidence; "
                    "they do not close the work."
                ),
                "wrapText": True,
            }
        }
    )
    return result


def _cloud_token() -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise PhotoProofError("Unable to obtain Vertex AI credentials")
    return credentials.token


def _bucket_name() -> str:
    value = os.environ.get("PHOTO_EVIDENCE_BUCKET", "").strip()
    if not value:
        raise PhotoProofError("PHOTO_EVIDENCE_BUCKET is required")
    return value


def _download_images(event: dict[str, Any], *, chat_token: str) -> list[tuple[bytes, str, str]]:
    message = event.get("message")
    attachments = message.get("attachment") if isinstance(message, dict) else None
    if not isinstance(attachments, list):
        return []

    image_attachments = [
        item
        for item in attachments
        if isinstance(item, dict)
        and str(item.get("contentType") or "").lower() in ALLOWED_TYPES
        and isinstance(item.get("attachmentDataRef"), dict)
        and isinstance(item["attachmentDataRef"].get("resourceName"), str)
    ]
    if not image_attachments:
        return []
    if len(image_attachments) != 2:
        raise ValueError("Attach exactly two images: BEFORE first, AFTER second.")

    downloaded: list[tuple[bytes, str, str]] = []
    for item in image_attachments:
        data_ref = item["attachmentDataRef"]
        resource_name = str(data_ref["resourceName"])
        mime_type = str(item.get("contentType") or "").lower()
        response = requests.get(
            f"{CHAT_API}/media/{quote(resource_name, safe='/')}",
            headers={"Authorization": f"Bearer {chat_token}"},
            params={"alt": "media"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise PhotoProofError(
                f"Google Chat attachment download failed with status {response.status_code}"
            )
        data = response.content
        if not data or len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Each photo must be between 1 byte and 8 MiB.")
        downloaded.append(
            (data, mime_type, str(item.get("contentName") or "photo"))
        )
    return downloaded


def has_image_attachments(event: dict[str, Any]) -> bool:
    message = event.get("message")
    attachments = message.get("attachment") if isinstance(message, dict) else None
    return bool(
        isinstance(attachments, list)
        and any(
            isinstance(item, dict)
            and str(item.get("contentType") or "").lower() in ALLOWED_TYPES
            for item in attachments
        )
    )


def _inspection_schema() -> dict[str, Any]:
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


def _inspect(
    *,
    delivery: dict[str, Any],
    before: bytes,
    before_type: str,
    after: bytes,
    after_type: str,
) -> dict[str, Any]:
    prompt = (
        "Act as a visual evidence reviewer for a synthetic, non-clinical Facilities "
        "workflow. Image 1 is BEFORE work and image 2 is AFTER work. Compare only "
        "what is visibly supported. Do not infer hidden repairs, identity, safety "
        "certification, or completion from text alone. completion_supported may be "
        "true only when both images appear to show the same subject/location, a "
        "visible problem exists before, and the after image visibly supports that "
        "the described physical problem was corrected. If ambiguous, unrelated, or "
        "insufficient, set completion_supported=false and explain why. This visual "
        "result is supporting evidence only and cannot close operational work.\n\n"
        f"Task: {delivery.get('what', delivery.get('issue_title', ''))}\n"
        f"Location: {delivery.get('where', '')}\n"
        f"Work order: {delivery.get('work_order', '')}"
    )
    url = (
        "https://aiplatform.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/locations/global/publishers/google/models/"
        f"{MODEL}:generateContent"
    )
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {_cloud_token()}",
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": before_type,
                                "data": base64.b64encode(before).decode("ascii"),
                            }
                        },
                        {
                            "inlineData": {
                                "mimeType": after_type,
                                "data": base64.b64encode(after).decode("ascii"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _inspection_schema(),
            },
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise PhotoProofError(
            f"Gemini photo inspection failed with status {response.status_code}"
        )
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        value = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise PhotoProofError("Gemini returned invalid photo inspection output") from exc
    if not isinstance(value, dict):
        raise PhotoProofError("Gemini returned invalid photo inspection output")
    return value


def _store(
    *,
    delivery: dict[str, Any],
    before: bytes,
    before_type: str,
    after: bytes,
    after_type: str,
    inspection: dict[str, Any],
) -> dict[str, Any]:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise PhotoProofError("Google Cloud Storage client is unavailable") from exc

    issue_id = str(delivery.get("issue_id") or delivery.get("delivery_id") or "")
    if not issue_id:
        raise PhotoProofError("Issue ID is required")
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
        "owner": "Facilities",
        "model": MODEL,
        "provider": "Vertex AI Gemini",
        "capture_channel": "Google Chat Human Reach",
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


def _record_trusted_completion(issue_id: str) -> dict[str, Any]:
    url = os.environ.get("EVIDENCE_SERVICE_URL", "").strip().rstrip("/")
    if not url:
        raise PhotoProofError("EVIDENCE_SERVICE_URL is required")
    token = id_token.fetch_id_token(GoogleAuthRequest(), url)
    if not token:
        raise PhotoProofError("Unable to obtain trusted evidence service identity token")
    response = requests.post(
        f"{url}/v1/issues/{issue_id}/complete",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={},
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.status_code >= 400:
        raise PhotoProofError(
            str(payload.get("message") or payload.get("error") or response.status_code)
        )
    return payload if isinstance(payload, dict) else {}


def process_message(
    *,
    event: dict[str, Any],
    delivery: dict[str, Any],
    chat_token: str,
) -> dict[str, Any]:
    if delivery.get("owner") != "Facilities":
        raise ValueError("Photo proof is currently supported for Facilities work only.")
    if str(delivery.get("delivery_status") or "") != "COMPLETION_CLAIMED":
        raise ValueError("Use Completed on the Facilities work card before attaching photo proof.")
    if str(delivery.get("authoritative_issue_state") or "ACTION_PENDING") != "ACTION_PENDING":
        raise ValueError("This work has already advanced beyond photo-proof collection.")

    images = _download_images(event, chat_token=chat_token)
    if not images:
        raise ValueError("Attach exactly two images: BEFORE first, AFTER second.")
    (before, before_type, _before_name), (after, after_type, _after_name) = images
    inspection = _inspect(
        delivery=delivery,
        before=before,
        before_type=before_type,
        after=after,
        after_type=after_type,
    )
    record = _store(
        delivery=delivery,
        before=before,
        before_type=before_type,
        after=after,
        after_type=after_type,
        inspection=inspection,
    )

    if inspection.get("completion_supported") is not True:
        return {
            "accepted": False,
            "message": str(
                inspection.get("summary")
                or "The before/after photos do not visibly support completion."
            ),
            "photo_evidence": record,
        }

    issue_id = str(delivery.get("issue_id") or delivery.get("delivery_id") or "")
    trusted = _record_trusted_completion(issue_id)
    return {
        "accepted": True,
        "message": (
            "Gemini found the before/after photos visibly support the repair. "
            "The photos were stored as supporting evidence and the separate trusted "
            "Facilities evidence path moved the issue to independent verification."
        ),
        "photo_evidence": record,
        "trusted_evidence": trusted,
    }
