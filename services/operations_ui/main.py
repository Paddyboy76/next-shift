from __future__ import annotations

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request

from data import (
    dashboard_summary,
    get_issue_bundle,
    list_issues,
    list_shift_snapshots,
)
from runtime import submit_handover


app = Flask(__name__)


@app.get("/")
def index():
    return render_template(
        "index.html"
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": (
                "next-shift-operations"
            ),
        }
    )


@app.get("/api/summary")
def summary():
    return jsonify(
        dashboard_summary()
    )


@app.get("/api/issues")
def issues():
    return jsonify(
        {
            "issues": list_issues(),
        }
    )


@app.get("/api/issues/<issue_id>")
def issue_detail(
    issue_id: str,
):
    try:
        result = get_issue_bundle(
            issue_id
        )
    except KeyError:
        return (
            jsonify(
                {"error": "not_found"}
            ),
            404,
        )

    return jsonify(result)


@app.get("/api/shifts")
def shifts():
    return jsonify(
        {
            "snapshots": (
                list_shift_snapshots()
            ),
        }
    )


@app.post("/api/intake")
def intake():
    payload = request.get_json(
        silent=True
    )

    if not isinstance(
        payload,
        dict,
    ):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    message = payload.get(
        "message"
    )

    if not isinstance(
        message,
        str,
    ):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    message = message.strip()

    if (
        not message
        or len(message) > 8000
    ):
        return (
            jsonify(
                {"error": "invalid_request"}
            ),
            400,
        )

    authenticated_user = (
        request.headers.get(
            "X-Goog-Authenticated-User-Email",
            "operations-ui",
        )
    )

    result = submit_handover(
        message=message,
        user_id=authenticated_user,
    )

    return jsonify(result)
