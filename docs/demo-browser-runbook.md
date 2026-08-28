# Next Shift — browser agent recording runbook

This is the literal action list for an agent driving a browser while the screen is captured. It pairs with `docs/demo-script.md`, which holds the narration recorded separately afterwards.

**The agent performs actions only. It never types, speaks, or overlays narration.**

---

## Rules for the agent

1. **Never fabricate a state.** Do not edit the DOM, inject text, mock a response, or use developer tools to make anything appear. Every frame must be a state the deployed system actually produced.
2. **Never retry inside a segment.** If a step fails or times out, stop, report what failed, and wait for a human decision. The segment is re-recorded from its first action — a retry mid-segment produces footage that implies a first-time success that did not happen.
3. **Wait on visible state, never on a fixed sleep**, except where a HOLD is specified. A HOLD is deliberate on-screen dwell time so a human can read the frame; it is not a workaround for a slow request.
4. **Move deliberately.** Pause about one second before each click and about two seconds after any state change. Automated cursors jump instantly, which makes state changes unreadable on video.
5. **Do not resize, scroll, or open developer tools** unless a step says to.
6. **Report, don't improvise.** If an element is missing or a label differs from this document, stop and report it. Do not hunt for a substitute control.

## Environment

| | |
|---|---|
| Operations | `https://next-shift-operations-mycnigy7dq-as.a.run.app` (IAP — sign in **before** capture starts) |
| Google Chat | space **Next Shift – Facilities Ops** |
| Cloud Shell | project pinned to `next-shift-506004` |
| Viewport | 1920×1080, browser zoom 100%, Cloud Shell font large enough to read on a laptop |

Hide bookmarks, notifications, and any tab whose title is not part of the demo.

### Microphone for the spoken handover

The intake uses `navigator.mediaDevices.getUserMedia`, so a browser agent cannot speak into it. Launch Chrome with a fake audio device backed by the rehearsed paragraph:

```bash
google-chrome \
  --use-fake-ui-for-media-stream \
  --use-fake-device-for-media-stream \
  --use-file-for-fake-audio-capture=/absolute/path/handover.wav%noloop \
  --window-size=1920,1080
```

`handover.wav` must be **16-bit PCM WAV**; other formats are silently ignored and you will capture a recording of silence. Verify with a throwaway run before capture:

```bash
ffmpeg -i handover.m4a -ar 48000 -ac 1 -c:a pcm_s16le handover.wav
ffprobe handover.wav      # expect pcm_s16le
```

If the fake device cannot be made to work, a human speaks this one step live and the agent resumes at Segment 3.

---

## Pre-flight — run before any capture

Stop and report if any check fails. These gate segments that will otherwise record badly.

| # | Check | Required result |
|---|---|---|
| 1 | Operations loads past IAP without a sign-in prompt | Dashboard visible |
| 2 | `Interpret → Route → Execute → Prove → Verify` visible in the intro | Present |
| 3 | Chat space has a fresh Facilities leaking-tap card in `ACTION_PENDING` | **Acknowledge / Blocked / Completed** all present |
| 4 | Open **Past** → carried work count | **≥ 1** |
| 5 | Open **Past** → shift snapshots count | **≥ 1** (see below) |
| 6 | Open **Past** → advisor cards | Pattern, Why, Confidence, Scope all **populated** |
| 7 | Cloud Shell: `gcloud config get-value project` | `next-shift-506004` |
| 8 | Cloud Shell: `bash scripts/demo_proof_snapshot.sh` completes | exit 0, output readable |

Checks 5 and 6 are the two that historically fail. Fixes:

```bash
# Check 5 — nothing in the deployed services writes shift snapshots.
python scripts/seed_shift_snapshot.py --outgoing "Night shift" --incoming "Day shift"

# Check 6 — advisor cards render blank when the memory service does not answer.
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud run services describe next-shift-memory-sync --region asia-southeast1 \
     --format='value(status.url)')/v1/sync" | head -40
```

If check 5 or 6 still fails, **report it and skip Segment 6.** `docs/demo-script.md` defines the fallback narration for that case. Recording an empty Past panel is worse than omitting it.

---

# Segments

Each segment is one continuous capture. Cuts between segments are ordinary edits; inside a segment, only waiting may be removed.

## Segment 1 — the refusal (script 0:00–0:08)

*Capture ~25 s. Most of it is trimmed; only the click and the state change survive.*

1. Focus the Google Chat tab on the Facilities leaking-tap card. HOLD 3 s.
2. Click **Completed**. Click once.
3. Wait for the card to show `CLAIMED · UNVERIFIED` and request BEFORE and AFTER photos.
4. HOLD 5 s on that state.

**Gate** The card must **not** show closed or verified. If it closed, the issue was not in `ACTION_PENDING` — stop and report.

