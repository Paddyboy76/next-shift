# Next Shift final demo script

## Goal

Deliver one **continuous, live, approximately four-minute** demonstration that proves Next Shift is a fortified operational fleet—not a summarizer, chatbot collection, or decorative dashboard.

Use only synthetic operational data and already-accepted live paths. Keep the product UI on screen for most of the demo. Use the terminal briefly for high-value Google Cloud proof, not as the main experience.

## Recording rules for this run

- One continuous take. Do not splice together separate successes.
- Rehearse the exact path immediately before recording.
- Keep one browser window with three prepared tabs: **Operations**, **Google Chat**, and **Cloud Shell**.
- Keep the terminal font large enough to read on a laptop screen.
- Do not type long commands during the recording. Use the repository's read-only `scripts/demo_proof_snapshot.sh` for the terminal proof.
- If a live model step stalls, narrate what is happening and stay truthful. Do not fake a success state.
- Do not create or expose real hospital data, branding, screenshots, identifiers, or workflows.

## What judges must understand by the end

1. a normal human handover becomes several durable operational jobs;
2. Gemini 3.5 is used for reasoning, speech, critique, and multimodal evidence support;
3. work continues asynchronously after the initiating interaction;
4. six specialists are isolated by owner and identity;
5. a human completion claim is not trusted as proof;
6. photo evidence can arrive through the frontline Google Chat workflow;
7. trusted evidence and a separate verifier control closure;
8. stale and unauthorized actions fail visibly;
9. Agent Registry, Runtime, Memory Bank, Identity, Gateway, Model Armor, and observability are real deployed platform elements;
10. the final deployed stack passes the readiness gate.

---

## 0:00–0:18 — cold open on the trust boundary

Start in **Google Chat** on the prepared synthetic Facilities leaking-tap work card.

Say:

> “A frontline worker can say the job is complete. Next Shift does not trust that as proof.”

Click **Completed** once.

Show the card becoming a completion claim and requesting BEFORE + AFTER photo proof instead of closing.

Then say:

> “That is the core design rule: a claim is not operational truth.”

This is the hook. Do not start with architecture.

## 0:18–0:48 — multimodal proof from the frontline workflow

In the same Chat work thread, attach the rehearsed synthetic **BEFORE** and **AFTER** leaking-tap images and @mention Next Shift.

Show the fast Gemini 3.5 response.

Say:

> “Gemini 3.5 compares what is visibly supported, but the images are supporting evidence only. Gemini still cannot close the work.”

Switch to Operations as the issue advances to **Stage 5 · Verify** and open the drawer. Briefly show the read-only before/after evidence and the trusted evidence entry.

Run the existing **Independent Verifier** action.

Show `VERIFYING → CLOSED` and then switch back to the same Chat card for green **Verified complete**.

Say:

> “A separate trusted evidence identity moved the work to verification. A separate Evidence Inspector checked the exact evidence. Only the Independent Verifier could close it.”

## 0:48–1:18 — messy spoken handover to durable work

Return to Operations.

Click **Record spoken handover** and speak one rehearsed, ordinary human paragraph containing several non-clinical jobs. Do not speak like a schema.

A good synthetic example:

> “The printer on seven isn't printing and the light keeps blinking, the meeting room aircon is leaking again, there’s water coming from something in the kitchen cupboard on eight, and the cupboard door itself is hanging loose.”

Stop recording. Show the Gemini 3.5 transcript and any explicit uncertain phrase. Do not clean up ordinary wording merely to help the system.

Click **Send to Next Shift**.

Point to the explicit intake outcomes: created jobs and any held-for-review item.

Say:

> “Gemini 3.5 normalizes messy human language into our six canonical channels. A second Gemini Coverage Critic checks omissions, duplication, conflation, uncertainty, and routing. Safe jobs keep moving; disputed work is held instead of silently lost.”

If the printer is held because none of the six channels clearly owns printer repair, that is a good boundary demonstration. Do not imply there is an IT agent.

## 1:18–1:38 — show the fleet, then let the user leave

Show the team strip and several newly created Facilities jobs as distinct cards.

Say:

> “The user is done. The work is not.”

Move away from the intake area—open another tab or simply stop interacting with Operations for several seconds while the cards progress asynchronously.

Say:

> “State Authority persists every job in Firestore. Owner-filtered Pub/Sub wakes dedicated Cloud Run specialists. The initiating user does not need to stay connected.”

Show one issue reaching `ACTION_PENDING` without another handover interaction.

## 1:38–2:00 — cross-shift continuity and Memory Bank

Open **Past**.

Show:

- Completed history;
- Shift snapshots / carried work;
- Improvement Advisor recommendations.

Say:

> “Current state and historical memory are deliberately separate. Firestore is authoritative now. Shift snapshots preserve what crossed the handover. Memory Bank carries longer-term synthetic patterns across sessions, but it is advisory only and cannot mutate work.”

This directly answers the Fortified track's extended-context requirement.

## 2:00–2:22 — full lifecycle trace

Open the completed leaking-tap issue and its **Full audit trail**.

Point to the latest event first and the collapsed earlier history.

Say:

