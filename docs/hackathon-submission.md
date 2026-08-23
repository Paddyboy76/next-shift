# Next Shift — hackathon submission copy

## Title

**Next Shift — A Fortified Autonomous Operations Fleet for Work That Survives the Handover**

## Tagline

**The handover ends. The work does not.**

## One-line pitch

Next Shift turns messy shift handovers into durable operational work and refuses to close anything until trusted evidence, independent inspection, and an independent verifier prove it is done.

## Submission description

Next Shift is a general handover and operational continuity system for 24/7 enterprises, demonstrated in a fully synthetic, non-clinical hospital operations environment.

One unstructured handover becomes multiple persistent jobs. A managed ADK Agent Runtime interprets the text, while an independent Gemini Coverage Critic checks the proposed issue set for missed, duplicated, conflated, uncertain, or misrouted work. State Authority then persists accepted work in Firestore and publishes owner-routed events. Dedicated Cloud Run specialists continue the workflows asynchronously through Pub/Sub and coordinate frontline action through Google Chat.

No model, specialist, or human claim can certify completion. A frontline “Completed” action remains `CLAIMED · UNVERIFIED`. A trusted source-specific synthetic integration must record evidence, a separate Evidence Inspector must pass that exact evidence, and only the independent verifier can request closure.

## Why it is agentic

The system reasons about ambiguous input, decomposes it into typed work, criticizes its own coverage through a separate model call, selects specialist ownership, and initiates durable asynchronous execution. The work continues after the user leaves: specialists wake from events, resume from current state, coordinate humans, wait for external proof, recover safely from delay or rejection, and independently verify outcomes.

The model does not own truth. Agentic reasoning is deliberately bounded by deterministic contracts, persisted state, identities, and independent proof.

## Why it is fortified

- Agent Runtime uses managed Agent Identity and is represented in Agent Registry.
- Agent Gateway governs the real `CLIENT_TO_AGENT` path; fail-closed Model Armor content authorization blocks a controlled instruction-bypass probe.
- Operations Control is protected by IAP.
- State Authority is the sole Next Shift Firestore writer.
- Six specialists have dedicated Cloud Run identities and owner-filtered Pub/Sub subscriptions with OIDC audiences.
- Principal/capability/owner/state rules are deterministic and denials are auditable.
- Duplicate handling is idempotent; retries are bounded; poison events reach a DLQ.
- Evidence, inspector, and verifier are separate identities with no direct Firestore access.
- Recovery Planner is advisory, cannot mutate/record evidence/close, and requires explicit sanction against fresh state.
- Memory Bank advice is `ADVISORY_ONLY`; Firestore remains current-state authority.

## Defining product moment

A frontline worker clicks **Completed** in Google Chat. Next Shift does not close the issue. It records an unverified claim, waits for independently sourced synthetic evidence, requires an exact-evidence inspection PASS, and permits only the separate verifier to close the work.

That implements the core rule:

> No agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable.

## Deployed proof

The live synthetic project has demonstrated:

- one handover producing six correctly routed operational jobs;
- independent intake critique and visible disagreement handling;
- Google Chat delivery to durable operational spaces;
- duplicate ACK without duplicate state mutation;
- bounded malformed-event retry and DLQ delivery;
- external synthetic evidence, exact-evidence inspection, and independent closure;
- stale Chat action denial with unchanged authoritative state;
- a full governed lifecycle trace;
- registered runtime lifecycle and managed advisory Memory Bank intelligence;
- a controlled recovery plan, separate sanction, fresh evidence, and independent closure;
- benign HTTP 200 and instruction-bypass HTTP 403 through the bound Runtime/Gateway/Model Armor path.

The read-only readiness gate has expanded beyond its `159 PASS / 0 WARN / 0 FAIL` golden baseline. Current success is defined by zero warnings, zero failures, and `NEXT_SHIFT_READINESS=PASS` on clean current `main`, not by freezing the earlier check count.

## Google technology

- Vertex AI Agent Runtime, Google ADK, Gemini, and managed Agent Identity
- Agent Registry and Memory Bank
- Agent Gateway and Model Armor
- Cloud Run, IAM, IAP, Pub/Sub, and Firestore
- Google Chat Human Reach
- Cloud Logging and Cloud Run request telemetry

The governed issue trace uses real durable correlation records alongside real Cloud Run trace/span fields. Native application OTLP spans are not claimed because export was unavailable at the current permission boundary.

## Safety and scope

All data, workspaces, evidence, and integration records are synthetic. The product is non-clinical and has no authority over diagnosis, prescribing, clinical acuity decisions, treatment interpretation, or licensed clinical work. It uses no real hospital data, branding, screenshots, identifiers, internal systems, or proprietary workflows.
