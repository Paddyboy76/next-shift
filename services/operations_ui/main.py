from __future__ import annotations

from io import BytesIO
import uuid

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_file

from completion import (
    record_trusted_completion,
    run_independent_verifier,
)
from coverage_arbitration import arbitrate_coverage
from critique import review_coverage
from data import (
    dashboard_summary,
    get_issue_bundle,
    list_issues,
    list_shift_snapshots,
)
from intelligence import current_intelligence
from photo_evidence import (
    MAX_IMAGE_BYTES,
    PhotoEvidenceError,
    image_bytes,
    inspect_and_store,
    list_photo_evidence,
)
from recovery import create_plan, sanction_plan
from runtime import submit_handover
from spoken import (
    MAX_AUDIO_BYTES,
    SpokenHandoverError,
    transcribe_spoken_handover,
    validated_spoken_source,
)
from state_authority import persist_handover_proposals
from trace import build_lifecycle_trace


app = Flask(__name__)


def _coverage_review_explanation(review: dict) -> str:
    summary = str(review.get("summary") or "").strip()
    findings = review.get("findings")
    parts: list[str] = []
    if summary:
        parts.append(summary)
    if isinstance(findings, list):
        for finding in findings[:3]:
            if not isinstance(finding, dict):
                continue
            finding_type = str(finding.get("type") or "review").replace("_", " ").title()
            detail = str(finding.get("detail") or "").strip()
            if detail:
                parts.append(f"{finding_type}: {detail}")
    return " ".join(parts).strip()


def _photo_records(issue_id: str) -> list[dict]:
    try:
        return list_photo_evidence(issue_id)
    except PhotoEvidenceError:
        return []


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/trace/<issue_id>")
def lifecycle_trace_page(issue_id: str):
    try:
        bundle = get_issue_bundle(issue_id)
    except KeyError:
        return render_template("trace.html", trace=None, error="Issue not found"), 404
    return render_template("trace.html", trace=build_lifecycle_trace(bundle), error=None)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "next-shift-operations"})


@app.get("/api/summary")
def summary():
    return jsonify(dashboard_summary())


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
    return jsonify({"issues": list_issues(include_human_reach=True)})


@app.get("/api/issues/<issue_id>")
def issue_detail(issue_id: str):
    try:
        result = get_issue_bundle(issue_id)
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    result["photo_evidence"] = _photo_records(issue_id)
    return jsonify(result)


@app.get("/api/issues/<issue_id>/photo-evidence/<evidence_id>/<kind>")
def photo_evidence_image(issue_id: str, evidence_id: str, kind: str):
    try:
        data, mime_type = image_bytes(issue_id, evidence_id, kind)
    except (KeyError, PhotoEvidenceError):
        return jsonify({"error": "photo_evidence_not_found"}), 404
    return send_file(BytesIO(data), mimetype=mime_type, max_age=300)


@app.post("/api/issues/<issue_id>/photo-evidence")
def record_photo_evidence(issue_id: str):
    try:
        bundle = get_issue_bundle(issue_id)
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    issue = bundle.get("issue") or {}
    if issue.get("owner") != "Facilities":
        return jsonify({"error": "photo_evidence_facilities_only"}), 409
    if issue.get("state") != "ACTION_PENDING":
        return jsonify({"error": "photo_evidence_state_mismatch", "message": "Photo proof is accepted only while Facilities work is awaiting completion evidence."}), 409

    before = request.files.get("before")
    after = request.files.get("after")
    if before is None or after is None:
        return jsonify({"error": "before_and_after_images_required"}), 400
    before_bytes = before.read(MAX_IMAGE_BYTES + 1)
    after_bytes = after.read(MAX_IMAGE_BYTES + 1)
    try:
        record = inspect_and_store(
            issue=issue,
            before=before_bytes,
            before_type=before.mimetype or "application/octet-stream",
            after=after_bytes,
            after_type=after.mimetype or "application/octet-stream",
        )
    except ValueError as exc:
        return jsonify({"error": "invalid_photo_evidence", "message": str(exc)}), 400
    except PhotoEvidenceError as exc:
        return jsonify({"error": "photo_evidence_failed", "message": str(exc)}), 502

    inspection = record.get("inspection") or {}
    if inspection.get("completion_supported") is not True:
        return jsonify({
            "status": "photo_review_required",
            "message": str(inspection.get("summary") or "The before/after images do not visibly support completion."),
            "photo_evidence": record,
        }), 409

    try:
        trusted = record_trusted_completion(issue_id)
    except RuntimeError as exc:
        return jsonify({
            "status": "photo_supported_but_trusted_evidence_failed",
            "message": str(exc),
            "photo_evidence": record,
        }), 502

    return jsonify({
        "status": "photo_evidence_accepted",
        "message": "Gemini found the before/after photos visually support the repair. Supporting photo evidence was stored privately; source-specific trusted evidence was recorded separately for independent verification.",
        "photo_evidence": record,
        "trusted_evidence": trusted,
    }), 201


@app.get("/api/issues/<issue_id>/trace")
def issue_trace(issue_id: str):
    try:
        bundle = get_issue_bundle(issue_id)
    except KeyError:
        return jsonify({"error": "not_found"}), 404
    return jsonify(build_lifecycle_trace(bundle))


