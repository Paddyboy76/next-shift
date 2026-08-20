# Next Shift — Canonical Project Truth

**Status:** Active hackathon build  
**Canonical repository:** `Paddyboy76/next-shift`  
**Google Cloud project:** `next-shift-506004`  
**Google Cloud project number:** `963749706976`  
**Primary region:** `asia-southeast1` (Singapore)  
**Last verified baseline:** commit `35eeba8071b45bf5a4998284d47b7f0e958361d9` — `Harden async workflow with idempotency and dead-letter handling`  
**Last verified date:** 2026-08-20

This file is the **single source of truth for all future ChatGPT, Codex, and human development sessions** on Next Shift. Read it before making architectural changes. When project reality changes, update this file in the same PR/commit as the change whenever practical.

---

## 1. Project mission

Next Shift is being built for the **Fortified Enterprise Fleet** track of Google’s **All Things Agentic Hackathon**.

The product concept is a non-clinical autonomous operations fleet for 24/7 environments, initially demonstrated in a hospital setting. It takes messy shift-handover inputs such as voice notes, emails, PDFs, images, and unresolved requests; extracts concrete operational issues; routes them to least-privilege specialist agents; maintains durable state across shifts; and verifies that actions were actually completed rather than merely discussed.

The core product statement is:

> **Next Shift does not summarize the handover. It finishes the operational work left behind by it.**

The first vertical is hospital operations because the problem is concrete, multi-departmental, asynchronous, and easy for judges to understand. The architecture should remain vendor-neutral enough to generalize later to hotels, factories, airports, logistics, care homes, and other 24/7 operations.

---

## 2. Hard boundaries and non-negotiables

1. **No BDMS/Bangkok Hospital branding, data, code, internal systems, screenshots, identifiers, or proprietary workflows.** The project is Hallermann Consulting-owned and must remain independent.
2. **Synthetic data only** for development, demos, tests, screenshots, videos, and public material.
3. **Non-clinical operations only.** Next Shift must not diagnose, recommend treatment, alter medication, make clinical triage decisions, or present itself as clinical decision support.
4. **Firestore is authoritative workflow truth.** The model may reason, recommend, or remember context, but it must not be treated as the source of truth for operational completion.
5. **No agent gets broad permissions merely because it is convenient.** Capabilities are role-scoped and least-privilege.
6. **An agent does not receive credit for saying it did something.** State-changing claims require externally verifiable evidence or trusted tool output.
7. **No silent failure.** Invalid actions must be rejected, surfaced, retried safely when appropriate, or routed to human review/dead-letter handling.
8. **No giant files / god modules.** Review Python files around 200 lines for mixed responsibilities; refactor before ~300 lines unless there is a strong reason not to.
9. **Do not weaken deterministic workflow rules to make an LLM test pass.** Fix the tool contract, permission boundary, orchestration, or evidence flow instead.
10. **Prefer full-file replacements for Python changes when editing interactively.** Avoid fragile mid-function copy/paste patches that can break indentation or imports.

---

## 3. Hackathon strategy

### Target

Primary target: **Grand Prize**.  
Track: **Fortified Enterprise Fleet**.

The architecture should naturally demonstrate the track requirements rather than bolt them on for judging:

- specialized institutional agents
- long-running asynchronous execution
- persistent cross-session context
- agent discovery/lifecycle
- least-privilege identity and authorization
- gateway/policy enforcement
- prompt-injection and data-leak protection
- end-to-end observability

### Demo thesis

The winning demo should visibly prove action, not just produce prose.

Ideal four-minute story:

1. ingest messy synthetic handover material
2. create several operational issues
3. autonomously route issues to specialist agents
4. show real state changes in Firestore
5. show asynchronous processing across an artificial shift boundary
6. show one hostile/prompt-injection attempt blocked
7. show one unauthorized data access denied
8. show a verifier refuse to close an issue without evidence
9. advance time / next shift and show unresolved work resume from durable state
10. finish with live Agent Platform / observability proof

### Discovery work

A Google Deep Research investigation has been requested to validate real hospital operational pain points and refine the agent mix. Its findings must be reviewed before locking the final demo workflow.

A structured discovery conversation with a senior nursing director is planned to validate real pain points, especially:

