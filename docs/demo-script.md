# Next Shift final demo script

## Demo objective

Show that Next Shift is not a handover summarizer or a collection of chatbots. It is a governed operational fleet that continues work across shifts and refuses to trust unverified completion claims.

Target length: 4–6 minutes.

## Opening — 20 seconds

“Every 24/7 operation has the same failure point: work crosses a shift boundary, context gets compressed into handover notes, and somebody later has to figure out what actually happened. Next Shift does not summarize the handover. It finishes the operational work left behind by it.”

Show Operations Control.

## Scene 1 — messy handover becomes durable work

Paste one synthetic handover containing:

- missing standard wheelchair
- Spanish interpreter request
- home oxygen DME pending
- EVS room turnaround
- leaking sink
- patient transport to Discharge Lounge

Narration:

“One messy handover becomes six independent operational jobs. The Agent Runtime interprets the text, but it does not own workflow truth. State Authority persists the work into Firestore.”

Show the ranked work queue populated across all six specialist owners.

## Scene 2 — least-privilege fleet

Briefly show the six owners and explain:

“Each job is published with owner metadata. Pub/Sub subscriptions are filtered by owner, each push path uses its own OIDC identity, and each specialist runs under a dedicated service account.”

Optional terminal cutaway:

`bash verify_readiness.sh`

Use the final line only:

`PASS=159 WARN=0 FAIL=0 — NEXT_SHIFT_READINESS=PASS`

Narration:

“State Authority is the only Next Shift runtime identity that can write Firestore. Specialists cannot bypass it.”

## Scene 3 — frontline coordination

Open one Google Chat Human Reach card.

Narration:

“Operational work often leaves the software boundary. Next Shift reaches the frontline through Google Chat with WHO, WHAT, WHERE and a work order.”

Point out that the card offers acknowledgement, block or completion claim actions.

## Scene 4 — the defining trust boundary

Use a fresh issue in `ACTION_PENDING` and click **Completed** in Google Chat.

Narration:

“This is the part that matters: a human says the task is complete. Next Shift records that as a claim. It does not treat the claim as proof.”

Show Operations Control displaying `CLAIMED · UNVERIFIED`.

Then record trusted synthetic evidence.

Narration:

“A trusted external evidence identity records evidence. That moves the issue to `VERIFYING`, but still does not close it.”

Run the independent verifier.

Narration:

“Only an independent verifier can request `VERIFYING → CLOSED`. The specialist, frontline worker and evidence service cannot self-certify closure.”

Show `CLOSED · VERIFIED`.

## Scene 5 — governed lifecycle trace

Open `/trace/<issue_id>`.

Narration:

“Every important decision is inspectable. This is not decorative telemetry. These are the real durable IDs, principals, capabilities, timestamps, Human Reach records, evidence record and verifier identity that produced the final state.”

Scroll through:

- intake
- specialist transitions
- Human Reach
- trusted evidence
- verifier
- closed state

## Scene 6 — stale action is denied

Show the previously accepted stale-response proof, or perform it on a prepared issue if time allows.

Narration:

“Even an old valid Google Chat card cannot mutate work after authoritative state has moved on.”

Show audit line:

- `decision=DENY`
- `principal=ns-human-reach@...`
- `capability=human_reach.delivery_update`
- `reason=human_reach_stale_response`
- `current=CLOSED`
- `expected=ACTION_PENDING`

Narration:

“The request reached the real production path and State Authority rejected it. Firestore stayed `CLOSED · VERIFIED`.”

## Scene 7 — prohibited clinical request

Submit a synthetic clinical instruction such as a medication-prescribing request.

Narration:

“Next Shift’s authority is deliberately narrow. Clinical work is outside scope. A prohibited instruction is refused without creating operational work.”

Do not linger on the clinical example; the point is the authority boundary.

## Scene 8 — Google platform architecture

Use the architecture diagram while narrating:

“Next Shift runs on a managed Agent Runtime with Agent Identity. Agent Gateway governs the client-to-agent path. Model Armor is attached through content authorization. State Authority is the Firestore mutation choke point. Cloud Run and Pub/Sub provide the event-driven specialist fleet. Google Chat provides Human Reach. Trusted evidence plus an independent verifier control closure.”

## Closing — 20 seconds

“Next Shift is built around one principle: no agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned and verifiable. That is how a handover stops being a summary and becomes finished work.”

## Recording guidance

Capture clean shots of:

1. empty/clean Operations Control opening
2. handover text before submit
3. six-owner work queue after submit
4. one Human Reach Google Chat card
5. `CLAIMED · UNVERIFIED`
6. evidence → `VERIFYING`
7. verifier → `CLOSED · VERIFIED`
8. governed lifecycle trace
9. stale-response DENY audit line
10. final architecture diagram
11. readiness verifier final result

Avoid showing Cloud Shell clutter unless it proves a security/reliability point. Prefer the UI and trace page for the main story.
