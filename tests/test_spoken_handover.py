from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


MODULE_PATH = Path(__file__).parents[1] / "services" / "operations_ui" / "spoken.py"
SPEC = importlib.util.spec_from_file_location("spoken_handover_test_module", MODULE_PATH)
spoken = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(spoken)


def test_gemini_audio_transcription_returns_auditable_nonpersistent_receipt():
    response = Mock(status_code=200)
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"transcript":"The loading bay door is stuck.",'
            '"language":"English","uncertain_segments":[]}'
        )}]}}]
    }
    with patch.object(spoken, "_access_token", return_value="token"), patch.object(
        spoken.requests, "post", return_value=response
    ) as post:
        result = spoken.transcribe_spoken_handover(audio=b"synthetic-audio", mime_type="audio/wav")

    assert result["transcript"] == "The loading bay door is stuck."
    assert result["receipt"]["audio_persisted"] is False
    assert result["receipt"]["operator_review_required"] is True
    assert result["receipt"]["audio_sha256"] == hashlib.sha256(b"synthetic-audio").hexdigest()
    assert post.call_args.kwargs["json"]["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "audio/wav"


def test_spoken_receipt_binds_exact_transcript_to_durable_source_reference():
    message = "A synthetic loading bay door is stuck."
    receipt = {
        "audit_reference": "spoken-handover:test",
        "transcript_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "audio_sha256": "a" * 64,
        "model": "gemini-2.5-flash",
    }
    source = spoken.validated_spoken_source(message, receipt)
    assert source.startswith("spoken-handover:test:audio-sha256:")
    with pytest.raises(ValueError, match="Transcript changed"):
        spoken.validated_spoken_source(message + " edited", receipt)


def test_spoken_handover_rejects_oversize_or_unsupported_audio():
    with pytest.raises(ValueError):
        spoken.transcribe_spoken_handover(audio=b"x", mime_type="application/octet-stream")
    with pytest.raises(ValueError):
        spoken.transcribe_spoken_handover(
            audio=b"x" * (spoken.MAX_AUDIO_BYTES + 1), mime_type="audio/wav"
        )
