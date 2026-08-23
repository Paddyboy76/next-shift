from __future__ import annotations

import uuid

from flask import Flask
from flask import jsonify
from recovery import create_plan, sanction_plan
from flask import render_template
from flask import request

from completion import (
    record_trusted_completion,
    run_independent_verifier,
)
from critique import review_coverage
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
from trace import build_lifecycle_trace
from intelligence import current_intelligence


app = Flask(__name__)


@app.get("/")
def index():
    return render_template(
        "index.html"
    )


@app.get("/trace/<issue_id>")
def lifecycle_trace_page(
    issue_id: str,
):
    try:
        bundle = get_issue_bundle(
            issue_id
        )
    except KeyError:
        return (
            render_template(
                "trace.html",
                trace=None,
                error="Issue not found",
            ),
            404,
        )

    return render_template(
        "trace.html",
        trace=build_lifecycle_trace(bundle),
        error=None,
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


@app.get("/api/intelligence")
def intelligence():
    return jsonify(current_intelligence())


@app.get("/api/platform")
def platform():
    return jsonify(
        {
            "agent_runtime": {
                "resource": "projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048",
                "framework": "google-adk",
                "identity": "AGENT_IDENTITY",
                "lifecycle": "DEPLOYED",
            },
            "observability": {
                "provider": "Cloud Run request tracing",
                "export": "Cloud Logging trace and span correlation",
            },
            "registry": {
                "api": "agentregistry.googleapis.com",
                "agent": "Next Shift",
                "service": "next-shift-runtime",
                "verification": "LIVE_REGISTRY_VERIFIED",
            },
        }
    )


@app.get("/api/issues")
def issues():
    return jsonify(
        {
            "issues": list_issues(
                include_human_reach=True
            ),
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


@app.get("/api/issues/<issue_id>/trace")
def issue_trace(
    issue_id: str,
):
    try:
        bundle = get_issue_bundle(
            issue_id
        )
    except KeyError:
        return (
            jsonify(
                {"error": "not_found"}
            ),
            404,
        )

    return jsonify(
        build_lifecycle_trace(bundle)
    )


@app.post("/api/issues/<issue_id>/complete")
def complete_issue(
    issue_id: str,
):
    try:
        result = record_trusted_completion(
            issue_id
        )
    except RuntimeError as exc:
        return (
            jsonify(
                {
                    "error": "trusted_evidence_failed",
                    "message": str(exc),
                }
            ),
            502,
        )

    return jsonify(result)


@app.post("/api/issues/<issue_id>/verify")
def verify_issue(
    issue_id: str,
):
    try:
        result = run_independent_verifier(
            issue_id
        )
    except RuntimeError as exc:
        return (
            jsonify(
                {
                    "error": "verification_failed",
                    "message": str(exc),
                }
            ),
            502,
        )

    return jsonify(result)


@app.post("/api/issues/<issue_id>/recovery-plan")
def recovery_plan(issue_id: str):
    try:
        return jsonify(create_plan(issue_id)), 201
    except RuntimeError as exc:
        return jsonify({"error": "recovery_planning_failed", "message": str(exc)}), 502


@app.post("/api/issues/<issue_id>/recovery-plans/<plan_id>/sanction")
def recovery_plan_sanction(issue_id: str, plan_id: str):
    try:
        return jsonify(sanction_plan(issue_id, plan_id))
    except RuntimeError as exc:
        return jsonify({"error": "recovery_sanction_failed", "message": str(exc)}), 502


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

    intake_reference = (
        "operations-ui:"
        + str(uuid.uuid4())
    )

    result = submit_handover(
        message=message,
        user_id=authenticated_user,
        request_id=intake_reference,
    )

    if result.get("blocked") is True:
        return jsonify(result)

    if result.get("structured_output") is not True:
        return (
            jsonify(
                {
                    "blocked": False,
                    "status": "invalid_agent_output",
                    "error": "structured_output_required",
                    "message": result.get(
                        "message",
                        (
                            "The Agent Runtime did not return the required "
                            "structured intake result. No durable work was "
                            "created."
                        ),
                    ),
                }
            ),
            502,
        )

    proposals = result.pop(
        "proposals",
        [],
    )

    if not isinstance(proposals, list):
        return (
            jsonify(
                {
                    "blocked": False,
                    "status": "invalid_agent_output",
                    "error": "invalid_proposal_payload",
                    "message": (
                        "The structured intake result contained an invalid "
                        "proposal payload. No durable work was created."
                    ),
                }
            ),
            502,
        )

    if not proposals:
        result["status"] = "accepted_no_work"
        result["issue_count"] = 0
        result["issues"] = []
        return jsonify(result)

    source_reference = intake_reference

    try:
        coverage_review = review_coverage(message=message, proposals=proposals, source_reference=source_reference)
    except RuntimeError as exc:
        return jsonify({"blocked":False,"status":"coverage_review_failed","error":"coverage_critic_failure",
                        "message":"Independent coverage review failed; no operational work was created.",
                        "detail":str(exc),"intake_reference":source_reference}),502
    result["coverage_review"] = coverage_review
    if coverage_review.get("decision") != "PASS":
        result.update({"status":"human_review_required","issue_count":0,"issues":[],
                       "message":"Coverage Critic disagreed with intake. No work was dispatched; the durable review requires operator attention."})
        return jsonify(result),409

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
