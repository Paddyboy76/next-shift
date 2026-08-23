# Mission 14 — Spoken Handover Evidence

## What was inspected

- Read `AGENTS.md` in full and reviewed the Mission 14 contract before changes.
- Verified Git state: controller branch `codex/autonomous-final-attack`, head `1198adb2aa0201f6ef9a38e5b2297a535ca3ad5d`, `origin/main` at the requested golden baseline `ce7baed79f07ecfb958225f37291d7949312e342`, with only the controller-owned `docs/autonomy/STATUS.md` modification present initially. The branch was not changed.
- Verified active GCP project `next-shift-506004`, Cloud Run services/revisions, service identities, invoker IAM, Pub/Sub push routing, Agent Runtime/Identity, Agent Gateway, Model Armor, required APIs, Registry/memory/recovery assertions, and production readiness.
- Inspected the existing IAP-protected Operations intake, managed Agent Runtime call, independent Coverage Critic, State Authority persistence boundary, frontend, deployment path, and test conventions.
- Billing linkage could not be re-read: the Cloud Billing API is disabled for this runner consumer and the runner lacks billing access. No API or permission was broadened merely to satisfy that read.

## Pre-change green proof

Before implementation:

- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh`
- Result: `PASS=177 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`.
- The two warnings were exactly the controller-authorized non-main branch and dirty-worktree conditions. There were no product, security, cloud, evidence, or integration failures.

## What changed

- Added optional browser microphone capture to Operations Control. Recording is explicit; the operator stops it and receives editable text before any work can be created.
- Added `/api/spoken-handover/transcribe`, accepting only allowlisted audio MIME types and at most 4 MiB.
- Added real Vertex AI Gemini `gemini-2.5-flash` multimodal transcription with a strict response schema, temperature zero, language and uncertain-segment reporting, and no task creation during transcription.
- Added a metadata-only audit receipt containing provider, model, MIME type, byte count, audio SHA-256, transcript SHA-256, unique audit reference, `audio_persisted=false`, and `operator_review_required=true`. Cloud Logging receives these fields without prompt, transcript, or audio content.
- Bound an unedited Gemini transcript receipt into the durable issue `source_reference`. If the operator edits the transcript, the receipt is cleared and the existing text path remains available. A mismatched receipt fails visibly.
- Preserved the governed execution path: reviewed transcript → existing `/api/intake` → Agent Gateway and fail-closed Model Armor → managed ADK Agent Runtime → independent Coverage Critic → State Authority → Firestore/Pub/Sub. Audio transcription cannot write Firestore, dispatch work, bypass coverage review, change authority, record evidence, or close an issue.
- Added focused tests, a reproducible `deploy_spoken_handover.sh`, a live readiness assertion for the configured Gemini model, and concise README/demo guidance that treats speech as optional.

## What was deliberately not changed

- No speech-to-work shortcut was added. An operator must review the transcript and explicitly submit it.
- No audio payload is persisted and no transcript content is written to Cloud Logging.
- Firestore authority, canonical states, specialist IAM, Pub/Sub routing, trusted-evidence rules, independent inspection/verification, clinical boundary, Gateway, and Model Armor policies were not weakened or replaced.
- No clinical workflow or public clinical demo content was added.
- Spoken input is optional in the four-minute demo; the stable text fallback remains the default recovery path.
- No branch change, commit, push, merge, or pull request was performed.

## Exact validation performed

- Installed `espeak-ng` only in the ephemeral runner environment to create a fully synthetic WAV; it is not a repository or production dependency.
- Real Vertex AI call using the project credentials and `gemini-2.5-flash`:
  - audio: `Synthetic evening operations handover. The loading bay door is stuck and facilities must inspect it.`
  - result: correct English transcript, zero uncertain segments, hashes present, `audio_persisted=false`, `operator_review_required=true`.
- A first real call exposed malformed free-form JSON. Added a Gemini response schema and repeated the call successfully; the invalid response was not presented as success.
- Real multipart Flask endpoint test with the same synthetic WAV: HTTP 200 with the correct transcript and full audit receipt.
- `.venv/bin/python -m pytest -q tests/test_spoken_handover.py`: `3 passed`.
- `.venv/bin/python -m pytest -q`: `127 passed, 49 subtests passed`.
- `.venv/bin/python -m compileall -q services/operations_ui`: passed.
- `bash -n deploy_spoken_handover.sh verify_readiness.sh`: passed.
- `git diff --check`: passed.
- JavaScript could not be checked with Node because Node is not installed in the runner. The browser code uses standard `MediaRecorder`, `FormData`, and existing fetch/error helpers, with an explicit capability fallback.
- Post-deployment unauthenticated request returned HTTP 302 to Google IAP, confirming the operator boundary remains protected.
- Latest revision error query (`severity>=ERROR`) returned `[]`.
- Final `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh`: `PASS=178 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`. The only warnings remain the two authorized controller repository conditions.

## Relevant live GCP evidence

- Production service: `next-shift-operations`.
- Latest created and ready revision: `next-shift-operations-00025-wqd`.
- Traffic: 100% to latest revision.
- Runtime identity: `ns-operations-ui@next-shift-506004.iam.gserviceaccount.com`.
- Live model binding: `SPOKEN_HANDOVER_MODEL=gemini-2.5-flash`.
- Operations invoker policy remains restricted to `service-963749706976@gcp-sa-iap.iam.gserviceaccount.com`.
- The Operations identity already has `roles/aiplatform.user`; no IAM grant was added.
- The final readiness gate reconfirmed the Agent Runtime/Identity, Gateway/Model Armor binding, State Authority sole-writer boundary, independent critic/inspector/verifier, specialist invoker isolation, owner-filtered push subscriptions, retry/DLQ controls, and sanctioned recovery proof.

## Remaining risks

- Microphone permission, browser codec support, background noise, and speech clarity remain environmental. The UI fails visibly and retains text intake.
- The runner is intentionally not an Operations invoker and cannot pass the human IAP session, so it did not weaken IAP to invoke the deployed private endpoint directly. The same endpoint code was exercised with a real multipart request and real Vertex call before the exact source was deployed; production revision/configuration/readiness were then inspected.
- The transcription audit event becomes visible in production Cloud Logging on the first authenticated operator recording; no fake production event was inserted solely to create telemetry.
- Operators must review uncertainty and transcription accuracy. Editing intentionally discards the speech receipt and uses ordinary text provenance.

PHASE_RESULT: PASS