- what is routinely lost between shifts
- what nurses/managers spend time chasing
- which unresolved tasks cross departments
- what appears complete but later proves incomplete
- what repeatedly escalates
- which activities are suitable for autonomous coordination
- where human approval must remain mandatory
- which operational failures matter most to frontline staff and nursing leadership

Do not ask for confidential employer information, proprietary workflows, or patient data.

---

## 4. Current technology stack

### Core

- **Python 3.12**
- **Google ADK** for agent development
- **Gemini 3.5 Flash** through Vertex AI
- **Gemini Enterprise Agent Platform / Agent Runtime**
- **Firestore Native mode** for deterministic operational state
- **Pub/Sub** for asynchronous event routing
- **Cloud Storage** for deployment staging
- **Google Cloud IAM / Agent Identity** for least-privilege identities
- later: **Memory Bank**, **Agent Gateway**, **Model Armor**, **Agent Registry**, **Agent Observability/OpenTelemetry**
- secondary Google model planned: **Gemma** for constrained independent verification/security work if it materially improves the system

### Repository / development

- GitHub repository: `Paddyboy76/next-shift`
- default branch: `main`
- Cloud Shell used for current development
- Google Cloud billing attached
- budget alert: **THB 500/month**
- development policy: free tier first, hackathon credit second, real spend last

The THB 500 budget is a monitoring/alert mechanism, not an assumption that Google Cloud will enforce a hard shutdown at THB 500.

Hackathon Google Cloud credit request: **USD 150 requested; approval/status must be verified before assuming it is available.**

---

## 5. Google Cloud resources

### Project

- project ID: `next-shift-506004`
- project number: `963749706976`
- billing account used during setup: `0153B7-79FA06-D6A9AA`

### Agent Runtime

First deployed Agent Runtime resource:

`projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048`

Display name: `Next Shift`

Verified properties from successful deployment/testing:

- region: `asia-southeast1`
- framework: Google ADK
- Python 3.12 package
- managed Agent Identity enabled
- telemetry enabled
- remote `async_stream_query` works
- Gemini 3.5 Flash remote invocation verified
- runtime exposes managed session/memory-related methods

### Storage

Deployment staging bucket:

`gs://next-shift-506004-agent-staging`

Current bucket location is `US` multi-region. This was sufficient for deployment, but regional alignment should be revisited before claiming a strict data-residency architecture.

### Firestore

Database:

`projects/next-shift-506004/databases/(default)`

Properties:

- type: `FIRESTORE_NATIVE`
- edition: Standard
- location: `asia-southeast1`
- free tier: enabled at creation
- delete protection: enabled
- realtime updates: enabled

### Pub/Sub

Primary topic:

`projects/next-shift-506004/topics/next-shift-handover-received`

Current worker/test subscription:

`projects/next-shift-506004/subscriptions/next-shift-handover-received-test`

Dead-letter topic:

`projects/next-shift-506004/topics/next-shift-dead-letter`

Dead-letter review subscription:

`next-shift-dead-letter-review`

Current retry/dead-letter policy:

- max delivery attempts: **5**
- minimum retry backoff: **10s**
- maximum retry backoff: **60s**
- invalid event was experimentally confirmed to reach the DLQ after 5 failed deliveries

---

## 6. Current proven architecture

The currently working path is:

```text
Synthetic handover input
        ↓
Next Shift intake agent
        ↓
create_handover_issue tool
        ↓
workflow layer
        ↓
Firestore issue persisted as RECEIVED
        ↓
versioned Pub/Sub event emitted
        ↓
Facilities worker receives event asynchronously
        ↓
worker validates contract + idempotency + ownership + current state
        ↓
Facilities workflow performs RECEIVED → TRIAGED
        ↓
processed event recorded
        ↓
Pub/Sub message ACKed
```

This has been tested end-to-end successfully.

The implementation deliberately separates:

- **LLM reasoning**
- **agent/tool permissions**
- **business workflow rules**
- **persistence**
- **event contracts**
- **event transport**
- **worker processing**

Do not collapse these layers back together for convenience.

---

## 7. Workflow state machine

Canonical states:

```text
RECEIVED
TRIAGED
ASSIGNED
ACTION_PENDING
VERIFYING
CLOSED
BLOCKED
HUMAN_REVIEW
FAILED
```

Canonical transitions:

```text
RECEIVED
  → TRIAGED
  → HUMAN_REVIEW
  → FAILED

TRIAGED
  → ASSIGNED
  → HUMAN_REVIEW
  → FAILED

ASSIGNED
  → ACTION_PENDING
  → BLOCKED
  → HUMAN_REVIEW
  → FAILED

ACTION_PENDING
  → VERIFYING
  → BLOCKED
  → HUMAN_REVIEW
  → FAILED

VERIFYING
  → CLOSED
  → ACTION_PENDING
  → BLOCKED
  → HUMAN_REVIEW
  → FAILED

BLOCKED
  → ASSIGNED
  → ACTION_PENDING
  → HUMAN_REVIEW
  → FAILED

HUMAN_REVIEW
  → ASSIGNED
  → ACTION_PENDING
  → FAILED

CLOSED
  → terminal

FAILED
  → terminal
```

Rules:

- do not skip states unless the canonical state machine is intentionally changed
- do not invent statuses such as `ESCALATED`, `COMPLETE`, `RESOLVED`, or `IN_PROGRESS`
- invalid transitions return structured rejections at tool boundaries where possible rather than crashing the whole agent process
- closure must eventually belong to a verifier/evidence flow, not the operational specialist that performed the work

---

## 8. Agent roles and authority model

### `next_shift` — intake agent

Current authority:

- can create a handover issue
- can read a handover issue
- cannot change workflow state
- cannot claim downstream work occurred
- should identify an obvious operational owner during intake

This boundary was introduced after testing showed Gemini would otherwise continue from an empty ADK CLI turn and opportunistically advance workflow state. Removing the transition tool from intake solved the problem at the capability layer rather than through prompt pleading.

### `facilities_agent` — specialist

Current intended authority:

- reads Facilities-owned issues
- can perform Facilities-specific workflow progression where evidence/rules allow
- currently proven first action: `RECEIVED → TRIAGED`
- cannot close issues merely because Facilities was contacted or expected to act

### `facilities_worker`

Current asynchronous worker responsibility:

- receive Pub/Sub message
- decode JSON
- validate event contract/version
- check idempotency
- read authoritative issue state
- reject/skip non-Facilities or non-RECEIVED work where appropriate
- perform deterministic first Facilities workflow action
- record processed-event outcome
- ACK success/duplicate/intentional skip
- NACK processing failures so Pub/Sub retry/DLQ policy applies

### Planned roles

Likely future roles, subject to research validation:

- dispatcher / routing agent
- logistics or mobility agent
- guest-services/interpreter agent
- facilities agent
- closure sentinel / follow-up agent
- independent verifier

Do not create agents merely to increase the agent count. Each agent must have a distinct institutional responsibility, permission boundary, and reason to exist.

---

## 9. Event contract and reliability baseline

Current event:

- type: `handover.issue.received`
- version: `1.0`

Required payload fields:

```text
event_id
event_type
event_version
occurred_at
issue_id
owner
state
source_type
source_reference
```

Safe routing metadata is published; do not place unnecessary sensitive or full clinical content into routing events.

Current reliability controls:

- UUID event IDs
- explicit event type/version
- contract validation
- processed-event records in Firestore
- duplicate event detection
- deterministic current-state check before mutation
- ACK only after successful/intentional handling
- NACK on processing failures
- exponential retry policy
- dead-letter forwarding after bounded retries

Acceptance proof completed:

1. valid issue created as `RECEIVED`
2. Pub/Sub worker autonomously moved it to `TRIAGED`
3. processed-event record existed
4. exact duplicate event was republished
5. duplicate was ACKed without changing state
6. intentionally invalid event version `999.0` was NACKed repeatedly
7. Pub/Sub delivered it 5 times
8. message then appeared successfully on the dead-letter review subscription with dead-letter source delivery count `5`

---

## 10. Repository structure

Current modular direction:

```text
next-shift/
├── AGENTS.md
├── acceptance_async.py
├── deploy_agent.py
├── facilities_worker.py          # thin compatibility/entry wrapper
├── test_firestore.py
│
├── facilities/
│   ├── __init__.py
│   └── agent.py
│
├── next_shift/
│   ├── __init__.py
│   ├── agent.py
│   ├── facilities_agent.py
│   ├── handover_store.py         # compatibility shim
│   ├── tools.py
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   └── states.py
│   │
│   ├── events/
│   │   ├── __init__.py
│   │   ├── contracts.py
│   │   └── publisher.py
│   │
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── firestore.py
│   │   └── processed_events.py
│   │
│   └── workflows/
│       ├── __init__.py
│       └── handover.py
│
└── workers/
    ├── __init__.py
    └── facilities_worker.py
```

