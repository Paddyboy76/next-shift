# Next Shift — Canonical Project Truth


**Status:** Active hackathon build — operational fleet complete; fortified product phase underway  
**Canonical repository:** `Paddyboy76/next-shift`  
**Google Cloud project:** `next-shift-506004`  
**Google Cloud project number:** `963749706976`  
**Primary region:** `asia-southeast1` (Singapore)  
**Last verified baseline:** commit `317e7e4d5f73d77418508dd2a94cf6f654631d7b` — `Add closed-loop Facilities coordination`  
**Last verified date:** 2026-08-20


This file is the canonical project truth for future ChatGPT, Codex, and human development sessions.


Read it completely before making architectural changes.


Repository state and live Google Cloud state are authoritative if either differs from this document.


---


## 1. Mission


Next Shift is being built for Google's **All Things Agentic Hackathon**, targeting the **Fortified Enterprise Fleet** track and the Grand Prize.


Next Shift is a non-clinical autonomous operations fleet for 24/7 environments, initially demonstrated in a synthetic hospital setting.


Core statement:


> **Next Shift does not summarize the handover. It finishes the operational work left behind by it.**


The system converts messy handover information into durable operational work, routes that work to least-privilege specialists, maintains state across shifts, performs asynchronous actions, gathers trusted evidence, and independently verifies completion.


---


## 2. Hard boundaries


These are non-negotiable.


1. Synthetic data only.
2. No Bangkok Hospital / BDMS data, branding, screenshots, code, identifiers, internal systems, or proprietary workflows.
3. Non-clinical operations only.
4. No diagnosis.
5. No prescribing or medication changes.
6. No clinical triage or acuity decisions.
7. No interpretation of clinical measurements for treatment decisions.
8. No delegation of licensed clinical work.
9. Firestore is authoritative operational truth.
10. Agent memory must never replace Firestore workflow state.
11. Agents cannot claim completion without trusted evidence.
12. Operational specialists do not close their own work.
13. Invalid or unauthorized actions must fail visibly.
14. Least privilege must be technically enforced rather than entrusted only to prompts.
15. Keep code modular; avoid god modules.


---


## 3. Current product architecture


The proven architecture is:


```text
messy synthetic handover
        ↓
Next Shift ADK intake
        ↓
multiple structured operational issues
        ↓
Firestore authoritative state
        ↓
versioned Pub/Sub event
        ↓
owner routing metadata
        ↓
filtered specialist subscription
        ↓
least-privilege specialist worker
        ↓
resumable deterministic workflow
        ↓
operational action
        ↓
trusted external/synthetic evidence
        ↓
VERIFYING
        ↓
independent verifier
        ↓
CLOSED

The system also supports:

multi-issue handover decomposition
deterministic owner routing
versioned event contracts
filtered specialist Pub/Sub subscriptions
asynchronous processing
idempotent event handling
retry handling
dead-letter queue
persistent workflow history
resumable specialist workflows
trusted evidence
independent verification
cross-shift continuity snapshots
rejection of prohibited clinical requests
4. Canonical workflow state machine

Canonical states:

RECEIVED
TRIAGED
ASSIGNED
ACTION_PENDING
VERIFYING
CLOSED
BLOCKED
HUMAN_REVIEW
FAILED

Normal successful path:

RECEIVED
→ TRIAGED
→ ASSIGNED
→ ACTION_PENDING
→ VERIFYING
→ CLOSED

Rules:

do not invent alternative status names
do not silently skip state transitions
workflow mutation must obey deterministic state rules
operational specialists may progress work but must not self-certify closure
VERIFYING → CLOSED requires trusted evidence and independent verification
invalid transitions fail visibly
5. Operational fleet

The following operational specialists are implemented.

Facilities

Owner:

Facilities

Worker:

facilities_worker

Closed-loop workflow proven:

RECEIVED
→ TRIAGED
→ ASSIGNED
→ ACTION_PENDING
→ trusted maintenance evidence
→ VERIFYING
→ independent verifier
→ CLOSED

Synthetic example:

Leaking sink
Room 402
Asset Logistics

Owner:

AssetLogistics

Worker:

asset_logistics_worker

Closed-loop wheelchair / asset workflow proven.

Synthetic RTLS example:

WC-041
Floor 3 - Lift Lobby

Authority chain:

asset_logistics_worker
→ synthetic_rtls
→ independent_verifier
Language Access

Owner:

LanguageAccess

Worker:

language_access_worker

Closed-loop interpreter coordination proven.

Example:

Spanish interpreter
Room 402

Authority chain:

language_access_worker
→ synthetic_language_service
→ independent_verifier
Discharge DME

Owner:

DischargeDME

Worker:

discharge_dme_worker

Closed-loop durable medical equipment coordination proven.

Example equipment includes:

home_oxygen
hospital_bed
walker
wheelchair

Authority chain:

discharge_dme_worker
→ synthetic_dme_vendor
→ independent_verifier
EVS Throughput

Owner:

EVSThroughput

Worker:

evs_throughput_worker

Closed-loop room-turnaround coordination proven.

Supports:

EVS assignment
cleaning request
turnaround target
ACTION_PENDING
trusted cleaning-complete evidence
independent closure
Patient Transport

Owner:

PatientTransport

Worker:

patient_transport_worker

Closed-loop transport coordination proven.

Expected successful path:

transport request
→ transporter assignment
→ ACTION_PENDING
→ trusted arrival evidence
→ VERIFYING
→ independent verifier
→ CLOSED
6. Multi-issue handover intake

The intake agent can decompose one messy handover into several independent operational issues.

A synthetic handover has successfully produced separate work for:

AssetLogistics
LanguageAccess
DischargeDME
EVSThroughput
Facilities

PatientTransport is also implemented as an operational owner.

Each issue receives specialist-specific workflow_input.

The intake agent must not collapse several unrelated operational problems into one issue merely because they were mentioned in one handover.

7. Clinical safety boundary

Clinical requests are outside Next Shift authority.

A focused synthetic request such as:

prescribe 5 mg oxycodone for discharge

was correctly refused without creating an operational issue.

This boundary must remain technically and behaviorally visible.

Future security work should strengthen this with platform policy and prompt-injection defenses, but must not weaken the deterministic non-clinical boundary already present.

8. Cross-shift continuity

Cross-shift continuity is implemented.

A shift snapshot captures unresolved work while authoritative current state remains in Firestore.

Example:

Day Shift
→ Night Shift

A continuity snapshot records information including:

captured issue
owner
state at handover
current authoritative state
whether state changed
next action
still-open work
work resolved after handover

The incoming shift must read current Firestore state rather than trust a stale handover summary.

9. Evidence and independent verification

Evidence-backed closure is implemented.

Fundamental rule:

An operational agent's claim that work happened is not proof that it happened.

Trusted evidence sources are capability-specific synthetic integrations such as:

synthetic_rtls
synthetic_dme_vendor
synthetic_language_service

and equivalent trusted sources for the other implemented capabilities.

Operational specialists progress work to ACTION_PENDING.

Trusted evidence moves appropriate work toward VERIFYING.

The independent verifier validates the evidence and owns closure.

Specialists must not close their own issues.

10. Routing and worker isolation

Canonical operational owners:

Facilities
AssetLogistics
LanguageAccess
DischargeDME
EVSThroughput
PatientTransport

Canonical workers:

facilities_worker
asset_logistics_worker
language_access_worker
discharge_dme_worker
evs_throughput_worker
patient_transport_worker

Routing is deterministic.

next_shift/domain/routing.py owns the canonical mapping between operational owners and specialist workers.

Workers must reject work outside their authority.

Current specialist workflows also perform owner checks, but Phase 2 will centralize this into a reusable, auditable authorization layer.

11. Pub/Sub architecture

Shared handover topic:

next-shift-handover-received

Dead-letter topic:

next-shift-dead-letter

Known specialist subscriptions:

next-shift-facilities
next-shift-asset-logistics
next-shift-discharge-dme
next-shift-language-access
next-shift-evs-throughput
next-shift-patient-transport

Specialist subscriptions use owner attribute filters.

Known retry / DLQ configuration:

maximum delivery attempts: 5
minimum backoff: 10s
maximum backoff: 60s

Before modifying cloud resources, verify current live configuration.

12. Reliability guarantees

Implemented reliability controls include:

UUID event IDs
versioned event contracts
deterministic routing
current-state checks
persistent processed-event records
duplicate event detection
ACK only after successful or intentional handling
NACK on processing failure
bounded retry
dead-letter forwarding
resumable workflows

A duplicate event must not duplicate operational work.

A malformed or unsupported event must fail visibly and follow retry / DLQ policy.

13. Google Cloud project

Expected project:

next-shift-506004

Project number:

963749706976

Primary region:

asia-southeast1

Billing was verified enabled on 2026-08-20.

Always verify before mutation:

gcloud config get-value project
gcloud billing projects describe next-shift-506004
14. Agent Runtime

Previously verified Agent Runtime resource:

projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048

Previously verified properties include:

Google ADK deployment
Python 3.12 package
managed Agent Identity enabled
telemetry enabled
remote query execution working

Do not assume this runtime resource remains unchanged.

Verify before deployment or modification.

15. Firestore

Expected database:

projects/next-shift-506004/databases/(default)

Firestore is authoritative operational workflow truth.

Use it for facts such as:

issue ID
owner
state
workflow input
action records
evidence references
verification status
timestamps
history
processed event IDs
continuity state

LLM context or Memory Bank must not override these values.

16. Memory

Memory and operational truth are separate concepts.

Firestore

Use for deterministic operational truth.

Memory Bank

Potential future use:

recurring operational patterns
preferences
useful context from prior shifts
non-authoritative historical context

Memory Bank must never silently mutate or replace Firestore state.

Only integrate it when it materially improves the product.

17. Development philosophy

The preferred development cycle is:

build
→ syntax-check
→ real integration run
→ inspect authoritative state
→ commit
→ move on

Do not turn Next Shift into a test-count project.

Tests are appropriate where they protect important behavior such as:

workflow state integrity
event contracts
authorization boundaries
idempotency
retry behavior
evidence rules
independent verification
security regressions

Do not create dozens of trivial tests merely to increase coverage.

18. Editing conventions

Repository:

/home/patrick/next-shift

Virtual environment:

/home/patrick/next-shift/.venv

Before work:

cd /home/patrick/next-shift
source /home/patrick/next-shift/.venv/bin/activate


git status
git branch --show-current
git fetch origin
git status -sb
git log -12 --oneline

For substantive interactive Python edits:

nano /full/path/to/file.py

Prefer full-file replacements over fragile sed or indentation-sensitive patches.

Verify paths before use.

19. Git baseline

Current verified baseline:

317e7e4d5f73d77418508dd2a94cf6f654631d7b

Commit:

Add closed-loop Facilities coordination

At verification time:

main == origin/main

Recent fleet milestones:

317e7e4 Add closed-loop Facilities coordination
0717cb3 Add closed-loop patient transport coordination
4fd44f7 Add multi-issue operational handover intake
95eca64 Add durable cross-shift continuity
4743b40 Add closed-loop EVS throughput coordination
e3f1b62 Add closed-loop LanguageAccess coordination
4e646ca Add closed-loop DME discharge coordination
a503eee Add evidence-backed independent verification
b6cadef Make AssetLogistics workflow resumable
95a3f50 Bind specialist workers to filtered subscriptions
5ed1cad Add owner-aware Pub/Sub routing metadata
c43b22a Add AssetLogistics wheelchair workflow
fc0cda4 Integrate facilities worker with dispatcher routing
7a10497 Add deterministic operational routing contract
8642044 Add deterministic workflow regression tests

Never assume this remains the latest commit in a future session.

Verify origin/main.

20. Phase 2 — current objective

The operational-fleet phase is complete.

Current objective:

Security + UI + observability + deployment + final product polish

Priority order:

A. Shared authorization

Build reusable least-privilege enforcement.

Examples:

LanguageAccess attempts Facilities action
→ DENIED
→ auditable security record
Facilities attempts DME action
→ DENIED
→ auditable security record

Authorization must not rely solely on agent prompts.

Prefer enforcement at capability, workflow, tool, identity, IAM, and gateway boundaries.

B. Fortified Enterprise Fleet security

Integrate relevant Google platform capabilities where practical and real:

Agent Identity / IAM
Agent Gateway where appropriate
Model Armor
prompt-injection protection
unauthorized-resource denial
auditable security events

Do not bolt on features solely for presentation.

C. Operations UI

Build a usable Next Shift operations interface.

Minimum views:

handover intake
issue board
specialist owner
current state
next action
SLA/timing
evidence
verification state
history
blocked / human-review work
cross-shift continuity
incoming-shift snapshot

The interface should show what Next Shift actually did, not merely visualize logs.

D. Observability

Operators and judges should be able to trace:

handover
→ issue
→ event
→ route
→ specialist
→ action
→ evidence
→ verifier
→ closure

Use real Google Agent Platform / OpenTelemetry observability where practical.

Do not fabricate telemetry.

E. Persistent platform integration

Review deliberately:

Agent Runtime
Agent Identity
Memory Bank
Agent Registry / lifecycle
Agent Gateway
Model Armor
observability

Only integrate features that provide genuine architectural value.

F. Deployment

Build stable reproducible deployment.

Requirements:

no manually babysat background workers
event-driven/serverless specialists where practical
stable backend
stable frontend
reproducible configuration
minimal operating cost
synthetic data only
G. Full product acceptance

Run a deployed multi-issue handover containing several simultaneous operational problems.

Strong synthetic acceptance scenario:

missing wheelchair
patient transport
Spanish interpreter
home oxygen
EVS turnaround
leaking sink
prohibited medication request
unresolved work surviving shift change

The workflows must actually execute and persist outcomes.

H. Product polish

Only after the deployed product works:

UX polish
architecture diagram
README
deployment documentation
public explanation
hackathon submission
final demo/video

Do not optimize the video before the product.

21. Current security milestone

The immediate new engineering milestone is:

Shared, technically enforced, auditable least-privilege authorization across the specialist fleet.

Current workflows contain local owner checks.

The next implementation should centralize these rules without weakening the existing deterministic checks.

Desired behavior:

authorized specialist
→ action allowed
→ normal workflow continues
wrong specialist / capability
→ action denied
→ no operational state mutation
→ denial persisted as security evidence/audit record

Authorization failures must be inspectable later by operators and judges.

22. What success looks like

Next Shift must not become a collection of chatbots.

The finished product should visibly prove that:

messy handover input becomes structured work
several issues can emerge from one handover
each issue is routed to the correct specialist
specialists have constrained authority
unauthorized actions are denied
operational state survives shifts
async events wake the correct worker
duplicate events do not duplicate work
failures retry safely
poisoned events reach a DLQ
specialists cannot self-certify completion
trusted evidence is required
an independent verifier controls closure
clinical requests are blocked
security failures are auditable
operators can see the entire lifecycle
the system runs on a stable deployed Google Cloud architecture

The defining engineering principle remains:

No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable.
