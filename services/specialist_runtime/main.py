from __future__ import annotations

import base64
import json
import os
from typing import Any

from flask import Flask
from flask import jsonify
from flask import request

from workflow import HANDLERS
from workflow import process_issue


app = Flask(__name__)


def _owner() -> str:
    owner = os.environ.get(
        "SPECIALIST_OWNER"
    )

    if owner not in HANDLERS:
        raise RuntimeError(
            "Valid SPECIALIST_OWNER is required"
        )

    return owner


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "specialist-runtime",
            "owner": _owner(),
        }
    )


@app.post("/pubsub")
def pubsub():
    owner = _owner()

    envelope: dict[str, Any] | None = (
        request.get_json(
            silent=True
        )
    )

    if not isinstance(envelope, dict):
        return (
            jsonify(
                {"error": "invalid_envelope"}
            ),
            400,
        )

    message = envelope.get("message")

    if not isinstance(message, dict):
        return (
            jsonify(
                {"error": "invalid_message"}
            ),
            400,
        )

    attributes = message.get(
        "attributes",
        {},
    )

    if (
        not isinstance(attributes, dict)
        or attributes.get("owner") != owner
    ):
        return (
            jsonify(
                {"error": "wrong_owner"}
            ),
            403,
        )

    encoded = message.get("data")

    if not isinstance(encoded, str):
        return (
            jsonify(
                {"error": "missing_data"}
            ),
            400,
        )

    try:
        payload = json.loads(
            base64.b64decode(
                encoded,
                validate=True,
            ).decode("utf-8")
        )
    except (
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return (
            jsonify(
                {"error": "invalid_data"}
            ),
            400,
        )

    if (
        not isinstance(payload, dict)
        or payload.get("owner") != owner
    ):
        return (
            jsonify(
                {"error": "invalid_payload"}
            ),
            400,
        )

    issue_id = payload.get("issue_id")

    workflow_input = payload.get(
        "workflow_input",
        {},
    )

    if (
        not isinstance(issue_id, str)
        or not issue_id
        or not isinstance(
            workflow_input,
            dict,
        )
    ):
        return (
            jsonify(
                {"error": "invalid_payload"}
            ),
            400,
        )

    try:
        result = process_issue(
            owner=owner,
            issue_id=issue_id,
            workflow_input=workflow_input,
        )
    except Exception as exc:
        print(
            f"SPECIALIST_PROCESSING_FAILED "
            f"owner={owner} "
            f"issue_id={issue_id} "
            f"error={type(exc).__name__}:"
            f"{exc}",
            flush=True,
        )

        return (
            jsonify(
                {"error": "processing_failed"}
            ),
            500,
        )

    print(
        f"SPECIALIST_PROCESSED "
        f"owner={owner} "
        f"issue_id={issue_id} "
        f"state={result['to_state']}",
        flush=True,
    )

    return ("", 204)
