# Next Shift final demo script

## Goal

One **approximately four-minute** video that proves Next Shift is a fortified operational fleet — not a summarizer, a chatbot collection, or a decorative dashboard.

## Production method for this submission

Screen capture is driven by a browser agent following `docs/demo-browser-runbook.md`. Voiceover is recorded separately against the finished picture cut.

This is a deliberate change from an unassisted live take. It removes the timing risk of narrating over four live model calls, and it lets each UI state stay on screen long enough to read.

### The honesty line — do not cross it

The product's entire claim is that unverified claims are not truth. A judge who catches a faked frame ends the submission, so:

- **Allowed:** trimming dead waiting time; cutting a mouse fumble; speeding up a long async wait with a visible speed-up or a clean cut; recording voiceover separately.
- **Not allowed:** splicing a later successful attempt over an earlier failure to imply first-time success; showing a state the system did not actually produce; narrating anything the footage does not show.
- If a step genuinely fails during capture, fix the cause and **re-record that whole segment**, from the segment's first action. Never stitch a failed attempt to a successful one inside one continuous-looking motion.
- Every state on screen must be a state the deployed system actually produced from the actions visible in the same segment.

### Segment boundaries

Capture in the seven segments defined in the runbook. A cut between segments is an ordinary edit. A cut **inside** a segment may only remove waiting.

## Narration budget

Total spoken narration is approximately **400 words over 240 seconds** — about 100 words per minute. That is deliberately unhurried. Do not add sentences to fill silence; silence over a state change is doing work.

Each block below gives its word count. If you rewrite a line, keep the count.

## What the judge must understand by the end

1. an ordinary human handover becomes several durable operational jobs;
2. Gemini 3.5 does reasoning, speech, critique, and multimodal evidence support;
3. work continues asynchronously after the initiating interaction ends;
4. six specialists are isolated by owner and identity;
5. a human completion claim is not trusted as proof;
6. trusted evidence and a separate verifier control closure;
7. stale and unauthorized actions fail visibly;
8. Agent Registry, Runtime, Memory Bank, Identity, Gateway, and Model Armor are really deployed;
9. the deployed stack passes a readiness gate.

---

# The script

## 0:00–0:08 — teaser · the refusal (14 words)

**SCREEN** Google Chat, Facilities work card for the leaking tap.

**ACTION** The **Completed** button is clicked. The card resolves to `CLAIMED · UNVERIFIED` and asks for BEFORE and AFTER photos instead of closing.

**EXACT WORDS**

> "A worker just marked this repair complete. Next Shift refused to close it."

**CRITERION** Demo (30%) — hook.

**WHY THIS EARNS POINTS** A judge on their twentieth video decides in eight seconds whether to lean in. This is a flash-forward, not the start of the story: it buys attention and is paid off at 1:54. Nothing is explained yet, and nothing needs to be.

## 0:08–0:18 — orientation (20 words)

**SCREEN** Cut to Operations Control, top of page. The intro line `Interpret → Route → Execute → Prove → Verify` is visible.

**ACTION** None. Let the page sit.

**EXACT WORDS**

> "This is Next Shift. Unfinished work at shift change shouldn't become a note for the next person to chase."

**CRITERION** Utility (40%) — problem framing.

**WHY THIS EARNS POINTS** This names the pain, which the previous version of the script never did. Do **not** read out the five stage names here. They are on screen, and they are narrated at 0:56 when a card is actually moving through them — a taxonomy explained before anything moves is dead air.

## 0:18–0:56 — messy spoken handover becomes governed work (60 words)

**SCREEN** Operations intake panel.

**ACTION** **Record spoken handover** → the rehearsed paragraph plays → stop → transcript appears → **Send to Next Shift** → created and held outcomes are named on screen.

**THE SPOKEN PARAGRAPH** (ordinary human speech — do not clean it up)

> "The printer on seven isn't printing and the light keeps blinking, the meeting room aircon is leaking again, there's water coming from something in the kitchen cupboard on eight, and the cupboard door itself is hanging loose."

**EXACT WORDS**

> "One person, speaking normally, not knowing any schema. Gemini 3.5 transcribes it, then separates it into distinct jobs across six operational channels. A second Gemini Coverage Critic independently checks for omissions, duplication, conflation, and routing errors. Safe work moves. Genuinely disputed work is held for review rather than silently disappearing."

**CRITERION** Utility (40%) + Architecture (30%) + live proof.

