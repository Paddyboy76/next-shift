# Next Shift final demo script

## Goal

Record one continuous, approximately four-minute browser demo that shows a real Next Shift run on the deployed Google Cloud project.

Claude may drive the browser. Patrick narrates live. The recording must not rely on cuts, stitched successes, hidden retries, or a voiceover added afterwards to make the run look cleaner than it was.

If a take fails, stop and record a new take from the beginning. If a genuine continuous take is slightly too long, a uniform speed-up of the whole recording is preferable to trimming or splicing. If sped up, disclose it on screen or in the video description.

The browser runbook is `docs/demo-browser-runbook.md`.

## Tone

Sound like a person showing something they built, not somebody reading a judging rubric.

- Use short sentences.
- Say what the judge is looking at before naming technology.
- Avoid strings of product names unless they explain a design choice.
- Do not narrate every click.
- Leave a little silence when an important state changes.

## What the judge should understand

By the end, the judge should have seen that:

1. a messy handover becomes separate durable operational jobs;
2. work keeps moving after the person handing over is finished;
3. six specialists have bounded responsibilities and identities;
4. a human completion claim is not trusted as proof;
5. Gemini 3.5 supports speech, critique, and multimodal evidence without owning workflow truth;
6. trusted evidence and an independent verifier control closure;
7. carried work, shift snapshots, and Memory Bank preserve continuity without replacing current Firestore state;
8. stale or bypass actions are denied;
9. the backend is visibly running on Google Cloud;
10. the deployed stack passes the submission/readiness gate.

---

# One-take narration

The timestamps are targets, not editing points. Keep recording continuously.

## 0:00–0:10 — the refusal

**SCREEN** Google Chat, fresh Facilities leaking-tap card.

**ACTION** Click **Completed** once. Let `CLAIMED · UNVERIFIED` appear.

**SAY**

> "Here's a Facilities job. The worker says it's done. Next Shift doesn't close it — it marks it claimed, unverified. Saying something is finished isn't the same as proving it."

**WHY** Immediate live proof of the product's core trust boundary.

## 0:10–0:22 — orient the judge

**SCREEN** Operations Control, top of page with `Interpret → Route → Execute → Prove → Verify` visible.

**SAY**

> "This is the operations view. At shift change, unfinished work shouldn't turn into another note for the next person to chase."

**WHY** Frames the real-world friction before the technical explanation.

## 0:22–0:58 — messy speech becomes governed work

**ACTION** Click **Record spoken handover**. Patrick says the paragraph below live. Stop recording, wait for the transcript, then click **Send to Next Shift**.

**SPOKEN HANDOVER**

> "The printer on seven isn't printing and the light keeps blinking, the meeting room aircon is leaking again, there's water coming from something in the kitchen cupboard on eight, and the cupboard door itself is hanging loose."

**THEN SAY**

> "That's normal end-of-shift speech, not a form. Gemini 3.5 transcribes it and separates the work into distinct jobs. A second Gemini Coverage Critic checks the coverage before anything is persisted. The printer doesn't clearly belong to one of our six teams, so it can be held for review instead of guessed into the wrong queue."

**WHY** Demonstrates high-value autonomous delegation, ambiguity handling, and more than a chatbot response.

## 0:58–1:18 — the user is finished; the work is not

**SCREEN** Newly created cards.

**ACTION** Move the cursor away. Do not click or refresh. Let at least one job advance toward `ACTION_PENDING`.

**SAY**

> "Now I'm not touching anything. State Authority has persisted the jobs in Firestore, and owner-filtered Pub/Sub wakes the right Cloud Run specialist, each with its own identity and permissions. You can watch the work move from Interpret, to Route, to Execute. The person handing over is already done."

**WHY** This is the clearest proof of asynchronous fleet execution.

## 1:18–1:48 — frontline completion evidence

**SCREEN** Return to the same Google Chat thread from the opening.

**ACTION** Attach the synthetic BEFORE image, then AFTER image, @mention Next Shift, and send. Wait for Gemini's comparison reply.

**SAY**

> "Frontline teams don't need another operations console. Their work can reach them in Google Chat. Here the worker adds before and after pictures. Gemini can tell us whether the visible change supports the repair, but it still cannot close the job. The images are supporting evidence only."

**WHY** Demonstrates multimodal UX while preserving authority separation.

## 1:48–2:18 — trusted evidence and independent closure

**SCREEN** Operations, leaking-tap issue drawer.

**ACTION** Show the supporting visual evidence. Then click **Record trusted evidence**. Wait for the issue to move to Stage 5 / `VERIFYING`. Show that trusted evidence is a separate entry. Click **Run independent verifier**. Wait for `CLOSED`. Return to Google Chat and show the same card green as **Verified complete**.

**SAY**

