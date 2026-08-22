# Next Shift — hackathon submission copy

## One-line pitch

Next Shift is a fortified autonomous operations fleet that turns messy shift handovers into durable work and refuses to close anything until trusted evidence and an independent verifier prove it is actually done.

## Short description

Next Shift converts an unstructured handover into multiple persistent operational jobs, routes each job to a least-privilege specialist, coordinates frontline action through Google Chat, and keeps Firestore as the authoritative source of workflow truth. Specialists and humans can progress or claim completion, but only trusted evidence plus an independent verifier can close work.

The demo uses synthetic non-clinical hospital operations, but the architecture is designed for any 24/7 enterprise where work crosses shifts.

## What makes it agentic

The Agent Runtime does more than answer questions. It interprets one messy handover, decomposes it into independent operational proposals, and initiates a fleet of asynchronous specialist workflows.

The system then continues operating without requiring the original user to remain in the loop:

- durable work persists across shifts
- owner-filtered Pub/Sub wakes the correct specialist
- specialists resume deterministic workflows
- Human Reach coordinates real-world action asynchronously
- evidence arrives independently of the specialist
- a separate verifier controls final closure

## What makes it fortified

Next Shift treats every model, specialist and human claim as untrusted until it crosses an explicit authority boundary.

Production controls include:

- managed Agent Identity
- Agent Gateway on the client-to-agent path
- Model Armor content authorization
- IAP-protected Operations Control
- one State Authority as the Firestore mutation choke point
- dedicated specialist Cloud Run identities
- dedicated OIDC Pub/Sub push identities and audiences
- owner-filtered production subscriptions
- deterministic principal/capability/owner/state authorization
- bounded retry and dead-letter handling
- idempotent duplicate processing
- trusted evidence identities
- independent verifier identity
- stale Human Reach rejection with structured security audit events

A final read-only production verifier reports:

`PASS=159 WARN=0 FAIL=0 — NEXT_SHIFT_READINESS=PASS`

## The defining product moment

A frontline worker clicks **Completed** in Google Chat.

Next Shift does not close the issue.

The system records the action as `CLAIMED · UNVERIFIED`. A trusted evidence service must independently record proof. That moves work to `VERIFYING`. Only a separate verifier can request the final transition to `CLOSED · VERIFIED`.

This makes the core principle visible:

> No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned and verifiable.

## Production acceptance highlights

The deployed system has demonstrated:

- one handover producing six independent operational jobs
- exact routing to Facilities, AssetLogistics, LanguageAccess, DischargeDME, EVSThroughput and PatientTransport
- Google Chat delivery to two durable operational spaces
- duplicate events ACKed without duplicate state mutation
- malformed events retried five times then delivered to the DLQ
- trusted evidence moving work to `VERIFYING`
- independent verifier closure
- prohibited clinical requests refused without durable work creation
- stale Google Chat completion rejected after authoritative closure
- structured authorization DENY audit proof
- full lifecycle trace from intake to `CLOSED · VERIFIED`

## Google Cloud services used

- Vertex AI Agent Runtime / ADK
- managed Agent Identity
- Agent Gateway
- Model Armor
- Cloud Run
- Pub/Sub
- Firestore
- Google Chat
- Cloud Logging / request tracing
- IAP
- IAM

## Safety and scope

The demo is synthetic and non-clinical. Next Shift does not diagnose, prescribe, perform clinical triage, interpret clinical measurements for treatment decisions, or delegate licensed clinical work.

No Bangkok Hospital / BDMS data, branding, screenshots, identifiers, internal systems or proprietary workflows are used.

## Suggested submission title

**Next Shift — A Fortified Autonomous Operations Fleet for Work That Survives the Handover**

## Suggested tagline

**The handover ends. The work does not.**

## Suggested final paragraph

Next Shift demonstrates a pattern for enterprise agents that is intentionally stricter than “the agent said it succeeded.” Reasoning is separated from authority, frontline coordination is separated from proof, and completion is separated from verification. The result is an autonomous system that can keep work moving across shifts while remaining inspectable, least-privilege and evidence-backed.