## Segment 2 — orientation (script 0:08–0:18)

*Capture ~15 s.*

1. Switch to the Operations tab, scrolled to the top.
2. No interaction. HOLD 12 s with the five-stage line visible.

## Segment 3 — spoken handover (script 0:18–0:56)

*Capture 60–90 s. Model latency is trimmed later.*

1. Click into the Operations intake panel. HOLD 2 s.
2. Click **Record spoken handover**.
3. Let the fake audio device play the full paragraph — roughly 14 s. Do not click during playback.
4. Click stop.
5. Wait for the transcript to appear. HOLD 4 s so it is readable. **Do not edit the transcript**, including obvious speech artefacts — imperfect input surviving the pipeline is the point.
6. Click **Send to Next Shift**.
7. Wait for the intake outcome. HOLD 6 s on the named created and held items.

**Gate** The outcome must **name** each created and held item. If items are created but not named, stop and report — nothing may appear to vanish between the model and State Authority.

## Segment 4 — asynchronous progression (script 0:56–1:16)

*Capture 40–60 s. This is the segment where a visible speed-up is acceptable.*

1. Ensure the new job cards are visible.
2. Move the cursor off the cards, to a neutral area. **Do not click, scroll, hover, or refresh.**
3. HOLD, untouched, until at least one card visibly advances and one reaches `ACTION_PENDING`.
4. HOLD 5 s after the last transition.

**Gate** No interaction at all during step 3. The whole value of this segment is that nothing was driving it. If a manual refresh is unavoidable, report it — the narration must then change.

## Segment 5 — claim, photos, and closure (script 1:16–2:18)

*Capture 90–120 s.*

1. Switch to Google Chat, the same card, still `CLAIMED · UNVERIFIED`. HOLD 3 s.
2. Attach the synthetic **BEFORE** image, then the **AFTER** image, in that order, in the same thread.
3. @mention Next Shift and send.
4. Wait for the Gemini 3.5 comparison reply. HOLD 6 s.
5. Switch to Operations. Open the leaking-tap issue.
6. Wait for **Stage 5 · Verify**. HOLD 3 s on the trusted evidence entry, separate from the visual support entry.
7. Run the **Independent Verifier** action.
8. Wait for `VERIFYING → CLOSED`. HOLD 4 s.
9. Switch to Google Chat. Wait for the same card to refresh to green **Verified complete**. HOLD 5 s.

**Gates**
- Step 4: the reply must mark the images supporting/visual evidence only. If it reads as closure authority, stop and report.
- Step 6: visual support and trusted evidence must be **visibly distinct entries**. That distinction is the architecture argument.
- Step 9: the card must be the **same** card from Segment 1, refreshed — not a new message.

## Segment 6 — the record and what survives the shift (script 2:18–2:58)

*Capture 50–70 s. Skip entirely if pre-flight checks 5 or 6 failed.*

1. With the closed issue open, open the **full audit trail** drawer. HOLD 5 s at the top.
2. Scroll down slowly, once, over about 6 s. Do not scroll back up.
3. Close the drawer.
4. Click **Past**.
5. HOLD 5 s on carried work.
6. Expand **Shift snapshots**. HOLD 4 s.
7. Expand **Management recommendations**. HOLD 5 s.

**Gate** Steps 6 and 7 must show populated content. A zero count or a blank card must not be recorded — stop and report instead.

## Segment 7 — live cloud proof and readiness (script 2:58–4:00)

*Capture 60–90 s.*

1. Switch to Cloud Shell. HOLD 2 s.
2. Run:
   ```bash
   bash scripts/demo_proof_snapshot.sh
   ```
3. Wait for completion. HOLD 10 s on the output, still — no scrolling while it is being read.
4. Run:
   ```bash
   tail -8 /tmp/next-shift-demo-readiness.log
   ```
5. HOLD 6 s with `WARN=0`, `FAIL=0`, `NEXT_SHIFT_READINESS=PASS` visible.
6. Switch to the README architecture diagram. HOLD 8 s. No scrolling.
7. Switch to Google Chat, green **Verified complete** card. HOLD 5 s. End capture.

**Gate** Step 2 must exit 0. It runs `set -euo pipefail` and aborts if the active project is wrong — if it aborts, fix the project and re-record the segment from step 1.

---

## Handing off to the edit

Deliver per segment: the raw capture, its start and end timestamps, and any step that needed a gate decision.

Editing order:
1. Assemble segments 1–7 in order.
2. Trim waiting only. Keep every HOLD — they exist so the voiceover has somewhere to sit.
3. Target 240 s. If long, cut from Segments 6 and 7 first; never from 3 or 4.
4. Record voiceover against the picture cut using the exact words in `docs/demo-script.md`.
5. Final check: play it once muted. If the story is unclear without narration, the picture cut is wrong — narration cannot rescue it.
