from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from flask import Flask, jsonify
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel


PROJECT = "next-shift-506004"
LOCATION = "asia-southeast1"
ENGINE = "projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048"
SCOPE = {"context": "next-shift-operational-intelligence"}
MODEL = os.environ.get("ADVISOR_MODEL", "gemini-2.5-flash")
META_PREFIX = "NS_ADVISORY_V2_META "
RECOMMENDATION_PREFIX = "NS_ADVISORY_V2_RECOMMENDATION "
MAX_MEMORY_CONTEXT = 5
app = Flask(__name__)


def parsed(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def aggregate_history(documents: list[Any]) -> dict[str, Any]:
    issues = [item.to_dict() or {} for item in documents]
    owners = Counter(str(item.get("owner") or "Unknown") for item in issues)
    states = Counter(str(item.get("state") or "UNKNOWN") for item in issues)
    durations: dict[str, list[float]] = {}
    locations: Counter[str] = Counter()
    evidence_refs: list[dict[str, Any]] = []
    for document, issue in zip(documents, issues):
        data = issue.get("workflow_input") or {}
        location = next((str(data[key]).strip() for key in ("room", "service_location", "destination", "origin") if data.get(key)), "")
        if location:
            locations[location] += 1
        created = parsed(issue.get("created_at"))
        closed = parsed(issue.get("closed_at") or issue.get("updated_at"))
        if issue.get("state") == "CLOSED" and created and closed and closed >= created:
            durations.setdefault(str(issue.get("owner") or "Unknown"), []).append((closed - created).total_seconds() / 60)
        evidence_refs.append({
            "firestore_document": f"handover_issues/{document.id}", "owner": issue.get("owner"),
            "state": issue.get("state"), "location": location or None,
            "created_at": created.isoformat() if created else None,
            "closed_at": closed.isoformat() if closed else None,
        })
    return {
        "sample_size": len(issues), "owner_counts": dict(sorted(owners.items())),
        "state_counts": dict(sorted(states.items())),
        "mean_closure_minutes_by_owner": {key: round(mean(value), 1) for key, value in sorted(durations.items()) if value},
        "repeated_locations": [{"location": key, "issue_count": value} for key, value in locations.most_common(10) if value > 1],
        "historical_issue_refs": evidence_refs,
    }


def scoped_memories(client: Any) -> list[Any]:
    memories = [item for item in client.agent_engines.memories.list(name=ENGINE) if item.scope == SCOPE]
    memories.sort(key=lambda item: item.create_time or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return memories


def generate_recommendations(aggregate: dict[str, Any], memory_context: list[dict[str, str]]) -> list[dict[str, Any]]:
    prompt = {
        "role": "Operational Improvement Advisor for synthetic 24/7 enterprise operations",
        "authority_contract": {"authority": "ADVISORY_ONLY", "current_state_authority": "Firestore", "may_mutate_workflow": False},
        "instructions": [
            "Reason over the supplied historical aggregates and managed Memory Bank context.",
            "Return 1 to 3 actionable recommendations, never a current-state decision.",
            "Every recommendation must identify the observed pattern, why it matters, a concrete change to consider, affected owner/location/process, reasonable expected improvement, confidence, and exact supporting references.",
            "Keep each prose field under 220 characters and cite no more than 3 Firestore references and 3 Memory Bank references.",
            "Use only supplied evidence. Do not invent causes, outcomes, records, or current issue state.",
            "Firestore references must exactly match historical_issue_refs. Memory references must exactly match supplied memory_name values.",
        ],
        "historical_aggregate": aggregate,
        "managed_memory_context": memory_context,
    }
    response = GenerativeModel(MODEL).generate_content(
        json.dumps(prompt, sort_keys=True),
        generation_config=GenerationConfig(temperature=0.2, response_mime_type="application/json", response_schema={
            "type": "OBJECT", "properties": {"recommendations": {"type": "ARRAY", "items": {
                "type": "OBJECT", "properties": {
                    "pattern": {"type": "STRING"}, "why_it_matters": {"type": "STRING"},
                    "recommended_change": {"type": "STRING"}, "affected_scope": {"type": "STRING"},
                    "expected_improvement": {"type": "STRING"},
                    "confidence": {"type": "STRING", "enum": ["LOW", "MEDIUM", "HIGH"]},
                    "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "memory_records": {"type": "ARRAY", "items": {"type": "STRING"}},
                }, "required": ["pattern", "why_it_matters", "recommended_change", "affected_scope", "expected_improvement", "confidence", "evidence", "memory_records"]
            }}}, "required": ["recommendations"]
        }),
    )
    recommendations = json.loads(response.text).get("recommendations") or []
    if not recommendations:
        raise RuntimeError("Gemini returned no operational recommendations")
    return recommendations


def sync_memory() -> dict[str, Any]:
    documents = list(firestore.Client(project=PROJECT).collection("handover_issues").stream())
    aggregate = aggregate_history(documents)
    vertexai.init(project=PROJECT, location=LOCATION)
    client = vertexai.Client(project=PROJECT, location=LOCATION)
    previous = scoped_memories(client)[:MAX_MEMORY_CONTEXT]
    recommendations = generate_recommendations(aggregate, [{"memory_name": item.name, "fact": item.fact or ""} for item in previous])
    advisory_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    generated_at = datetime.now(timezone.utc).isoformat()
    recommendation_memory_names = []
    for index, recommendation in enumerate(recommendations):
        recommendation_fact = RECOMMENDATION_PREFIX + json.dumps({
            "advisory_id": advisory_id, "index": index, "recommendation": recommendation,
        }, separators=(",", ":"), sort_keys=True)
        if len(recommendation_fact) >= 2048:
            raise RuntimeError("Gemini recommendation exceeds the Memory Bank fact limit")
        operation = client.agent_engines.memories.create(name=ENGINE, fact=recommendation_fact, scope=SCOPE)
        if operation.error or not operation.response:
            raise RuntimeError(f"Memory Bank recommendation create failed: {operation.error or 'missing response'}")
        recommendation_memory_names.append(str(operation.response.name))
    payload = {
        **{key: value for key, value in aggregate.items() if key != "historical_issue_refs"},
        "recommendations": recommendations, "generated_at": generated_at,
        "generated_by": {"provider": "Vertex AI", "model": MODEL, "ai_generated": True},
        "authority": "ADVISORY_ONLY", "current_state_authority": "Firestore", "may_mutate_workflow": False,
        "provenance": {"source_collection": "handover_issues", "synthetic_only": True, "issue_count": len(documents), "managed_memory_inputs": [item.name for item in previous]},
    }
    metadata = {key: value for key, value in payload.items() if key != "recommendations"}
    metadata["advisory_id"] = advisory_id
    metadata["recommendation_memory_names"] = recommendation_memory_names
    fact = META_PREFIX + json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    if len(fact) >= 2048:
        raise RuntimeError("Advisory metadata exceeds the Memory Bank fact limit")
    operation = client.agent_engines.memories.create(name=ENGINE, fact=fact, scope=SCOPE)
    if operation.error or not operation.response:
        raise RuntimeError(f"Memory Bank create failed: {operation.error or 'missing response'}")
    payload["memory_bank"] = {"status": "SYNCED", "agent_engine": ENGINE, "memory_name": str(operation.response.name), "scope": SCOPE}
    return payload


def _payload_from_memory(memory: Any, prefix: str) -> dict[str, Any] | None:
    fact = memory.fact or ""
    if not fact.startswith(prefix):
        return None
    try:
        return json.loads(fact[len(prefix):])
    except json.JSONDecodeError:
        return None


def inspect_intelligence() -> dict[str, Any]:
    client = vertexai.Client(project=PROJECT, location=LOCATION)
    memories = scoped_memories(client)
    for memory in memories:
        payload = _payload_from_memory(memory, META_PREFIX)
        if payload is not None:
            recommendation_names = set(payload.pop("recommendation_memory_names", []))
            recommendations = []
            for item in memories:
                if item.name not in recommendation_names:
                    continue
                record = _payload_from_memory(item, RECOMMENDATION_PREFIX)
                if record and record.get("advisory_id") == payload.get("advisory_id"):
                    recommendations.append(record)
            recommendations.sort(key=lambda item: item.get("index", 0))
            payload["recommendations"] = [item["recommendation"] for item in recommendations]
            payload["memory_bank"] = {"status": "SYNCED", "agent_engine": ENGINE, "memory_name": memory.name, "scope": SCOPE}
            return payload
    return {"authority": "ADVISORY_ONLY", "current_state_authority": "Firestore", "may_mutate_workflow": False, "recommendations": [], "memory_bank": {"status": "NOT_SYNCED", "agent_engine": ENGINE, "scope": SCOPE}}


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
