# Mission 09 — Coverage Critic + Evidence Inspector

Audit date: 2026-08-23 UTC  
Repository: `Paddyboy76/next-shift`  
Project: `next-shift-506004` (`963749706976`)  
Region: `asia-southeast1`

## What was inspected

- Read all 809 lines of `AGENTS.md` before architectural changes.
- Fetched origin and verified the controller branch remained `codex/autonomous-final-attack` at `4179d79e05bfe592f49ce8930d95696e7f4f05cb`; preserved the controller-owned `docs/autonomy/STATUS.md` edit and did not change branches or perform Git publishing actions.
- Inspected the typed Agent Runtime intake contract, Operations intake orchestration, State Authority intake validation and policy, evidence envelope and closure transaction, verifier runtime, lifecycle trace, deployment scripts and regressions.
- Inspected live Cloud Run revisions, runtime identities, invoker IAM, Pub/Sub topics, project IAM, enabled platform APIs and readiness state.
- Attempted Firestore database metadata and billing inspection. The runner cannot read Firestore database metadata, and Cloud Billing API is disabled/inaccessible to this identity; neither limitation prevents the deployed application identities from using authoritative Firestore.

## What was changed

- Deployed a dedicated Coverage Critic runtime under `ns-coverage-critic`. It uses a separate Gemini call to compare raw handover text with typed intake proposals for missed, duplicated, conflated, misrouted or uncertain operational work.
- The critic has no direct Firestore role and no issue-mutation API. It can only submit a bounded review to State Authority, which persists the message hash, findings, decision, model, principal and source reference in `coverage_reviews`.
- Operations requires a durable critic `PASS` before proposal persistence. A disagreement returns `human_review_required`, creates no issue, dispatches no event and exposes the durable findings to the operator.
- Deployed a deterministic Evidence Inspector runtime under the separate `ns-evidence-inspector` identity. It independently evaluates evidence issuer, provenance, observation mode, timestamps, capability, source, subject, details and coverage.
- Added narrow State Authority inspection-context and inspection-record capabilities. Inspections persist in `evidence_inspections`; the inspector has no direct Firestore role.
- Added a hard closure gate: State Authority refuses verifier closure unless a `PASS` inspection exists for the exact issue and evidence ID. The verifier invokes the inspector before requesting closure.
- Added focused adversarial tests for accepted provenance, specialist claims and wrong-capability evidence.
- Extended `verify_readiness.sh` so both runtimes, identities, environment bindings and invoker boundaries are now production-readiness requirements.

## What was deliberately not changed

- Firestore remains authoritative; neither critic nor inspector received a direct Firestore role.
- Critics do not change issue state, routing policy, evidence or verifier authority.
- Deterministic routing and both existing verifier and State Authority evidence checks remain. The inspector is an additional independent gate, not a replacement.
- No Gemma call was added merely to increase model count. Semantic coverage uses Gemini; evidence policy remains deterministic because its evidence contracts are explicit and auditable.
- No clinical workflow, proprietary data, fabricated telemetry or presentation mock was added.
- No broad runner impersonation or permanent acceptance-only IAM grant was added.

## Exact validation performed

- `.venv/bin/python -m py_compile services/state_authority/*.py services/coverage_critic_runtime/main.py services/evidence_inspector_runtime/main.py services/operations_ui/*.py services/verifier_runtime/main.py`: success.
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`: 119 tests passed.
- `git diff --check`: success.
- `bash ./deploy_critic_inspector.sh`: `CRITIC_INSPECTOR_DEPLOY_OK=1`.
- Ran a real authenticated Coverage Critic PASS and disagreement through a short-lived Cloud Run Job using the existing Operations identity.
- Ran a real Facilities issue from State Authority intake through filtered Pub/Sub delivery and the specialist workflow to `ACTION_PENDING`.
- Ran trusted evidence and independent verification through a short-lived Cloud Run Job using the existing Operations caller identity. The verifier invoked the separately authenticated Evidence Inspector before closure.
- Queried correlated State Authority authorization logs for intake, specialist transitions, evidence recording, inspection context, inspection recording and final closure.
- Queried error-severity logs for the five affected services after deployment; none were returned.
- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash ./verify_readiness.sh`: `PASS=169 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`. The warnings are exactly the authorized controller branch and dirty phase worktree.
- Deleted all three temporary acceptance Job definitions after inspection. Their execution history and durable product records remain auditable.

## Relevant live GCP evidence

Deployed revisions serving 100% traffic:

- State Authority: `next-shift-state-authority-00021-wm4`
- Coverage Critic: `next-shift-coverage-critic-00001-gtt`
- Evidence Inspector: `next-shift-evidence-inspector-00001-g68`
- verifier: `next-shift-verifier-00003-69p`
- Operations: `next-shift-operations-00017-tj2`

Least-privilege runtime chain:

- Operations is the sole invoker of Coverage Critic.
- Coverage Critic can invoke State Authority only through its bounded `coverage.review` capability.
- verifier is the sole invoker of Evidence Inspector.
- Evidence Inspector can invoke State Authority only through `evidence_inspection.read` and `evidence_inspection.record`.
- State Authority remains the sole Next Shift Firestore writer; Operations remains the only Next Shift Firestore viewer.

Live critic records:

- `JOxtR6k5I1m5d2eP9AA4`: `PASS`, no findings, model `gemini-3.5-flash`, source `mission09-live-pass`.
- `wHXDz2S0SxQCi58goBqH`: `REVIEW_REQUIRED`, durable `MISSED` finding with suggested owner `AssetLogistics` for a wheelchair omitted from the proposal. No issue was created for the disagreement scenario.

Live closure proof:

- Issue: `fA49pejqLiqrK6QQl6Wv`
- Intake event: `097fd763-8768-47e1-8230-c6a1dbe01273`
- Specialist `ACTION_PENDING` transition: `RStChalOiwpfxiv6Ij7J`
- Trusted evidence: `yNbtfFxsUaO6p0MldEUZ`
- Evidence transition: `PtDfwNXnno1oNDRlxJ5a`
- Evidence inspection: `flY6Z7Ul2bCy8cp6wXO9`, decision `PASS`
- Closure transition: `31Exoe07Lzi1Z6YysIwo`
- Final state: `CLOSED`

Correlated authorization records prove that `ns-worker-facilities` progressed work only to `ACTION_PENDING`, `ns-trusted-evidence` recorded independently sourced synthetic evidence, `ns-evidence-inspector` read and approved the exact evidence, and `ns-verifier` requested the final closure. State Authority enforced every mutation.

## Remaining risks

- The Coverage Critic is an LLM-based semantic safeguard, so disagreements can include model variance even at temperature zero. Its fail-closed orchestration, bounded output validation, durable findings and no-mutation design contain that risk; deterministic routing remains authoritative.
- The evidence inspector is deterministic rather than a second model. This is intentional: explicit capability contracts are stronger and more inspectable than adding a decorative model call.
- The runner cannot directly query Firestore database metadata. Durable records were inspected through authenticated application responses and correlated State Authority audit events rather than broadening runner access.
- One initial acceptance Job under the trusted-evidence identity was denied at the Cloud Run edge because only Operations is authorized to invoke that service. It made no application or Firestore mutation. The successful run used the already authorized Operations caller and preserved the trusted-evidence service's separate recording identity.

The phase goal is satisfied: intake coverage now has an independent, durable, fail-closed critique step; evidence closure now requires a separate inspection identity and exact-evidence PASS; disagreements are visible; deterministic routing, policy and verifier authority remain intact; and the complete deployed path is proven with authoritative records.

PHASE_RESULT: PASS
