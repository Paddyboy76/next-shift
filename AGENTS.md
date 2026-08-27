# Next Shift — Canonical Project Truth

**Status:** Final product hardening complete; submission freeze pending clean-main verification  
**Canonical repository:** `Paddyboy76/next-shift`  
**Google Cloud project:** `next-shift-506004`  
**Project number:** `963749706976`  
**Primary region:** `asia-southeast1`  
**Final accepted branch:** `final/visual-hierarchy-polish`  
**Latest accepted live proof date:** 2026-08-27

Read this file completely before changing architecture or deployment. Repository state and live Google Cloud state are authoritative if either differs from this document.

## Mission

Next Shift is a fortified operational handover and continuity system for 24/7 enterprises, demonstrated with fully synthetic, non-clinical hospital operations.

Core product line:

> **The handover ends. The work does not.**

Engineering principle:

> **No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable.**

Next Shift turns messy human handovers into durable work, routes each issue to a least-privilege specialist, continues that work asynchronously after the initiating interaction ends, coordinates frontline people through Google Chat, gathers trusted evidence, and permits only an independent verifier to close work.

## Non-negotiable boundaries

1. Synthetic data only.
2. No real hospital data, branding, screenshots, identifiers, internal systems, or proprietary workflows.
3. Non-clinical operations only.
4. No diagnosis, prescribing, medication changes, clinical triage, treatment interpretation, or delegation of licensed clinical work.
5. Firestore is authoritative current workflow truth.
6. Memory Bank is advisory only and must never replace current Firestore state.
7. Specialists and humans may claim completion but cannot certify it.
8. Trusted source-specific evidence is required before verification.
9. Independent Verifier alone may request `VERIFYING → CLOSED`.
10. State Authority is the sole Next Shift workflow mutation path and sole Firestore writer.
11. Least privilege must be technically enforced through identities, IAM, invoker boundaries, capabilities, and deterministic authorization.
12. Invalid, stale, or unauthorized actions must fail visibly and be auditable.
13. Keep modules focused; avoid god modules and presentation-only security.

## Canonical operational channels

The deployed fleet has six deterministic owners:

- `Facilities`
- `AssetLogistics`
- `LanguageAccess`
- `DischargeDME`
- `EVSThroughput`
- `PatientTransport`

The human does not need to know this schema. Gemini 3.5 normalizes ordinary handover language into one proposal per distinct unresolved job. Multiple jobs for the same owner remain separate. If a task clearly belongs to none of the six channels, it may be held for operator review rather than forced into the nearest owner.

## Canonical lifecycle

```text
RECEIVED
→ TRIAGED
→ ASSIGNED
→ ACTION_PENDING
→ VERIFYING
→ CLOSED
```

Visible governed outcomes also include `BLOCKED`, `HUMAN_REVIEW`, and `FAILED`.

Do not invent alternative canonical state names. Do not silently skip transitions.

## Current governed architecture

```text
messy typed or spoken handover
        ↓
Gemini 3.5 / managed ADK Agent Runtime
        ↓
typed proposals
        ↓
independent Gemini 3.5 Coverage Critic
        ↓
bounded dispatch / held review outcome
        ↓
State Authority
        ↓
Firestore authoritative truth
        ↓
owner-filtered Pub/Sub
        ↓
six least-privilege Cloud Run specialists
        ↓
ACTION_PENDING
        ↓
Human Reach / Google Chat
        ↓
completion claim remains unverified
        ↓
optional Facilities BEFORE/AFTER Gemini 3.5 visual support
        ↓
separate trusted source-specific evidence
        ↓
VERIFYING
        ↓
independent Evidence Inspector
        ↓
Independent Verifier
        ↓
CLOSED
```

The initiating user does not need to remain connected. Firestore persistence plus Pub/Sub-driven specialists continue work asynchronously.

## Gemini 3.5 usage

All judge-visible model paths are on `gemini-3.5-flash`:

- managed ADK intake agent;
- spoken-handover transcription;
- independent Coverage Critic;
- Facilities supporting photo comparison in Operations audit path;
- Facilities Google Chat photo comparison;
- Operational Improvement Advisor / Memory Bank recommendation generation.

The compact proof script must visibly report:

```text
MODEL_ASSERT all_demo_gemini_3_5=true
```

## Human Reach / Google Chat

Google Chat is a frontline coordination surface, not workflow authority.

A delivered work card can expose `Acknowledge`, `Blocked`, and `Completed` only while authoritative issue state is `ACTION_PENDING`.

`Completed` means `CLAIMED · UNVERIFIED`; it does not close the issue.

Human Reach re-reads State Authority before rendering current state. After evidence or verification, Operations refreshes the same Chat card. `VERIFYING` is shown as evidence received / independent verification running; `CLOSED` is shown as green **Verified complete**.

A stale Chat response against a CLOSED issue must be denied with no mutation. Final proof includes `reason=human_reach_stale_response`, expected `ACTION_PENDING`, current `CLOSED`.

## Facilities photo proof

The frontline submission point is Google Chat, not the Operations drawer.

Accepted sequence:

1. Facilities worker clicks **Completed** in the work card.
2. Card remains an unverified claim and requests exactly two images in the same work thread: BEFORE then AFTER.
3. Worker replies with the two synthetic images and @mentions Next Shift.
4. Gemini 3.5 compares visible change only.
5. Images are stored privately with hashes and inspection metadata as `SUPPORTING_VISUAL_EVIDENCE_ONLY`, `may_close_work=false`.
6. Separate trusted Facilities evidence moves the issue to `VERIFYING`.
7. Evidence Inspector checks the exact trusted evidence.
8. Independent Verifier alone closes the issue.
9. Human Reach refreshes the same card to green **Verified complete**.

Do not describe Gemini photo comparison as trusted closure evidence.

## Intake and Coverage Critic behavior

The intake path is deliberately robust to ordinary human shorthand, repeated same-owner work, uncertain component names, and imperfect spoken transcripts.

Coverage arbitration happens exactly once in Operations. `UNCERTAIN` findings may remain advisory while safe work continues. `DUPLICATED`, `CONFLATED`, or `MISROUTED` findings must be scoped to concrete proposals; only implicated proposals are held. An unscoped blocker gets one Gemini scoping pass and cannot silently erase unrelated work.

UI results must name each created and held item so nothing disappears between model analysis and durable State Authority work.

## Evidence and closure authority

Closure is intentionally separated:

1. specialist or human claim — not proof;
2. optional Gemini visual support — supporting evidence only;
3. trusted source-specific integration — operational evidence;
4. Evidence Inspector — exact-evidence PASS/FAIL;
5. Independent Verifier — only identity allowed to request final closure.

State Authority validates principal, capability, owner, current state, freshness, requested transition, and evidence prerequisites before mutation.

## Recovery

Recovery Planner is advisory only. It may read bounded current state and recommend an allowlisted action, but cannot mutate state, change owner, record evidence, or close work. Operations separately sanctions the exact plan against fresh state.

Final proof includes a real `recovery.sanction` ALLOW with `reason=recovery_action_sanctioned`.

Do not add recovery UI or controls unless explicitly required by the product plan. The demo should show prepared proof, not developer recovery controls.

## Cross-shift continuity and Memory Bank

Firestore and Memory Bank serve different purposes:

- Firestore: authoritative current work state and durable workflow history;
- Memory Bank: persistent advisory historical patterns and improvement context.

Incoming shifts re-read current Firestore truth rather than trusting stale summaries.

The Operational Improvement Advisor uses Gemini 3.5 and managed Memory Bank context, but declares `authority=ADVISORY_ONLY`, `current_state_authority=Firestore`, and `may_mutate_workflow=false`.

## Google platform stack

The final product deliberately uses and proves:

- Gemini 3.5
- Google ADK
- Vertex AI Agent Runtime
- managed Agent Identity
- Agent Registry
- Memory Bank
- Agent Gateway
- Model Armor
- Cloud Run
- IAM
- IAP
- Pub/Sub
- Firestore
- Google Chat
- Cloud Logging / Cloud Run telemetry

Gateway / Model Armor behavioral proof must show benign `200 / ALLOW`, instruction-bypass `403 / DENY`, and `fail_open=false` through the bound managed runtime path.

## Observability truth

`/trace/<issue_id>` is a durable governed lifecycle correlation view assembled from persisted operational records: intake, event, route, specialist, Human Reach, supporting visual evidence, trusted evidence, inspector, verifier, recovery, principals, capabilities, and final state.

Cloud Logging / Cloud Run provide real service revision, request, authorization, denial, proof, and security telemetry separately.

Do not fabricate one synthetic distributed trace. Native application OTLP export is not claimed; exact scope is documented in `docs/verification.md`.

## Reliability

Required production guarantees include:

- versioned event contracts;
- deterministic routing;
- owner-filtered Pub/Sub subscriptions;
- dedicated specialist and push identities;
- current-state checks;
- processed-event idempotency;
- bounded retry;
- DLQ handling;
- resumable specialist workflows;
- stale-action protection;
- exact evidence and verifier separation.

Duplicate events must not duplicate state mutation. Poison/malformed events must fail visibly and reach bounded retry/DLQ behavior.

## Final accepted live proof

Final Aug 27 acceptance proved:

- messy multi-item text intake;
- repeated same-owner Facilities jobs staying separate;
- disputed printer repair held while safe jobs continued;
- Gemini 3.5 spoken handover reaching durable work;
- authoritative Human Reach card refresh;
- completion claim remaining unverified;
- stale Human Reach action DENY with no mutation;
- Facilities BEFORE/AFTER photos submitted in Chat;
- Gemini 3.5 visual comparison as supporting evidence only;
- trusted evidence moving work to `VERIFYING`;
- Independent Verifier closure and green Chat **Verified complete**;
- Gateway/Model Armor `200 / 403` fail-closed proof;
- sanctioned recovery proof;
- branch readiness `179 PASS / 1 authorized branch warning / 0 FAIL / NEXT_SHIFT_READINESS=PASS` before the Memory 3.5 readiness extension.

The durable acceptance record is `docs/autonomy/evidence/100-final-product-acceptance-20260827.md`.

## Final submission gate

Final submission must be tested on clean current `main`:

```bash
bash verify_readiness.sh
```

Required terminal condition:

```text
WARN=0
FAIL=0
NEXT_SHIFT_READINESS=PASS
```

The exact PASS count may increase as high-value checks are added.

Compact read-only judge proof:

```bash
bash scripts/demo_proof_snapshot.sh
```

## Development workflow

Always begin substantive work by:

```bash
cd /home/patrick/next-shift
cat AGENTS.md
git fetch origin
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

Repository and deployed GCP state are authoritative.

Preferred cycle:

```text
inspect current repo/live truth
→ make the narrowest repo change
→ syntax / focused contract checks
→ full tests where warranted
→ deploy the exact affected service(s)
→ run real integration acceptance
→ inspect authoritative state/logs
→ readiness
→ commit/PR/merge
```

Do not patch production manually when the change belongs in the repo. Prefer repo/branch changes followed by pull, test, and reproducible deployment. Avoid giant ad-hoc heredocs and unnecessary local preview detours.

Do not turn the project into a test-count exercise. Tests should protect state integrity, authorization, idempotency, evidence, model requirements, routing, and security boundaries.

## Current objective

The product feature phase is frozen. The remaining work is:

1. ensure PR #31 and documentation are truthful;
2. merge to `main`;
3. deploy the exact merged `main` revisions;
4. run clean-main readiness with zero warnings/failures;
5. smoke-test the accepted live paths;
6. rehearse and record the approximately four-minute demo in `docs/demo-script.md`;
7. submit.

Do not add new features unless a concrete final acceptance or eligibility failure requires one.
