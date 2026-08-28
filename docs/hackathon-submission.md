# Next Shift — hackathon submission copy

## Title

**Next Shift — A Fortified Autonomous Operations Fleet for Work That Survives the Handover**

## Tagline

**The handover ends. The work does not.**

## One-line pitch

Next Shift turns messy human shift handovers into durable operational work across six enterprise channels and refuses to close anything until trusted evidence and an independent verifier prove it is done.

## Submission description

Next Shift is a general handover and operational continuity system for 24/7 enterprises, demonstrated in a fully synthetic, non-clinical hospital operations environment.

A human can type or speak an ordinary handover paragraph without knowing the schema. Gemini 3.5 normalizes the handover into distinct operational jobs across Facilities, Asset Logistics, Language Access, Discharge Equipment, EVS Throughput, and Patient Transport. A separate Gemini 3.5 Coverage Critic checks the proposed work for omissions, duplicates, conflation, routing errors, and uncertainty. Safe work continues while a genuinely disputed proposal can be held for review rather than silently disappearing or blocking unrelated jobs.

State Authority persists accepted work in Firestore and publishes owner-routed Pub/Sub events. Dedicated Cloud Run specialists continue the workflows asynchronously after the initiating interaction ends. Human Reach delivers frontline work through Google Chat, where people can acknowledge, report a blocker, or report completion.

A completion claim is not proof. `Completed` remains `CLAIMED · UNVERIFIED`. For Facilities, the frontline worker can reply in the same Google Chat work thread with BEFORE and AFTER images. Gemini 3.5 compares the visible change, but the images are explicitly supporting evidence only. A separate trusted source-specific evidence identity must still record completion evidence, a separate Evidence Inspector must pass the exact evidence, and only the Independent Verifier can request `CLOSED`.

## Why it is agentic

Next Shift does more than answer a prompt. It:

- understands messy text or spoken handover input;
- decomposes one handover into multiple typed jobs, including repeated jobs for the same owner;
- runs a second independent Gemini coverage review;
- persists accepted work so it survives the initiating interaction and shift boundary;
- wakes dedicated specialists asynchronously through owner-filtered Pub/Sub;
- coordinates frontline humans through Google Chat;
- waits for external proof instead of trusting a completion claim;
- uses a separate inspector and verifier for closure;
- preserves unresolved work across shifts;
- uses Memory Bank for persistent advisory historical patterns;
- can recommend bounded recovery from delayed or rejected work without giving the planner mutation authority.

The model reasons. The governed fleet owns execution and truth.

## Why it is fortified

- **Agent Registry:** the managed Next Shift runtime is cataloged as a registered agent/service for governed lifecycle and enterprise discovery.
- **Agent Runtime + Google ADK:** long-running managed reasoning with managed Agent Identity.
- **Memory Bank:** persistent historical context across sessions while Firestore remains current-state authority.
- **Agent Identity / IAM:** every service-to-service capability is bound to a narrow runtime identity.
- **Agent Gateway:** the live managed runtime is bound through the `CLIENT_TO_AGENT` governed path.
- **Model Armor:** fail-closed content authorization blocks a controlled prompt-injection/instruction-bypass attempt.
- **Operations Control:** protected by IAP.
- **State Authority:** sole Next Shift Firestore writer and deterministic mutation choke point.
- **Six specialists:** dedicated Cloud Run identities and owner-filtered Pub/Sub subscriptions with OIDC audiences.
- **Reliability:** processed-event idempotency, bounded retries, and dead-letter handling.
- **Evidence separation:** Human Reach, visual comparison, trusted evidence, Evidence Inspector, and Independent Verifier have distinct authority.
- **Recovery separation:** Recovery Planner is advisory and requires a separate sanction against current authoritative state.
- **Observability:** durable lifecycle correlation plus inspectable Cloud Logging / Cloud Run telemetry, denial records, proof traces, and live serving revisions.

## Defining product moment

A Facilities worker receives a job in Google Chat and taps **Completed**.

Next Shift does not close the issue.

The Chat card becomes an unverified completion claim and asks the worker to reply in that job thread with BEFORE and AFTER photos. Gemini 3.5 compares what is visibly supported. If the pair supports the repair, the images are stored privately as supporting evidence and a separate trusted Facilities integration records source-specific evidence. The issue moves to `VERIFYING`. A separate Evidence Inspector checks the exact evidence, and only the Independent Verifier can close it. The Google Chat card then refreshes to green **Verified complete**.

That implements the core rule:

> No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable.

## Deployed live proof

The final deployed acceptance demonstrated:

- one messy handover producing multiple correctly routed jobs;
- repeated Facilities work remaining separate instead of being conflated;
- a disputed printer-repair proposal being held while unrelated safe work continued;
- spoken Gemini 3.5 handover transcription and end-to-end governed intake;
- Google Chat delivery and authoritative card refresh;
- a frontline completion claim remaining unverified;
- Facilities BEFORE/AFTER images submitted in the Chat work thread and compared by Gemini 3.5;
- separate trusted evidence moving work to `VERIFYING`;
- Evidence Inspector + Independent Verifier closing the exact issue;
- Chat refreshing to green **Verified complete**;
- stale Chat completion action denied with `reason=human_reach_stale_response` and no state mutation;
- duplicate event handling without duplicate mutation;
- bounded malformed-event retry and DLQ delivery;
- cross-shift continuity using current Firestore truth;
- a controlled recovery plan and separate `recovery_action_sanctioned` proof;
- Agent Gateway / Model Armor behavioral proof with benign HTTP `200 / ALLOW`, instruction-bypass HTTP `403 / DENY`, and `fail_open=false`;
- all judge-facing Gemini paths on `gemini-3.5-flash`;
- final clean-main submission gate: `180 PASS / 0 WARN / 0 FAIL / NEXT_SHIFT_READINESS=PASS / NEXT_SHIFT_SUBMISSION=PASS`.

Final repository state:

```text
main=882975f89595f6306f9c6246bd5a6983fa0d5bb1
152 tests passed
49 subtests passed
MODEL_ASSERT all_demo_gemini_3_5=true
```

The durable final freeze record is `docs/autonomy/evidence/101-final-submission-freeze-20260828.md`. The historical Aug 27 product-acceptance record is `docs/autonomy/evidence/100-final-product-acceptance-20260827.md`. The continuous live demo runbook is `docs/demo-script.md`.

## Google technology

- Gemini 3.5 through Vertex AI
- Google ADK
- Vertex AI Agent Runtime + managed Agent Identity
- Agent Registry
- Memory Bank
- Agent Gateway
- Model Armor
- Cloud Run
- IAM and IAP
- Pub/Sub
- Firestore
- Google Chat
- Cloud Logging and Cloud Run request telemetry

## Safety and scope

All text, audio, images, workspaces, evidence, and integration records in the demonstration are synthetic. The product is non-clinical and has no authority over diagnosis, prescribing, clinical acuity decisions, treatment interpretation, or licensed clinical work. It uses no real hospital data, branding, screenshots, identifiers, internal systems, or proprietary workflows.
