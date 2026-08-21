from __future__ import annotations

import uuid

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
from state_authority import (
    persist_handover_proposals,
)


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

    if result.get("blocked") is True:
        return jsonify(result)

    proposals = result.pop(
        "proposals",
        [],
    )

    if not isinstance(proposals, list):
        return (
            jsonify(
                {
                    "blocked": False,
                    "status": "persistence_failed",
                    "error": "invalid_agent_output",
                    "message": (
                        "The intake analysis returned an invalid "
                        "proposal payload. No workflow mutation was made."
                    ),
                }
            ),
            502,
        )

    if not proposals:
        result["issue_count"] = 0
        result["issues"] = []
        return jsonify(result)

    source_reference = (
        "operations-ui:"
        + str(uuid.uuid4())
    )

    analysis_message = str(
        result.get("message", "")
    ).strip()

    try:
        created = persist_handover_proposals(
            proposals=proposals,
            source_reference=source_reference,
        )
    except RuntimeError as exc:
        return (
            jsonify(
                {
                    "blocked": False,
                    "status": "persistence_failed",
                    "error": "state_authority_failure",
                    "message": (
                        "Handover analysis succeeded, but State Authority "
                        "did not persist all proposed work. The failure is "
                        "visible and requires operator attention."
                    ),
                    "detail": str(exc),
                    "intake_reference": source_reference,
                }
            ),
            502,
        )

    created_summary = ", ".join(
        f"{issue.get('id')} ({issue.get('owner')})"
        for issue in created
    )

    result.update(
        {
            "status": "accepted",
            "intake_reference": source_reference,
            "issue_count": len(created),
            "issues": created,
            "message": (
                f"Created {len(created)} durable operational issue(s) "
                f"through State Authority: {created_summary}."
                + (
                    f"\n\n{analysis_message}"
                    if analysis_message
                    else ""
                )
            ),
        }
    )

    return jsonify(result)