**WHY THIS EARNS POINTS** Utility is the heaviest-weighted criterion, so it goes first. This is also the most impressive *live* moment in the demo — unstructured speech in, several correctly-owned governed jobs out. The held item is a feature, not a gap: it proves the system declines to guess.

**GUARDRAIL** If the printer is held because no canonical channel owns printer repair, say so plainly. Never imply there is an IT agent.

## 0:56–1:16 — the user leaves, the work does not (32 words)

**SCREEN** The new job cards. Cursor moves away and stops. Cards advance on their own.

**ACTION** No interaction for several seconds. At least one card reaches `ACTION_PENDING` untouched.

**EXACT WORDS**

> "The user is done. The work is not. Every job is persisted by State Authority in Firestore, then owner-filtered Pub/Sub wakes a dedicated Cloud Run specialist. Watch a job leave Interpret, pass Route, and reach Execute — with nobody driving it."

**CRITERION** Fortified Fleet — asynchronous long-running execution.

**WHY THIS EARNS POINTS** This is the single clearest answer to the track's core requirement, and it is the right moment to name the five stages, because the judge can see a card crossing them. Hold the shot through the silence. The absence of interaction *is* the proof.

## 1:16–1:54 — the claim, and why it isn't enough (60 words)

**SCREEN** Google Chat, Facilities card — now in context.

**ACTION** Show `CLAIMED · UNVERIFIED` from the teaser. Attach the synthetic BEFORE and AFTER images in the same thread, @mention Next Shift, show the Gemini 3.5 comparison reply.

**EXACT WORDS**

> "Frontline teams don't need another console — work reaches them in Google Chat. But completed is not closed. Gemini 3.5 compares what visibly changed between before and after. That is supporting evidence only. It is stored with hashes, marked as visual support, and it explicitly cannot close the work. Neither can the worker."

**CRITERION** Architecture (30%) — authority separation, multimodal Gemini.

**WHY THIS EARNS POINTS** This is where the teaser pays off, and the judge now understands why the refusal at 0:00 was the right behaviour rather than a bug. Saying that the model *cannot* close work is a stronger architecture signal than any capability claim.

## 1:54–2:18 — trusted evidence and independent closure (40 words)

**SCREEN** Operations, the issue advancing to Stage 5 · Verify, then the same Chat card.

**ACTION** Show the trusted Facilities evidence entry, run the Independent Verifier, show `VERIFYING → CLOSED`, then cut to the Chat card refreshing to green **Verified complete**.

**EXACT WORDS**

> "A separate trusted evidence identity moved this to verification. A separate Evidence Inspector checked the exact evidence submitted. And only the Independent Verifier — an identity nobody else can act as — was permitted to close it."

**CRITERION** Architecture (30%) — strict separation of responsibilities.

**WHY THIS EARNS POINTS** Four distinct authorities in one closure, each provable. The green card returning to the exact surface the video opened on closes the loop visually.

## 2:18–2:38 — the governed record (34 words)

**SCREEN** The issue drawer / full audit trail.

**ACTION** Open the drawer. Rest at the top, then scroll once, slowly.

**EXACT WORDS**

> "We don't dump an event log on an operator. The top answers three questions: where is this now, what just happened, what is it waiting for. Everything underneath is there for whoever has to investigate."

**CRITERION** Architecture + observability, and UX maturity.

**WHY THIS EARNS POINTS** Explaining the *hierarchy* rather than reading the contents shows product judgment, which reads as production readiness. Do not call this a distributed trace — it is a durable lifecycle correlation, and the distinction is in `docs/verification.md`.

## 2:38–2:58 — what survives the shift (34 words)

**SCREEN** **Past** panel: carried work, shift snapshots, Improvement Advisor.

**ACTION** Open Past. Rest on carried work first.

**EXACT WORDS**

> "Current state and long-term memory are deliberately separate. Firestore is authoritative now. Snapshots preserve what crossed each handover. Memory Bank carries patterns across sessions — but it is advisory, and it cannot change operational truth."

**CRITERION** Fortified Fleet — persistent cross-session context over weeks.

**WHY THIS EARNS POINTS** Directly answers the track's extended-context requirement.

**PRE-FLIGHT GATE — this block is conditional.** Do not record it unless the runbook's pre-flight confirms **carried work ≥ 1**, **shift snapshots ≥ 1**, and **advisor cards rendering populated fields**. Pointing a camera at "Shift snapshots 0" or blank advisor cards actively costs more points than skipping the block. If the gate fails and cannot be fixed, cut the snapshot and Memory Bank sentences, keep carried work only, and give the recovered seconds to 0:18–0:56.