@app.post("/api/issues/<issue_id>/complete")
def complete_issue(issue_id: str):
    try:
        result = record_trusted_completion(issue_id)
    except RuntimeError as exc:
        return jsonify({"error": "trusted_evidence_failed", "message": str(exc)}), 502
    return jsonify(result)


@app.post("/api/issues/<issue_id>/verify")
def verify_issue(issue_id: str):
    try:
        result = run_independent_verifier(issue_id)
    except RuntimeError as exc:
        return jsonify({"error": "verification_failed", "message": str(exc)}), 502
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
    return jsonify({"snapshots": list_shift_snapshots()})


@app.post("/api/intake")
def intake():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400

    message = payload.get("message")
    if not isinstance(message, str):
        return jsonify({"error": "invalid_request"}), 400
    message = message.strip()
    if not message or len(message) > 8000:
        return jsonify({"error": "invalid_request"}), 400

    authenticated_user = request.headers.get("X-Goog-Authenticated-User-Email", "operations-ui")
    try:
        spoken_source = validated_spoken_source(message, payload.get("spoken_receipt"))
    except ValueError as exc:
        return jsonify({"error": "invalid_spoken_receipt", "message": str(exc)}), 400

    intake_reference = spoken_source or ("operations-ui:" + str(uuid.uuid4()))
    result = submit_handover(message=message, user_id=authenticated_user, request_id=intake_reference)
    if result.get("blocked") is True:
        return jsonify(result)
    if result.get("structured_output") is not True:
        return jsonify({
            "blocked": False,
            "status": "invalid_agent_output",
            "error": "structured_output_required",
            "message": result.get("message", "The Agent Runtime did not return the required structured intake result. No durable work was created."),
        }), 502

    proposals = result.pop("proposals", [])
    if not isinstance(proposals, list):
        return jsonify({
            "blocked": False,
            "status": "invalid_agent_output",
            "error": "invalid_proposal_payload",
            "message": "The structured intake result contained an invalid proposal payload. No durable work was created.",
        }), 502
    if not proposals:
        result["status"] = "accepted_no_work"
        result["issue_count"] = 0
        result["issues"] = []
        return jsonify(result)

    source_reference = intake_reference
    try:
        coverage_review = review_coverage(message=message, proposals=proposals, source_reference=source_reference)
    except RuntimeError as exc:
        return jsonify({
            "blocked": False,
            "status": "coverage_review_failed",
            "error": "coverage_critic_failure",
            "message": "Independent coverage review failed; no operational work was created.",
            "detail": str(exc),
            "intake_reference": source_reference,
        }), 502

    result["coverage_review"] = coverage_review
    arbitration = arbitrate_coverage(proposals, coverage_review)
    dispatchable = list(arbitration["dispatchable"])
    held = list(arbitration["held"])
    if not dispatchable:
        explanation = _coverage_review_explanation(coverage_review)
        result.update({
            "status": "human_review_required",
            "issue_count": 0,
            "issues": [],
            "held_issue_count": len(held),
            "held_proposals": held,
            "review_required": True,
            "message": "Coverage review found a blocking routing/duplication concern. No operational work was dispatched." + (f" Review: {explanation}" if explanation else ""),
        })
        return jsonify(result), 409

    analysis_message = str(result.get("message", "")).strip()
    try:
        created = persist_handover_proposals(proposals=dispatchable, source_reference=source_reference)
    except RuntimeError as exc:
        return jsonify({
            "blocked": False,
            "status": "persistence_failed",
            "error": "state_authority_failure",
            "message": "Handover analysis succeeded, but State Authority did not persist all dispatchable work. The failure is visible and requires operator attention.",
            "detail": str(exc),
            "intake_reference": source_reference,
        }), 502

    created_summary = ", ".join(f"{issue.get('id')} ({issue.get('owner')})" for issue in created)
    review_required = bool(arbitration["review_required"])
    held_message = f" Held {len(held)} disputed proposal(s) for operator review." if held else ""
    result.update({
        "status": "accepted_with_review" if review_required else "accepted",
        "intake_reference": source_reference,
        "issue_count": len(created),
        "issues": created,
        "held_issue_count": len(held),
        "held_proposals": held,
        "review_required": review_required,
        "message": f"Created {len(created)} durable operational issue(s) through State Authority: {created_summary}." + held_message + (f"\n\n{analysis_message}" if analysis_message else ""),
    })
    return jsonify(result)


@app.post("/api/spoken-handover/transcribe")
def transcribe_handover():
    if request.content_length and request.content_length > MAX_AUDIO_BYTES + 65536:
        return jsonify({"error": "audio_too_large"}), 413
    upload = request.files.get("audio")
    if upload is None:
        return jsonify({"error": "audio_required"}), 400
    audio = upload.read(MAX_AUDIO_BYTES + 1)
    try:
        result = transcribe_spoken_handover(audio=audio, mime_type=upload.mimetype or "application/octet-stream")
    except ValueError as exc:
        return jsonify({"error": "invalid_audio", "message": str(exc)}), 400
    except SpokenHandoverError as exc:
        return jsonify({"error": "transcription_failed", "message": str(exc)}), 502
    return jsonify(result)