At the latest measured refactor checkpoint, the largest production module was approximately 146 lines. Maintain this modularity as the system grows.

Separation of concerns:

- `domain/` — canonical domain rules/types
- `persistence/` — storage implementation only
- `events/` — event schema + publication
- `workflows/` — business transitions/orchestration
- `tools.py` — thin ADK-facing tool adapters
- `agent.py` / specialist agent files — agent policy/instructions/capabilities
- `workers/` — event consumers and transport lifecycle

---

## 11. Known working Git history

Verified milestones:

- `888a949531ece5b2c5f66965adf106648f0a7c0a` — Initialize Next Shift ADK agent
- `9d38f658bacd83a1c29d241d91a9392435f833f0` — Deploy Next Shift baseline to Agent Runtime
- `821cb318804624ad6c91ce85b9db5b2f54280388` — Add durable handover workflow and facilities agent
- `5e06fc3fcdf386ed9ac07fb1cd04ef27c1630c28` — Add asynchronous facilities routing with Pub/Sub
- `35eeba8071b45bf5a4998284d47b7f0e958361d9` — Harden async workflow with idempotency and dead-letter handling

When starting a new session, verify current `origin/main` rather than assuming this SHA is still latest.

---

## 12. Critical setup/deployment lessons already learned

### Vertex AI backend