## 2:58–3:26 — one compact live proof of the Google stack (46 words)

**SCREEN** Cloud Shell, large font.

**ACTION** Run `bash scripts/demo_proof_snapshot.sh`. Hold the output still and readable. Point at four things only.

**EXACT WORDS**

> "These are live reads from the deployed project, not labels in a UI. Real Cloud Run revisions and distinct service identities. Gemini 3.5 serving both speech and photo comparison. Agent Gateway and Model Armor: the allowed path returns two hundred, the bypass attempt returns four-oh-three, and it fails closed. And a stale Chat response against already-closed work: denied, with no mutation."

**CRITERION** Architecture + production readiness.

**WHY THIS EARNS POINTS** The `403` and the stale `DENY` are the highest-value frames in the whole video: they prove the security boundary by showing something correctly *fail*. Most submissions only show things succeeding.

**GUARDRAIL** Do not scroll through dozens of services. Four things, then move.

## 3:26–3:46 — architecture and generalization (34 words)

**SCREEN** README architecture diagram.

**ACTION** Rest on the diagram. No scrolling.

**EXACT WORDS**

> "Memory Bank lets the system learn across shifts without touching current work. Agent Identity means Facilities cannot act as the verifier. Gateway and Model Armor mean the allowed path succeeds and bypasses fail closed. The hospital is synthetic. The six channels are any 24/7 enterprise — factory, airline, hotel, utility, data centre."

**CRITERION** Fortified Fleet checklist + innovation.

**WHY THIS EARNS POINTS** Every platform component is stated as a *because*, never as a name on a list. "We use Agent Identity" scores nothing; "Facilities cannot act as the verifier" scores. This is the block most at risk of sounding like rubric-reading — keep the causal clause on every single item.

## 3:46–4:00 — close (24 words)

**SCREEN** Readiness output showing `WARN=0`, `FAIL=0`, `NEXT_SHIFT_READINESS=PASS`, then the green Chat card.

**EXACT WORDS**

> "The deployed stack passes its own production gate. No agent claim is trusted merely because a model said it. The handover ends. The work does not."

**CRITERION** Readiness + memorable close.

**WHY THIS EARNS POINTS** Ends on the product line, on the same surface the video opened on. Do not narrate a hard-coded PASS count — the number grows as checks are added, and a stale number is a needless accuracy risk.

---

# Pre-recording preparation

## Data preparation (must pass before capture)

```bash
# 1. Seed at least one real shift snapshot from current authoritative state.
python scripts/seed_shift_snapshot.py --outgoing "Night shift" --incoming "Day shift"
python scripts/seed_shift_snapshot.py --list

# 2. Refresh Memory Bank so the advisor renders real Gemini recommendations.
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud run services describe next-shift-memory-sync --region asia-southeast1 \
     --format='value(status.url)')/v1/sync" | head -40
```

Then confirm in the Operations **Past** panel that shift snapshots is non-zero and advisor cards show a populated pattern, why, confidence, and scope. If `recommendation_source` is `LOCAL_DETERMINISTIC_FALLBACK`, the memory service did not answer — the cards will render, but they are not Gemini output, so re-run the sync before recording.

## Terminal preparation

```bash
bash scripts/demo_proof_snapshot.sh
bash verify_readiness.sh | tee /tmp/next-shift-demo-readiness.log
tail -8 /tmp/next-shift-demo-readiness.log
```

`scripts/demo_proof_snapshot.sh` runs `set -euo pipefail` and **exits immediately if the active project is not `next-shift-506004`**. Pin the project in the recording tab and prove the script runs clean there before capture:

```bash
gcloud config set project next-shift-506004
```

## Synthetic assets

- BEFORE: visibly leaking or broken tap/fitting.
- AFTER: same subject and location, obviously repaired.
- Avoid ambiguous pairs such as "window open" vs "window closed" — Gemini correctly treats those as insufficient repair proof, which is right behaviour but a poor demo frame.
- Spoken paragraph as a 16-bit PCM WAV for the browser's fake audio device (see runbook).

## What not to do in the video

- Do not spend time typing long terminal commands.
- Do not show recovery-plan developer controls or manufacture a failure live.
- Do not claim the printer belongs to Asset Logistics when no canonical channel owns printer repair.
- Do not describe Gemini photo comparison as trusted closure evidence.
- Do not describe Memory Bank as current operational state.
- Do not say "synthetic" more than once — repeating it sounds defensive. Once, early, is enough.
- Do not hide a live failure. Re-record the segment instead.
- Do not show private keys, tokens, or emails beyond service identities.