> "Back here, the visual check is separate from trusted operational evidence. I'll record the trusted Facilities evidence now. That moves the job to Verify. An Evidence Inspector checks exactly what was submitted, and only the independent verifier can close it. Now it's closed, and the same Chat card turns green."

**WHY** This is the strongest architecture proof in the demo: claim, visual support, trusted evidence, inspection, and closure authority are separate.

## 2:18–2:38 — what the drawer means

**SCREEN** Closed issue drawer / full audit trail.

**ACTION** Pause at the top, then scroll once slowly enough to show the deeper sections.

**SAY**

> "If somebody needs to know what happened, the drawer starts with what matters: where the job is now, what just happened, and what it's waiting for. The full history, evidence and technical audit are underneath."

**WHY** Demonstrates operational clarity, auditability, and production-minded UX.

## 2:38–2:58 — what survives the shift

**SCREEN** Past panel: carried work, shift snapshots, populated Improvement Advisor.

**SAY**

> "And this is the bit that makes it a shift system rather than a task list. Carried work survives the shift boundary. Snapshots preserve what crossed a handover. Firestore stays the current truth; Memory Bank looks across earlier shifts for patterns and gives management advice, but that advice can't change live work."

**WHY** Demonstrates cross-shift continuity and persistent advisory context.

**GATE** Only show this if carried work is present, at least one real snapshot exists, and advisor cards have populated Pattern / Why / Confidence / Scope fields. Do not show an empty Past panel.

## 2:58–3:26 — live Google Cloud proof

**SCREEN** Cloud Shell, large readable font.

**ACTION** Run `bash scripts/demo_proof_snapshot.sh`. Keep the output still.

**SAY**

> "These are live reads from the deployed Google Cloud project. Separate Cloud Run services and identities, Gemini 3.5 on the demo paths, Agent Gateway and Model Armor allowing the proper path and blocking a bypass, and a stale Chat action being denied instead of changing already-closed work."

**WHY** Gives visible backend proof and demonstrates security by showing correct denial, not only success.

## 3:26–3:47 — architecture without the shopping list

**SCREEN** README architecture diagram.

**SAY**

> "The intake agent runs on Vertex AI Agent Runtime and is catalogued in Agent Registry. The specialists are split by responsibility, State Authority is the only workflow writer, and Memory Bank is advisory. Agent Identity, Gateway and Model Armor make those boundaries enforceable rather than just labels on a diagram."

**WHY** Explains why the Google platform components exist instead of merely naming them.

## 3:47–4:00 — readiness and close

**SCREEN** Pre-run readiness result showing `WARN=0`, `FAIL=0`, `NEXT_SHIFT_READINESS=PASS`, then return to the green Chat card if time allows.

**SAY**

> "Before this take, this deployed stack passed the submission gate with zero warnings and zero failures. The hospital data here is synthetic; the same problem exists anywhere shifts end before the work does. The handover ends. The work doesn't."

**WHY** Ends with reproducibility/readiness and generalizes the product beyond the demo domain.

---

# Pre-recording preparation

Run these before the take, not during it.

```bash
cd /home/patrick/next-shift
git checkout main
git pull --ff-only
source /home/patrick/next-shift/.venv/bin/activate

gcloud config set project next-shift-506004

python scripts/seed_shift_snapshot.py --outgoing "Night shift" --incoming "Day shift"
python scripts/seed_shift_snapshot.py --list

curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud run services describe next-shift-memory-sync \
      --project=next-shift-506004 \
      --region=asia-southeast1 \
      --format='value(status.url)')/v1/sync" | head -40

bash scripts/demo_proof_snapshot.sh
bash scripts/verify_submission.sh | tee /tmp/next-shift-submission-video.log
tail -20 /tmp/next-shift-submission-video.log
```

Before pressing Record, confirm:

- Operations is already authenticated through IAP;
- a fresh Facilities leaking-tap card is in `ACTION_PENDING` in Google Chat;
- BEFORE and AFTER images are ready to attach;
- Past shows carried work, at least one snapshot, and populated advisor fields;
- Cloud Shell is already in `/home/patrick/next-shift`, project `next-shift-506004`;
- the architecture diagram is open in its own tab;
- no private tokens, unrelated tabs, notifications, or real hospital information are visible.

## Recording method

Recommended setup:

- Monitor 1: the browser window being recorded.
- Monitor 2: this script and Claude's browser-control chat, not included in the capture.
- Claude drives the browser using `docs/demo-browser-runbook.md`.
- Patrick speaks the narration live and also speaks the handover paragraph when Claude starts the microphone capture.
- Record screen + microphone together in OBS or an equivalent recorder.
- Do not add a replacement voiceover later.
- If the take fails, start a fresh take from the beginning.
- If the whole genuine take must be sped up slightly to stay under four minutes, apply one uniform speed-up to the entire recording and disclose it.
