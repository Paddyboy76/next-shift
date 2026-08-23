# Mission 13 — Reproducibility + Submission Truth

Date: 2026-08-23 UTC

## What was inspected

- Read all 809 lines of `AGENTS.md` before changing repository files.
- Verified the controller branch remained `codex/autonomous-final-attack` at `fa28a7b5181ca12013e8188d1ba403529c823b49`; `origin/main` remained the golden `ce7baed79f07ecfb958225f37291d7949312e342`.
- Preserved the pre-existing controller-owned `docs/autonomy/STATUS.md` change marking Mission 13 running.
- Inspected README, architecture, submission copy, demo script, phase contracts, prior phase evidence, readiness implementation, deployment scripts, service source, tests, and public wording.
- Verified active project `next-shift-506004`, Cloud Run services/revisions/identities, Pub/Sub topics and production readiness.
- Re-read live Agent Registry entries and reran the real Agent Runtime / Agent Gateway / Model Armor behavioral verifier.
- Billing linkage could not be re-read because the Cloud Billing API is disabled for the runner consumer. Firestore database metadata could not be read by this runner identity. These limitations were recorded rather than changing APIs or permissions for a documentation phase; service-specific production checks and State Authority readiness remained available.

## What changed

- Reframed README and submission copy around the general 24/7 enterprise handover product, with the synthetic non-clinical hospital operations environment explicitly identified as the demonstration domain.
- Replaced the stale architecture description with a current authority map covering the independent Coverage Critic, State Authority, specialist fleet, Human Reach, external synthetic evidence, exact-evidence Inspector, independent Verifier, Recovery Planner, Registry, Memory Bank, and truthful observability boundary.
- Made evidence independence unmistakable: human/specialist claim, trusted evidence, exact-evidence inspection, and independent closure are separate identities and acts.
- Added `docs/deployment.md` with prerequisites, preflight, scoped deployment units, dependency order, shared-service environment warnings, and post-deployment proof. It deliberately does not advertise a zero-touch new-project bootstrap.
- Added `docs/verification.md` with exact local checks, read-only production readiness, controlled Gateway/Model Armor behavior, mutating-acceptance boundaries, and a claim-to-proof map for external reviewers.
- Updated submission wording to explain why the system is agentic: bounded reasoning initiates work that persists and continues asynchronously after the initiating interaction, while models remain outside the workflow-truth boundary.
- Updated the four-minute demo to expose intake critique, identity/capability traces, unverified completion claims, evidence inspection, controlled recovery, Registry/Memory provenance, and live Gateway/Model Armor proof without expanding clinical demo content.
- Removed the obsolete claim that the current readiness count is permanently 159. Documentation now distinguishes the 159-check golden baseline from the expanding current gate and defines submission success as zero warnings/failures plus `NEXT_SHIFT_READINESS=PASS` on clean current `main`.
- Documented the observability truth: real Cloud Run trace/span fields and durable governed lifecycle correlation are available; native application OTLP spans are not claimed.

## What was deliberately not changed

- No application code, workflow contract, state transition, IAM policy, runtime revision, evidence rule, verifier authority, specialist permission, or Firestore data was changed.
- No feature was added solely for submission presentation and no unavailable platform capability was claimed.
- No native OTLP trace, external integration, evidence, completion, or deployment state was fabricated.
- No cloud API was enabled to work around the runner's billing/metadata read limits.
- The live synthetic security verifier executed its existing private proof job and emitted its normal inspectable decision record; it did not call State Authority or create operational work.
- No Git branch change, commit, push, merge, or pull request was performed.

## Exact validation performed

- `python -m compileall -q next_shift services workers tests`: passed.
- `python -m pytest -q`: `124 passed, 49 subtests passed`.
- `bash -n` across readiness, deployment, and Gateway proof shell scripts: passed.
- `git diff --check`: passed.
- Public-copy restricted-source phrase audit across README and non-autonomy docs: no matches.
- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh`: `PASS=177 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`. The two warnings were exactly the authorized controller branch and dirty worktree exceptions; all 177 cloud/platform/product checks passed.
- `bash scripts/verify_gateway_model_armor_trace.sh`: `GATEWAY_MODEL_ARMOR_TRACE_PROOF=PASS`; benign HTTP 200; instruction-bypass HTTP 403; managed Agent Identity present; `FAIL_OPEN=false`; filter enforcement enabled; inspectable trace present.

## Relevant live GCP evidence

- Fifteen Cloud Run services were ready, serving 100% latest traffic under their expected identities. Key current revisions were State Authority `next-shift-state-authority-00023-66k`, Operations `next-shift-operations-00023-gzg`, Recovery Planner `next-shift-recovery-planner-00001-r6m`, Coverage Critic `next-shift-coverage-critic-00001-gtt`, Evidence Inspector `next-shift-evidence-inspector-00001-g68`, trusted evidence `next-shift-trusted-evidence-00002-mlc`, and verifier `next-shift-verifier-00003-69p`.
- Live readiness confirmed State Authority remained the sole Next Shift Firestore writer and Operations remained the only Next Shift direct Firestore viewer.
- Live readiness confirmed all specialist invoker boundaries and owner-filtered Pub/Sub OIDC/retry/DLQ paths.
- Agent Registry listed the real `Next Shift` agent UID `agentregistry-00000000-0000-0000-1ed0-77d6ac7e1fad`.
- Agent Runtime `8140616966286082048` remained readable with managed Agent Identity and the client-to-agent gateway binding.
- The final controlled proof used request trace `mission11-20260823T065514Z-28478`; the managed path returned benign 200 and bypass 403. Private Cloud Run Job execution `next-shift-gateway-trace-proof-h5m2k` completed successfully, and logging retained inspectable trace `mission11-f37a8937-fbfc-47a0-ade2-00dbc90dd241`.
- Readiness found sanctioned recovery proof `LBKZFwvyKFeM5jb8EZFz` and stale Human Reach denial proof `SqvPMquPLWalAYd69bgk`.

## Remaining risks

- Final submission freeze must rerun readiness on clean current `main`; this phase was required to remain on the controller branch and could therefore prove 177 production checks with two explicit repository-state warnings, not a clean-main zero-warning summary.
- Deployment remains a sequence of scoped scripts for the established project, not a zero-touch bootstrap. Shared-service environment variables require inspection when multiple deployment units are composed.
- Native application OTLP export remains unavailable at the current permission boundary. Documentation now states this limitation and relies only on real Cloud Run telemetry plus durable lifecycle correlation.
- Billing linkage and Firestore database metadata could not be independently refreshed by the runner, although serving resources, IAM authority, runtime integrations, and the complete readiness gate were verified.

The repository and submission materials now present a current, reproducible, claim-to-proof account of the deployed product without overstating platform, deployment, observability, or completion evidence.

PHASE_RESULT: PASS