Local ADK initially tried to use the Gemini Developer API and failed because no API key was supplied. The working Cloud/Vertex environment is:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=next-shift-506004
export GOOGLE_CLOUD_LOCATION=asia-southeast1
```

ADC must be valid:

```bash
gcloud auth application-default print-access-token >/dev/null && echo ADC_OK
```

### Agent Runtime region

The first deployment repeatedly failed with generic code 13 while `LOCATION="global"` was used. Changing the runtime deployment location to:

```text
asia-southeast1
```

produced the first successful Agent Runtime deployment. Do not revert Runtime deployment to `global` without verifying current platform support.

### Service identities / staging bucket

During setup, the following identities were relevant:

- `service-963749706976@gcp-sa-aiplatform.iam.gserviceaccount.com`
- `service-963749706976@gcp-sa-aiplatform-re.iam.gserviceaccount.com`

The Reasoning Engine service agent holds `roles/aiplatform.reasoningEngineServiceAgent`.

Staging-bucket IAM was explicitly granted during troubleshooting. Verify before changing/removing it.

### ADK Web

`adk web` through Cloud Shell Web Preview produced a blank/black UI with `/dev-ui/` 403 responses. `adk run` worked and was used for local behavioral testing. Do not spend project time fighting the web dev UI unless needed.

### ADK CLI behavior

During interactive `adk run`, apparent empty user turns sometimes caused the agent to continue acting. This exposed an important architectural principle: **do not rely on prompts to prevent unauthorized state mutation. Remove the capability/tool from agents that must not perform that action.**

### Deprecated client warning

Current deployment/test code may emit a warning that `vertexai.Client` is deprecated in favor of `agentplatform.Client`. This warning did not prevent successful deployment. Migration should be done intentionally and tested, not mixed into unrelated feature work.

---

## 13. Development and quality rules

### Before editing

Always verify:

```bash
cd ~/next-shift
source .venv/bin/activate
pwd
git status
git log -3 --oneline
```

For Google commands, prefer explicit project scoping:

```bash
--project=next-shift-506004
```

Cloud Shell configurations can reset between sessions.

### Code changes

- make one architectural change at a time
- syntax-check full changed Python modules before runtime testing
- prefer full-file edits over fragile partial indentation-sensitive edits
- maintain compatibility shims only when they simplify migration; do not let them become second implementations
- keep agents thin
- keep persistence unaware of agent-specific business policy
- keep workflow rules deterministic
- keep event contracts versioned

### Tests

Current useful tests/scripts:

- `test_firestore.py`
- `acceptance_async.py`
- direct local ADK agent test with `adk run next_shift`
- direct specialist test with `adk run facilities`

Do not replace focused verification with huge undirected test runs.

### Git

- branch: `main`
- keep working tree clean at milestones
- never commit `.venv`, `.env`, `.adk/session.db`, credentials, generated Python caches, or secrets
- `.adk/` runtime state must remain ignored
- commit known-good architecture milestones frequently

---

## 14. Security architecture direction

The intended enterprise story is least privilege plus verifiable enforcement.

Future security demonstrations should include:

1. an untrusted uploaded document/email containing prompt injection
2. Model Armor blocking or sanitizing the hostile instruction
3. an agent attempting a resource it does not have permission to access
4. Agent Identity / IAM / Gateway visibly denying that request
5. audit/trace evidence showing the denied action

Do not make unverified claims about Thai PDPA, GDPR, or regional data sovereignty. Synthetic data avoids the need to claim this prototype is currently production-compliant. Document what a real deployment would still require.

---

## 15. Memory vs operational truth

This distinction is fundamental.

### Firestore

Use for deterministic facts such as:

- issue ID
- owner
- workflow state
- action record
- verification status
- timestamps
- evidence references
- processed event IDs

### Memory Bank

Use later for longer-lived context such as:

- recurring operational patterns
- user/workflow preferences
- context from earlier shifts
- prior issue history useful to agent reasoning

Memory must never silently overwrite authoritative operational state.

---

## 16. Cost discipline

Current budget alert: **THB 500/month**.

Rules:

1. use free tiers/allowances wherever practical
2. use hackathon credit when approved
3. avoid idle always-on infrastructure where serverless/event-driven alternatives exist
4. do not enable services merely because they might be useful later
5. inspect billing before introducing high-volume Gemini calls or persistent services
6. demo/test with tiny synthetic workloads

---

## 17. Immediate next milestones

Unless research materially changes the product direction, the recommended order is:

### Foundation completion

1. verify current main + clean working tree
2. migrate deprecated client only if current Agent Platform SDK path is clear and tested
3. add automated tests around state transitions, event contracts, idempotency, and worker routing
4. rename `*-test` Pub/Sub resources when moving from prototype to stable demo infrastructure
5. introduce structured logging/trace correlation IDs

### Fleet expansion

6. create explicit dispatcher/routing contract
7. add second specialist only after its pain point is validated by research/interview
8. add verifier as a distinct authority boundary
9. add evidence objects so `VERIFYING → CLOSED` is proof-driven
10. add closure/follow-up sentinel for cross-shift continuation

### Enterprise platform features

11. integrate Memory Bank intentionally
12. integrate Agent Registry / lifecycle
13. integrate Agent Gateway
14. integrate Model Armor
15. expand Agent Identity/IAM policies per specialist
16. add OpenTelemetry / Agent Observability traces suitable for the demo

### Product/demo layer

17. multimodal handover intake
18. compact operations UI showing issues, owners, states, evidence, and agent activity
19. simulated time advance / next-shift continuation
20. attack/permission-denial demo
21. final 4-minute demo script
22. reproducible README/setup instructions
23. architecture diagram
24. public build article and qualifying social post for hackathon bonus points

---

## 18. Session startup protocol for ChatGPT / Codex / other agents

At the beginning of any future development session:

1. **Read this file completely.**
2. Inspect current repository state rather than assuming this document’s last SHA is still current.
3. Run/obtain:

```bash
cd ~/next-shift
source .venv/bin/activate
git status
git branch --show-current
git log -5 --oneline
git fetch origin
git status -sb
```

4. Verify Google project before Cloud mutations:

```bash
gcloud config get-value project
gcloud billing projects describe next-shift-506004
```

5. Never guess paths, resource IDs, current state, or deployed versions when they can be inspected.
6. Preserve the architecture boundaries in this document unless there is a concrete reason to change them.
7. If a new requirement conflicts with this document, call out the conflict explicitly before changing code.
8. After a material architecture/resource change, update this document so future sessions inherit the new truth.

---

## 19. What success looks like

A strong final Next Shift build is not a collection of chatbots.

It is a visible, event-driven enterprise system where:

- messy handover input becomes structured operational work
- agents delegate based on institutional responsibility
- permissions prevent an agent from doing work outside its role
- durable state survives sessions and shifts
- async events wake the right specialist without a human babysitter
- duplicate events do not duplicate work
- poisoned events retry safely and land in a DLQ
- work is not closed without evidence
- security failures are visible and auditable
- judges can watch real state change live on Google Cloud

The defining engineering principle is:

> **No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable.**
