# Mission 10 — Active Memory Intelligence + Registry + Observability

This mission is NOT complete merely because Memory Bank stores historical facts.

The primary goal is to make operational memory actively improve future operations.

## A. Active operational intelligence

Build a real Operational Improvement Advisor.

The system must:

1. Use historical synthetic operational records and managed Memory Bank.
2. Detect useful cross-shift and cross-department patterns.
3. Use Gemini reasoning to interpret those patterns.
4. Produce actionable plain-English operational recommendations.
5. Surface those recommendations visibly to managers/operators.
6. Include evidence/provenance for every recommendation.
7. Refresh advice automatically rather than requiring a human to manually ask for analysis.

Examples of useful patterns:

- recurring transport delays by location or shift period;
- repeated asset shortages;
- repeated Facilities issues in one location;
- recurring SLA breaches;
- repeated handoff work that requires escalation;
- time between request, assignment, action and verified completion;
- cross-department dependencies that repeatedly create downstream delay.

Recommendations should answer:

- What pattern did we observe?
- What evidence supports it?
- Why does it matter operationally?
- What should the enterprise consider changing?
- Which owner/location/process is affected?
- What improvement could reasonably result?
- How confident is the system?
- Which Memory Bank records or historical facts support the recommendation?

Required advisory contract:

authority = ADVISORY_ONLY
current_state_authority = Firestore
may_mutate_workflow = false

The advisor must never establish current issue state and must never mutate workflow state.

Prefer a genuine Gemini/Vertex AI reasoning step over hard-coded recommendation templates.

Deterministic aggregation may prepare evidence for the model, but deterministic aggregation alone is insufficient.

## B. Active refresh

The intelligence must be active.

Prefer the smallest reliable Google-native mechanism:

- refresh after relevant operational history changes; or
- refresh on shift transition; or
- use Cloud Scheduler for a periodic refresh.

Do not create unnecessary infrastructure.

The manager should see fresh recommendations without having to prompt a chatbot.

## C. Agent Registry

Agent Registry must be truthfully verified.

The runner now has read-only Agent Registry permission.

Verify at minimum:

- the registered `Next Shift` agent;
- the registered `next-shift-runtime` service;
- Agent Runtime reference;
- managed runtime identity where exposed.

Do not create fake registry entries.

## D. Observability / OpenTelemetry

Retry real OpenTelemetry export using Google current guidance.

Explicitly verify:

- quota project = next-shift-506004;
- service account has roles/serviceusage.serviceUsageConsumer;
- runtime identity has roles/telemetry.writer or the minimum trace writer role;
- OTLP endpoint is configured correctly;
- exported traces can actually be read back.

The runner now has Cloud Trace read access.

If direct Google telemetry ingestion still returns a platform/organization PERMISSION_DENIED after the above exact configuration is verified, document the failed live proof precisely and do not leave broken exporters deployed.

A persistent externally imposed telemetry restriction alone does NOT block this mission if:

- real Cloud Run trace/span identifiers remain visible;
- the governed lifecycle correlation remains truthful;
- Agent Registry is verified;
- Active Operational Improvement Advisor is genuinely working;
- the external telemetry restriction is documented without exaggeration.

## E. Final proof

Demonstrate at least one real AI-generated operational recommendation derived from historical synthetic data.

The recommendation must include evidence and provenance and must be visible through the deployed product.

Run tests, live acceptance and readiness.

Evidence file:

docs/autonomy/evidence/10-registry-memory-otel.md

Finish with PHASE_RESULT: PASS only if the active operational-intelligence requirement is truly satisfied.
