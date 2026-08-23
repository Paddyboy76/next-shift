# Mission 15 — Four-Minute Demo + Public Polish Evidence

Date: 2026-08-23  
Project: `next-shift-506004`  
Region: `asia-southeast1`

## What was inspected

- Read `AGENTS.md` completely before implementation.
- Verified the active controller branch, HEAD, origin relationship, recent history, and existing dirty file. Work began on `codex/autonomous-final-attack` at `7e0f963acc03152724a77f48e5cebcfef40a6a27`; `docs/autonomy/STATUS.md` was already modified and was preserved.
- Fetched origin and confirmed the documented golden `origin/main` baseline remained `ce7baed79f07ecfb958225f37291d7949312e342`.
- Verified the configured GCP project is `next-shift-506004`.
- Inspected all deployed Cloud Run services and ready revisions, specialist Pub/Sub filters/push endpoints/DLQ settings, the Operations UI IAM policy, Agent Runtime/Gateway/Model Armor readiness evidence, and the existing public README, submission copy, architecture wording, demo script, Operations UI, and deployment script.
- Confirmed the Operations UI remains IAP protected: its only Cloud Run invoker is `service-963749706976@gcp-sa-iap.iam.gserviceaccount.com`.
- Attempted the required billing and Firestore database metadata reads. The runner is not permitted to read billing metadata, the Cloud Billing API is disabled to this principal, and the runner cannot list Firestore databases. No permissions or APIs were broadened for this polish phase. Authoritative workflow checks in the readiness gate remained available through the intended Operations/State Authority boundaries.

## What was changed

- Added an above-the-fold public product statement that makes the synthetic hospital demonstration and broader 24/7-enterprise applicability explicit.
- Added a compact `Interpret → Route → Execute → Prove → Verify` lifecycle guide. It is static explanatory copy, not a fabricated progress indicator.
- Added **Load six-team synthetic handover**. It only fills the editable text field with a prepared, synthetic, non-clinical six-owner scenario. The operator must review and explicitly submit it through the unchanged live Agent Runtime, Coverage Critic, State Authority, Pub/Sub, and specialist path.
- Added responsive styling for the proof chain and intake controls.
- Updated the four-minute demo script to use the prepared text safely and to state exactly what the helper does not bypass.
- Added public-demo regression tests covering all six operational signals, the synthetic boundary, prohibited public-demo terms, operator review, and governed-path wording.
- Deployed only `next-shift-operations`; no workflow backend or data mutation service was redeployed.

## What was deliberately not changed

- No clinical, medication, dietary, diagnostic, treatment, or clinical-decision workflow or public-demo content was added.
- No map, generated video/music, decorative model call, simulated telemetry, fabricated evidence, fake completion, or presentation-only integration was added.
- No authorization, IAP, IAM, evidence, inspector, verifier, Gateway, Model Armor, Firestore, Pub/Sub, Memory Bank, recovery, or state-transition control was weakened.
- The helper does not auto-submit, create work, skip critique, manufacture demo records, or claim that processing succeeded.
- No Git branch change, commit, push, merge, or pull request was performed.
- The pre-existing controller edit to `docs/autonomy/STATUS.md` was not modified.

## Exact validation performed

Local validation:

```text
source .venv/bin/activate
python -m compileall -q next_shift services workers tests
python -m pytest -q
129 passed, 49 subtests passed in 1.11s
git diff --check
```

The new tests verify that the prepared scenario contains all six operational signals, includes `synthetic`, excludes prohibited public-demo language, and visibly preserves review plus governed submission.

Deployment:

```text
bash deploy_spoken_handover.sh
Service next-shift-operations revision next-shift-operations-00026-rmj
100 percent traffic
SPOKEN_HANDOVER_DEPLOY_OK=1
```

Post-deployment readiness:

```text
READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh
PASS=178  WARN=2  FAIL=0
NEXT_SHIFT_READINESS=PASS
```

Both warnings are the explicitly allowed controller-owned conditions: the required non-main controller branch and the phase worktree changes. There were zero cloud/product warnings and zero failures.

Live Gateway and Model Armor behavioral proof:

```text
bash scripts/verify_gateway_model_armor_trace.sh
TRACE_ID=mission11-20260823T072018Z-17689
BENIGN_HTTP=200
BYPASS_HTTP=403
FAIL_OPEN=false
FILTER_ENFORCEMENT=ENABLED
INSPECTABLE_TRACE_ID=mission11-818198c8-1c76-46f4-9129-f474b6063140
GATEWAY_MODEL_ARMOR_TRACE_PROOF=PASS
```

The probe created no operational work.

## Relevant live GCP evidence

- Operations revision: `next-shift-operations-00026-rmj`
- Revision readiness: `Ready=True`, `Active=True`, `ContainerHealthy=True`
- Traffic: 100% to the latest revision
- Runtime identity: `ns-operations-ui@next-shift-506004.iam.gserviceaccount.com`
- Deployed image digest: `sha256:69833698a59c34aab64c83582a821e6dfdbee0d9b4c51897ce5c6a8b91d20fca`
- Operations access remains IAP-only; the controller runner received HTTP 401 when attempting direct token access, as expected from the IAM policy.
- The current readiness gate re-verified all 15 Cloud Run services used by the product, sole Firestore writer/viewer boundaries, specialist invoker isolation, six filtered specialist push subscriptions, Human Reach delivery/DLQ controls, stale-action denial, managed Agent Identity, Agent Gateway, Model Armor, controlled recovery evidence, and required APIs.

## Remaining risks

- Final recording still requires an authorized IAP end-user browser session. This runner could verify the deployed revision, image, identity, traffic, and health conditions but could not render the protected page through an end-user IAP session. Access was not weakened to obtain a screenshot.
- A clean-current-`main` readiness run belongs to the outer controller after it applies phase changes; this phase could only run with the explicit branch/dirty allowances mandated by the autonomous controller workflow.
- Billing and direct Firestore database-list metadata remain unreadable to the runner. This did not block the product readiness checks, which use intended service boundaries, but it should remain an explicit infrastructure-administration limitation.
- The one-click scenario removes typing risk but cannot guarantee Gemini output or downstream latency. The demo script correctly requires visible durable results before making success claims and permits already-inspected durable proof when a live step is delayed.

PHASE_RESULT: PASS
