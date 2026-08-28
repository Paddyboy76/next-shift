# Next Shift — continuous browser recording runbook

This is the action list for Claude or another browser-control agent during the final hackathon recording.

The browser run is one continuous take. Patrick narrates live. Do not create separate successful clips for later stitching.

If any required step fails, stop the take and report the failure. Fix the cause, reset the demo state, and record a new take from the beginning.

## Non-negotiable rules

1. Never edit the DOM, inject text, mock a response, or manufacture a state.
2. Never retry a failed action during the same take in a way that hides the failure.
3. Wait for visible state changes rather than assuming success after a fixed delay.
4. Move the cursor deliberately. Pause briefly before important clicks and after important state changes.
5. Do not open developer tools.
6. Do not expose tokens, private credentials, unrelated tabs, or non-synthetic hospital information.
7. Do not refresh during the asynchronous-progression proof unless the run has already failed.
8. The Google Chat card used at the beginning and end must be the same card.

## Environment

| Surface | Required state |
|---|---|
| Operations | Authenticated through IAP, top of page ready |
| Google Chat | `Next Shift – Facilities Ops`, fresh leaking-tap card in `ACTION_PENDING` |
| Cloud Shell | `/home/patrick/next-shift`, project `next-shift-506004` |
| Architecture | README architecture diagram already positioned |
| Viewport | 1920×1080, browser zoom 100% |

Keep the browser address bar visible so the `.run.app` deployment remains visible when Operations is on screen. Hide bookmarks and notifications.

Patrick speaks the handover paragraph live. Do not use fake-audio capture for the final take.

---

# Pre-flight — before recording

Stop and report if any check fails.

| # | Check | Required result |
|---|---|---|
| 1 | Operations loads without an IAP sign-in prompt | dashboard visible |
| 2 | Operations intro | `Interpret → Route → Execute → Prove → Verify` visible |
| 3 | Chat leaking-tap card | `Acknowledge / Blocked / Completed` present |
| 4 | Past carried work | at least 1 |
| 5 | Past shift snapshots | at least 1 |
| 6 | Improvement Advisor | Pattern, Why, Confidence, Scope populated |
| 7 | Cloud Shell project | `next-shift-506004` |
| 8 | `bash scripts/demo_proof_snapshot.sh` | exit 0, output readable |
| 9 | readiness log | `WARN=0`, `FAIL=0`, readiness/submission PASS |
| 10 | evidence assets | BEFORE and AFTER images ready |

The snapshot and Memory Bank preparation belong before recording, never during the take.

---

# Start recording — one continuous take

## 1. Opening refusal

1. Focus Google Chat on the fresh leaking-tap Facilities card.
2. Hold briefly so the card is readable.
3. Click **Completed** once.
4. Wait for `CLAIMED · UNVERIFIED` and the BEFORE / AFTER request.
5. Hold briefly.
6. Switch to Operations.

**Gate:** the card must not close. If it becomes closed/verified, stop the take.

## 2. Orientation and spoken handover

1. Show the top of Operations with the five-stage lifecycle line visible.
2. Move to the spoken-handover control.
3. Click **Record spoken handover**.
4. Patrick speaks live:

   > The printer on seven isn't printing and the light keeps blinking, the meeting room aircon is leaking again, there's water coming from something in the kitchen cupboard on eight, and the cupboard door itself is hanging loose.

5. Click stop when Patrick finishes.
6. Wait for the transcript.
7. Hold long enough to read the transcript. Do not edit it.
8. Click **Send to Next Shift**.
9. Wait for the named created/held outcomes.
10. Hold briefly on those outcomes.

**Gate:** created and held work must be named. If the result is ambiguous or missing, stop the take.

## 3. Asynchronous progression

1. Make the newly created cards visible.
2. Move the cursor to a neutral area.
3. Do not click, refresh, scroll, or hover over controls.
4. Wait until at least one job visibly progresses and reaches `ACTION_PENDING`.
5. Hold briefly after the transition.
6. Switch to Google Chat.

**Gate:** the proof depends on no operator interaction during progression. If a refresh is required, stop the take.

