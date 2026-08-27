from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import uuid
from typing import Any

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
import requests


PROJECT_ID = "next-shift-506004"
LOCATION = "global"
DEFAULT_MODEL = "gemini-3.5-flash"
MAX_AUDIO_BYTES = 4 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/mp3",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
}


class SpokenHandoverError(RuntimeError):
    pass


def _access_token() -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise SpokenHandoverError("Unable to obtain Vertex AI credentials")
    return credentials.token


def _model() -> str:
    return os.environ.get("SPOKEN_HANDOVER_MODEL", DEFAULT_MODEL).strip()


def _generate_url(model: str) -> str:
    return (
        "https://aiplatform.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/"
        f"{model}:generateContent"
    )


def _response_json(body: dict[str, Any]) -> dict[str, Any]:
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        value = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise SpokenHandoverError("Gemini returned invalid transcription output") from exc
    if not isinstance(value, dict):
        raise SpokenHandoverError("Gemini returned invalid transcription output")
    transcript = value.get("transcript")
    if not isinstance(transcript, str) or not transcript.strip():
        raise SpokenHandoverError("Gemini did not detect a spoken handover")
    value["transcript"] = transcript.strip()
    return value


def transcribe_spoken_handover(*, audio: bytes, mime_type: str) -> dict[str, Any]:
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("Audio must be between 1 byte and 4 MiB")
    normalized_type = mime_type.split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError("Unsupported audio type")

    model = _model()
    response = requests.post(
        _generate_url(model),
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        },
        json={
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Transcribe this synthetic, non-clinical operational shift "
                            "handover exactly enough for an operator to review before "
                            "governed intake. Do not infer missing facts, create tasks, "
                            "or make clinical decisions. Return JSON with transcript, "
                            "language, and uncertain_segments (an array of short strings)."
                        )
                    },
                    {
                        "inlineData": {
                            "mimeType": normalized_type,
                            "data": base64.b64encode(audio).decode("ascii"),
                        }
                    },
                ],
            }],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "transcript": {"type": "STRING"},
                        "language": {"type": "STRING"},
                        "uncertain_segments": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": ["transcript", "language", "uncertain_segments"],
                },
            },
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise SpokenHandoverError(
            f"Gemini transcription failed with status {response.status_code}"
        )

    result = _response_json(response.json())
    uncertain = result.get("uncertain_segments", [])
    if not isinstance(uncertain, list) or not all(isinstance(item, str) for item in uncertain):
        uncertain = []

    audit_reference = f"spoken-handover:{uuid.uuid4()}"
    receipt = {
        "audit_reference": audit_reference,
        "model": model,
        "provider": "Vertex AI Gemini",
        "mime_type": normalized_type,
        "audio_bytes": len(audio),
        "audio_sha256": hashlib.sha256(audio).hexdigest(),
        "transcript_sha256": hashlib.sha256(
            result["transcript"].encode("utf-8")
        ).hexdigest(),
        "audio_persisted": False,
        "operator_review_required": True,
    }
    logging.warning(
        json.dumps(
            {
                "event_type": "spoken_handover.transcribed",
                **receipt,
                "uncertain_segment_count": len(uncertain),
                "transcript_logged": False,
            },
            sort_keys=True,
        )
    )
    return {
        "transcript": result["transcript"],
        "language": str(result.get("language", "und")),
        "uncertain_segments": uncertain,
        "receipt": receipt,
    }


def validated_spoken_source(message: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Invalid spoken handover receipt")
    audit_reference = value.get("audit_reference")
    transcript_sha256 = value.get("transcript_sha256")
    audio_sha256 = value.get("audio_sha256")
    model = value.get("model")
    if not all(isinstance(item, str) and item for item in (
        audit_reference, transcript_sha256, audio_sha256, model
    )):
        raise ValueError("Invalid spoken handover receipt")
    if not audit_reference.startswith("spoken-handover:"):
        raise ValueError("Invalid spoken handover receipt")
    expected = hashlib.sha256(message.encode("utf-8")).hexdigest()
    if transcript_sha256 != expected:
        raise ValueError("Transcript changed after transcription; transcribe again or use text intake")
    return f"{audit_reference}:audio-sha256:{audio_sha256}:model:{model}"
