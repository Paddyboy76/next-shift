from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from statistics import mean

from google.cloud import firestore
from flask import Flask, jsonify
import vertexai


PROJECT = "next-shift-506004"
LOCATION = "asia-southeast1"
ENGINE = "projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048"
SCOPE = {"context": "next-shift-operational-intelligence"}
app = Flask(__name__)


def parsed(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def sync_memory():
    db = firestore.Client(project=PROJECT)
    documents = list(db.collection("handover_issues").stream())
    issues = [item.to_dict() or {} for item in documents]
    owners = Counter(str(item.get("owner") or "Unknown") for item in issues)
    states = Counter(str(item.get("state") or "UNKNOWN") for item in issues)
    durations = {}
    locations = Counter()
    for issue in issues:
        data = issue.get("workflow_input") or {}
        location = next((str(data[key]) for key in ("room", "service_location", "destination", "origin") if data.get(key)), "")
        if location:
            locations[location] += 1
        if issue.get("state") == "CLOSED":
            start, end = parsed(issue.get("created_at")), parsed(issue.get("closed_at") or issue.get("updated_at"))
            if start and end and end >= start:
                durations.setdefault(str(issue.get("owner") or "Unknown"), []).append((end-start).total_seconds()/60)
    timing = {key: round(mean(value), 1) for key, value in sorted(durations.items()) if value}
    repeated = [{"location": key, "issue_count": value} for key, value in locations.most_common(5) if value > 1]
    recommendations = []
    if owners:
        owner, count = owners.most_common(1)[0]
        recommendations.append(f"Review {owner} capacity: it represents {count} of {len(issues)} historical issues.")
    if timing:
        slowest = max(timing, key=timing.get)
        recommendations.append(f"Inspect {slowest} handoffs first; its observed mean closure time is {timing[slowest]} minutes.")
    if repeated:
        recommendations.append(f"Investigate recurring operational demand at {repeated[0]['location']} ({repeated[0]['issue_count']} issues).")
    if not recommendations:
        recommendations.append("Collect more completed synthetic operations before acting on trends.")
    generated = datetime.now(timezone.utc).isoformat()
    analysis = {
        "sample_size": len(issues), "owner_counts": dict(sorted(owners.items())),
        "state_counts": dict(sorted(states.items())), "mean_closure_minutes_by_owner": timing,
        "repeated_locations": repeated, "recommendations": recommendations,
    }
    fact = "ADVISORY OPERATIONAL INTELLIGENCE. Firestore remains authoritative for current issue state. " + json.dumps(analysis, sort_keys=True) + f" Provenance: {len(documents)} synthetic Firestore issues at {generated}."
    client = vertexai.Client(project=PROJECT, location=LOCATION)
    operation = client.agent_engines.memories.create(name=ENGINE, fact=fact, scope=SCOPE)
    if operation.error or not operation.response:
        raise RuntimeError(f"Memory Bank create failed: {operation.error or 'missing response'}")
    memory = operation.response
    snapshot = {
        **analysis, "generated_at": generated, "authority": "ADVISORY_ONLY",
        "current_state_authority": "Firestore handover_issues", "may_mutate_workflow": False,
        "provenance": {"source_collection": "handover_issues", "synthetic_only": True, "issue_count": len(documents)},
        "memory_bank": {"status": "SYNCED", "agent_engine": ENGINE, "memory_name": str(memory.name), "scope": SCOPE},
    }
    return snapshot


def inspect_intelligence():
    db = firestore.Client(project=PROJECT)
    issues = [item.to_dict() or {} for item in db.collection("handover_issues").stream()]
    owners = Counter(str(item.get("owner") or "Unknown") for item in issues)
    memories = [
        item for item in vertexai.Client(project=PROJECT, location=LOCATION).agent_engines.memories.list(name=ENGINE)
        if item.scope == SCOPE
    ]
    memories.sort(key=lambda item: item.create_time or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    latest = memories[0] if memories else None
    recommendations = []
    if latest and latest.fact:
        marker = latest.fact.find("{")
        provenance = latest.fact.rfind(" Provenance:")
        if marker >= 0 and provenance > marker:
            recommendations = json.loads(latest.fact[marker:provenance]).get("recommendations", [])
    return {
        "authority": "ADVISORY_ONLY", "current_state_authority": "Firestore handover_issues",
        "may_mutate_workflow": False, "sample_size": len(issues), "owner_counts": dict(sorted(owners.items())),
        "recommendations": recommendations,
        "generated_at": latest.create_time.isoformat() if latest and latest.create_time else None,
        "provenance": {"source_collection": "handover_issues", "synthetic_only": True, "issue_count": len(issues)},
        "memory_bank": {"status": "SYNCED" if latest else "NOT_SYNCED", "agent_engine": ENGINE,
                        "memory_name": latest.name if latest else None, "scope": SCOPE},
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "next-shift-memory-sync"})


@app.post("/v1/sync")
def sync():
    return jsonify(sync_memory())


@app.get("/v1/intelligence")
def intelligence():
    return jsonify(inspect_intelligence())


def main() -> None:
    print(json.dumps(sync_memory(), sort_keys=True))


if __name__ == "__main__":
    main()
