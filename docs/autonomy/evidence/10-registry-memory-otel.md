# Mission 10 — Registry + Memory + OpenTelemetry evidence

## What was inspected

- Read `AGENTS.md` completely before architectural changes.
- Verified the controller branch remained `codex/autonomous-final-attack` at `124ce42bd2785d14d4369ffabec11f3c38706e3e`; the controller-owned `docs/autonomy/STATUS.md` change was the only initial working-tree modification.
- Verified active project `next-shift-506004`, enabled Agent Registry, Vertex AI, Telemetry, Cloud Logging, Cloud Monitoring and Cloud Trace APIs, all Cloud Run services, the deployed Agent Runtime and recent Cloud Run request trace/span fields.
- Read the live Agent Runtime resource `projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048`. It is a Google ADK Python 3.12 deployment with `identityType=AGENT_IDENTITY`, a managed effective identity, Agent Gateway binding, and managed memory methods.
- Inspected official current Google Cloud documentation for Agent Registry automatic/manual registration, Agent Engine Memory Bank, ADK/OpenTelemetry instrumentation and the recommended OTLP Telemetry API migration path.

## What changed

- Added a focused `next-shift-memory-sync` Cloud Run service. It runs as the existing `ns-operations-ui` read-only operational identity, reads historical synthetic `handover_issues`, creates advisory Memory Bank facts, and exposes a read-only intelligence response.
- Created real Agent Engine Memory Bank memories scoped to `context=next-shift-operational-intelligence`. The latest verified resource is `projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048/memories/8354296605783883776`.
- Added a judge-visible historical-intelligence panel and platform-lifecycle panel to Operations Control. The intelligence contract explicitly reports `authority=ADVISORY_ONLY`, `current_state_authority=Firestore handover_issues`, `may_mutate_workflow=false`, source collection, synthetic-only provenance, sample size, managed memory resource and scope.
- Added meaningful trend analysis for owner volume, mean closure timing, repeated locations and plain-English recommendations, plus a regression proving the analysis does not mutate input workflow state.
- Granted `ns-operations-ui` only the additional `roles/aiplatform.user` permission required to create/list its managed Memory Bank entries. Temporary runner permissions used for diagnosis were removed.
- Deployed `next-shift-memory-sync-00003-f94` and `next-shift-operations-00019-5jz`, each serving 100% latest traffic.

## Live Memory Bank evidence

The deployed sync read 46 authoritative synthetic Firestore issues and produced a managed Memory Bank fact with these inspected results:

- Facilities represented 15 of 46 historical issues.
- Facilities had the highest observed mean closure time at 40.3 minutes.
- Discharge Lounge was the most repeated location with 6 issues.
- Recommendations were persisted as advisory text alongside the explicit statement that Firestore remains authoritative for current issue state.
- A subsequent managed-memory list returned both created Memory Bank resources with their facts, create times and exact advisory scope.

## Registry evaluation

- `agentregistry.googleapis.com` is enabled.
- Current Google documentation states that supported Agent Runtime deployments are automatically registered.
- Direct `gcloud agent-registry services list` and `agents list` verification is blocked for the autonomous runner by `agentregistry.services.list` and `agentregistry.agents.list` denials.
- Temporarily granting the documented `roles/agentregistry.admin` role did not change the service-side denial; the temporary grant was removed.
- No local or fake registry was built. The UI truthfully reports that Agent Runtime supports automatic registration and that runner-side registry verification is blocked; it does not claim an inspected registry entry.

## Observability / OpenTelemetry evaluation

- Real Cloud Run request records already contain Google Cloud trace and span identifiers, and the existing governed lifecycle view correlates durable Firestore intake, event, specialist, action, evidence, verifier and closure records without pretending they are one distributed trace.
- Implemented and deployed OpenTelemetry Flask/Requests instrumentation first with the Google Cloud Trace exporter and then with Google's currently recommended OTLP gRPC exporter to `telemetry.googleapis.com:443`, using ADC, `gcp.project_id`, scoped credentials and the documented writer roles.
- Both real export attempts failed with platform `PERMISSION_DENIED`: legacy export denied `cloudtrace.traces.patch`; OTLP export returned `StatusCode.PERMISSION_DENIED` despite `roles/telemetry.tracesWriter` / `roles/telemetry.writer` and Service Usage permissions.
- The nonfunctional exporter was removed and the final Operations revision was redeployed so production is not left emitting exporter errors. No telemetry was fabricated.

## Deliberately not changed

- Firestore workflow state, state transitions, evidence rules, independent verifier ownership and least-privilege mutation boundaries were not changed.
- Memory does not establish current state and cannot mutate operational work.
- No fake registry, fake telemetry, local registry substitute or presentation-only trace was introduced.
- The branch was not changed and no commit, push, merge or pull request was performed.

## Exact validation performed

- `python -m pytest -q`: `120 passed, 49 subtests passed`.
- `python -m compileall -q next_shift services workers tests`: passed.
- `git diff --check`: passed.
- Real Memory Bank create and list against the deployed Agent Engine: succeeded; latest memory resource recorded above.
- Authenticated `GET /v1/intelligence` against deployed `next-shift-memory-sync`: returned `ADVISORY_ONLY`, `sample_size=46`, `memory_bank.status=SYNCED`, exact memory resource/scope and Firestore provenance.
- Cloud Run inspection: memory sync revision `00003-f94` and Operations revision `00019-5jz` are ready and receive 100% traffic under `ns-operations-ui`.
- `verify_readiness.sh`: `PASS=169 WARN=0 FAIL=2`. Both failures are controller-required Git conditions (the mandated non-main controller branch and expected uncommitted phase changes). All cloud architecture, Firestore sole-writer/viewer, invoker isolation, Pub/Sub, runtime identity, gateway and Model Armor checks passed.

## Remaining risks / blocker

- Agent Registry contents cannot be authoritatively inspected with the available runner identity even after the documented project role is granted.
- Native OpenTelemetry export cannot be verified because both supported Google ingestion paths reject writes at a platform/organization boundary even with the documented roles.
- These are material Mission 10 requirements. The Memory Bank and judge-visible lifecycle improvements are deployed and verified, but the phase cannot truthfully be declared complete until an identity/platform administrator resolves Registry read access and Telemetry API ingestion, followed by real registry and trace inspection.

PHASE_RESULT: BLOCKED
