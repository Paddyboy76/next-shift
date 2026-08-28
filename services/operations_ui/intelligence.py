from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import os
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

from google.cloud import firestore


PROJECT_ID = "next-shift-506004"
ISSUES = "handover_issues"
MEMORY_SNAPSHOTS = "operational_memory_snapshots"
MEMORY_TIMEOUT_SECONDS = 3


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def analyze_issues(issues: list[dict[str, Any]]) -> dict[str, Any]:
    owners = Counter(str(item.get("owner") or "Unknown") for item in issues)
    states = Counter(str(item.get("state") or "UNKNOWN") for item in issues)
    closure_minutes: dict[str, list[float]] = {}
    locations: Counter[str] = Counter()

    for issue in issues:
        workflow_input = issue.get("workflow_input") or {}
        location = next(
            (
                str(workflow_input[key]).strip()
                for key in ("room", "service_location", "destination", "origin")
                if workflow_input.get(key)
            ),
            "",
        )
        if location:
            locations[location] += 1

        if issue.get("state") != "CLOSED":
            continue
        created = _parse(issue.get("created_at"))
        closed = _parse(issue.get("closed_at") or issue.get("updated_at"))
        if created and closed and closed >= created:
            closure_minutes.setdefault(str(issue.get("owner") or "Unknown"), []).append(
                (closed - created).total_seconds() / 60
            )

    timing = {
        owner: round(mean(values), 1)
        for owner, values in sorted(closure_minutes.items())
        if values
    }
    repeated = [
        {"location": location, "issue_count": count}
        for location, count in locations.most_common(5)
        if count > 1
    ]
    recommendations: list[dict[str, Any]] = []
    if owners:
        busiest, count = owners.most_common(1)[0]
        recommendations.append(
            {
                "pattern": f"{busiest} carries the largest share of historical work.",
                "why_it_matters": (
                    f"{count} of {len(issues)} historical issues are owned by {busiest}, "
                    "which concentrates operational load on one channel."
                ),
                "recommended_change": f"Review {busiest} staffing and capacity for the busiest shifts.",
                "affected_scope": busiest,
                "expected_improvement": "Reduced queueing on the busiest operational channel.",
                "confidence": "MEDIUM",
            }
        )
    if timing:
        slowest = max(timing, key=timing.get)
        recommendations.append(
            {
                "pattern": f"{slowest} has the slowest observed closure time.",
                "why_it_matters": (
                    f"Observed mean closure time for {slowest} is {timing[slowest]} minutes "
                    "across completed synthetic work."
                ),
                "recommended_change": f"Inspect {slowest} handoffs and evidence collection first.",
                "affected_scope": slowest,
                "expected_improvement": "Shorter time from claim to verified closure.",
                "confidence": "MEDIUM",
            }
        )
    if repeated:
        location = repeated[0]["location"]
        issue_count = repeated[0]["issue_count"]
        recommendations.append(
            {
                "pattern": f"Recurring operational demand at {location}.",
                "why_it_matters": f"{location} generated {issue_count} separate historical issues.",
                "recommended_change": f"Investigate the underlying cause at {location} rather than repeating repairs.",
                "affected_scope": location,
                "expected_improvement": "Fewer repeat issues from the same location.",
                "confidence": "LOW",
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "pattern": "Insufficient completed history for trend analysis.",
                "why_it_matters": "Too few completed synthetic operations exist to support a reliable pattern.",
                "recommended_change": "Collect more completed synthetic operations before acting on trends.",
                "affected_scope": "All channels",
                "expected_improvement": "Trend recommendations become supportable.",
                "confidence": "LOW",
            }
        )

    return {
        "sample_size": len(issues),
        "owner_counts": dict(sorted(owners.items())),
        "state_counts": dict(sorted(states.items())),
        "mean_closure_minutes_by_owner": timing,
        "repeated_locations": repeated,
        "recommendations": recommendations,
        "recommendation_source": "LOCAL_DETERMINISTIC_FALLBACK",
    }


def _local_intelligence() -> dict[str, Any]:
    db = _db()
    snapshot = db.collection(MEMORY_SNAPSHOTS).document("current").get()
    if snapshot.exists:
        result = snapshot.to_dict() or {}
    else:
        issues = [item.to_dict() or {} for item in db.collection(ISSUES).stream()]
        result = {
            **analyze_issues(issues),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "memory_bank": {"status": "NOT_SYNCED"},
        }

    result["authority"] = "ADVISORY_ONLY"
    result["current_state_authority"] = "Firestore handover_issues"
    result["may_mutate_workflow"] = False
    return result


def current_intelligence() -> dict[str, Any]:
    memory_url = os.environ.get("MEMORY_SERVICE_URL", "").strip().rstrip("/")
    if memory_url:
        try:
            token = id_token.fetch_id_token(Request(), memory_url)
            response = requests.get(
                f"{memory_url}/v1/intelligence",
                headers={"Authorization": f"Bearer {token}"},
                timeout=MEMORY_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict):
                return result
        except (requests.RequestException, ValueError):
            pass

    return _local_intelligence()