## 4. Frontline photo evidence

1. Return to the same leaking-tap card from the opening, still `CLAIMED · UNVERIFIED`.
2. Attach the synthetic BEFORE image.
3. Attach the synthetic AFTER image.
4. @mention Next Shift and send in the same thread.
5. Wait for Gemini 3.5's comparison reply.
6. Hold long enough to show that the images are supporting/visual evidence only.
7. Switch to Operations and open the leaking-tap issue.

**Gate:** Gemini's visual result must not imply it has closure authority. If it does, stop the take.

## 5. Trusted evidence and independent closure

This is the critical correction to the older runbook. Do not simply wait for Stage 5 after the image comparison.

1. In the issue drawer, show the supporting visual evidence entry.
2. Show that the issue is still waiting for trusted evidence.
3. Click **Record trusted evidence** once.
4. Wait for the trusted evidence action to complete.
5. Wait for the issue to move to Stage 5 / `VERIFYING`.
6. Hold on the evidence section so the trusted evidence entry is visibly distinct from supporting visual evidence.
7. Click **Run independent verifier** once.
8. Wait for `VERIFYING → CLOSED` / verified state.
9. Hold briefly on the closed state.
10. Switch back to Google Chat.
11. Wait for the same card to show green **Verified complete**.
12. Hold briefly.
13. Switch back to Operations and open the closed issue.

**Gates:**

- `Record trusted evidence` must be a separate action from the Chat photo evidence.
- The issue must enter `VERIFYING` before the verifier is run.
- The verifier must be the action that closes the job.
- The final green Chat card must be the same original card.

## 6. Governed record

1. With the closed issue open, pause at the top of the drawer.
2. Open / show the full audit trail.
3. Scroll down once, slowly, so evidence, technical audit and deeper history are visible.
4. Do not scroll back and forth.
5. Close the drawer.
6. Open **Past**.

## 7. Cross-shift continuity

1. Hold on carried work.
2. Expand **Shift snapshots** and hold on a populated snapshot.
3. Expand **Management recommendations** and hold on populated Pattern / Why / Confidence / Scope fields.
4. Switch to Cloud Shell.

**Gate:** do not show a zero snapshot count or blank advisor cards. If Past is empty, stop the take rather than recording a weak frame.

## 8. Live Google Cloud proof

1. Cloud Shell should already be in `/home/patrick/next-shift` with project `next-shift-506004`.
2. Run:

   ```bash
   bash scripts/demo_proof_snapshot.sh
   ```

3. Wait for the script to complete.
4. Hold the output still and readable. Do not scroll while Patrick points out the proof.
5. Show these items only:
   - Cloud Run revisions and service identities;
   - Gemini 3.5 demo paths;
   - Gateway / Model Armor allowed path and bypass denial;
   - stale Chat `DENY` with no mutation.
6. Switch to the README architecture diagram.

**Gate:** the command must exit 0. If it aborts, stop the take.

## 9. Architecture

1. Hold on the architecture diagram without scrolling.
2. Patrick explains Agent Runtime, Agent Registry, specialist separation, State Authority, Memory Bank, Agent Identity, Gateway and Model Armor.
3. Switch back to Cloud Shell.

## 10. Readiness and close

1. Run only the already-prepared log read:

   ```bash
   tail -20 /tmp/next-shift-submission-video.log
   ```

2. Hold on the final lines showing zero warnings/failures and PASS.
3. If time permits, switch once more to the green **Verified complete** Chat card for the final sentence.
4. End the recording only after Patrick finishes the closing line.

Do not rerun the full submission gate during the take.

---

# After recording

Preferred submission is the genuine continuous take as captured.

Do not remove waits, mistakes, or failures from inside the run and then present the result as one live execution.

If the successful continuous take is slightly over four minutes, a uniform speed-up of the entire recording is preferable to cuts or splicing. Disclose the speed-up. If speeding the whole run makes the narration hard to understand, record a faster clean take instead.

A normal start/end trim that does not alter the live run may be technically harmless, but the safest competition interpretation is to leave the proof run continuous and untouched.