> “This is durable operational correlation: intake, route, specialist action, human claim, visual support, trusted evidence, inspection, verifier, and closure—with exact principals, timestamps, and evidence IDs preserved.”

Do not call it a fabricated single distributed trace. It is an authoritative lifecycle trace plus real Cloud platform telemetry.

## 2:22–2:52 — one compact terminal proof of the Google stack

Switch to Cloud Shell and run exactly:

```bash
cd /home/patrick/next-shift
bash scripts/demo_proof_snapshot.sh
```

Pause long enough for the output to be readable.

Point to only four things:

1. **Cloud Run revisions + service identities** for Operations, Human Reach, Coverage Critic, State Authority, and Verifier;
2. **Gemini 3.5** serving for spoken handover and photo proof;
3. **Gateway / Model Armor:** benign `200 / ALLOW`, bypass `403 / DENY`, `fail_open=false`;
4. **State Authority security records:** stale Chat `DENY` and controlled recovery sanction `ALLOW`.

Say:

> “These are live reads from the deployed Google Cloud project, not labels in the UI.”

Do not scroll through dozens of services. The compact snapshot is enough.

## 2:52–3:20 — Fortified Enterprise Fleet architecture

Return to the README architecture diagram or the clean architecture view.

Say:

> “The managed ADK runtime uses Agent Identity and is cataloged in Agent Registry. Agent Gateway and fail-closed Model Armor govern the client-to-agent path. Six Cloud Run specialists are isolated behind Pub/Sub and IAM. Memory Bank preserves advisory long-term context. State Authority is the only workflow writer.”

Then make the enterprise-generalization sentence explicit:

> “The hospital is synthetic demo data. These six channels could be maintenance, logistics, language support, room turnaround, transport, or equivalent operational teams in a factory, airline, hotel, utility, data center, or any 24/7 enterprise.”

## 3:20–3:42 — final readiness proof

Use a **pre-run clean-main readiness result already visible in Cloud Shell**. Do not burn the last 20 seconds waiting for the entire gate to rerun unless rehearsal proves it consistently completes within the time budget.

The screen must visibly show:

```text
WARN=0
FAIL=0
NEXT_SHIFT_READINESS=PASS
```

Do not hard-code an old PASS count in narration. The exact count grows as checks are added.

Say:

> “The gate verifies live Cloud Run revisions, IAM and invoker isolation, Firestore authority, Pub/Sub routing and retry policy, stale-action denial, managed Agent Identity, Agent Gateway, Model Armor, and the recovery proof.”

This is a truthful pre-run production gate result from the same deployed revision shown in the live demo, not a fabricated overlay.

## 3:42–4:00 — close

Return to Operations or the green **Verified complete** Chat card.

Say:

> “Next Shift is built around one principle: no agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable. The handover ends. The work does not.”

Stop.

---

## Pre-recording setup

### Browser tabs

1. **Operations Control** — authenticated through IAP.
2. **Google Chat · Next Shift – Facilities Ops** — fresh leaking-tap card ready.
3. **Cloud Shell** — authenticated, project `next-shift-506004`, repository on clean current `main`.
4. Optional fourth tab: README architecture diagram positioned at the Mermaid diagram.

### Synthetic demo assets

Prepare two obvious images for the Facilities repair:

- BEFORE: visibly leaking/broken tap or fitting;
- AFTER: same subject/location with an obvious repaired/replaced state.

Avoid ambiguous pairs such as “window open” vs “window closed.” Gemini correctly treats those as insufficient repair proof.

### Terminal rehearsal

Before recording:

```bash
cd /home/patrick/next-shift
bash scripts/demo_proof_snapshot.sh
bash verify_readiness.sh | tee /tmp/next-shift-demo-readiness.log
```

Leave the final readiness lines visible or easily retrievable with:

```bash
tail -8 /tmp/next-shift-demo-readiness.log
```

Confirm the proof snapshot returns live values and readiness ends with zero warnings/failures on clean main.

### Live facts to capture

- Gemini 3.5 spoken transcript;
- explicit created/held intake outcomes;
- several distinct jobs from one human paragraph;
- `CLAIMED · UNVERIFIED` after frontline completion;
- Chat BEFORE/AFTER photo submission;
- Gemini supporting visual comparison;
- trusted evidence separated from visual support;
- Evidence Inspector + Independent Verifier closure;
- Chat green **Verified complete**;
- durable lifecycle trace;
- Cloud Run revisions and service identities;
- Gateway/Model Armor `200 / 403` proof;
- stale Human Reach `DENY`;
- recovery sanction `ALLOW`;
- clean-main `NEXT_SHIFT_READINESS=PASS`.

## What not to do in the video

- Do not spend 30 seconds typing terminal commands.
- Do not show recovery-plan developer controls or manufacture a failure live.
- Do not claim the printer belongs to Asset Logistics when no canonical channel clearly owns printer repair.
- Do not describe Gemini photo comparison as trusted closure evidence.
- Do not describe Memory Bank as current operational state.
- Do not hide a live failure. If something fails, state what failed and show the authoritative state.
- Do not show private keys, tokens, emails beyond service identities, or any non-synthetic hospital information.
- Do not over-explain implementation details before the judge sees the product work.
