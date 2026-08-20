from __future__ import annotations

import base64
import json
from typing import Any

from flask import Flask
from flask import jsonify
from flask import request

from workflow import process_facilities_issue


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": (
                "next-shift-facilities"
            ),
        }
    )


@app.post("/pubsub")
def pubsub():
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

    if not isinstance(attributes, dict):
        return (
            jsonify(
                {"error": "invalid_attributes"}
            ),
            400,
        )

    if attributes.get("owner") != "Facilities":
        return (
            jsonify(
                {"error": "wrong_owner"}
            ),
            403,
        )

    encoded_data = message.get("data")

    if not isinstance(encoded_data, str):
        return (
            jsonify(
                {"error": "missing_data"}
            ),
            400,
        )

    try:
        payload = json.loads(
            base64.b64decode(
                encoded_data,
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

    if not isinstance(payload, dict):
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
        result = process_facilities_issue(
            issue_id=issue_id,
            facility_type=workflow_input.get(
                "facility_type",
                "plumbing",
            ),
            location=workflow_input.get(
                "location",
                "Room 402",
            ),
        )
    except Exception as exc:
        print(
            f"FACILITIES_PROCESSING_FAILED "
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
        f"FACILITIES_PROCESSED "
        f"issue_id={issue_id} "
        f"state={result['state']} "
        f"work_order_id="
        f"{result['work_order_id']}",
        flush=True,
    )

    return ("", 204)
