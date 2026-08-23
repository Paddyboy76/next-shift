# Mission 12 — Controlled Recovery Planner

## What was inspected

- Read `AGENTS.md` completely and verified the current branch, worktree, local/remote refs and recent history before editing.
- Verified active project `next-shift-506004`, active runner identity, Cloud Run services/revisions, Pub/Sub topics/subscriptions, project IAM, Agent Runtime access, Agent Gateway, Model Armor and production readiness.
- Inspected canonical states, State Authority policy/transition/evidence contracts, recoverable verifier rejection, Operations data and lifecycle trace paths, deployment scripts and readiness checks.
- Direct billing and Firestore database-description calls were unavailable to the runner because the Cloud Billing API is disabled for this consumer and the runner lacks Firestore database metadata permission. Service-specific live checks and the deployed State Authority path remained available.

## What was changed

- Added a deployed `next-shift-recovery-planner` Cloud Run service. It runs under the existing read/advice-only `ns-coverage-critic` identity, which has no Firestore data role and remains distinct from the Operations, trusted-evidence and verifier identities.
- Added State Authority capabilities `recovery.read`, `recovery.plan` and `recovery.sanction`. The planner can read a bounded authoritative recovery context and propose a plan; only Operations can sanction it.
- Added a durable `recovery_plans` Firestore record with observed state, understood failure reason, safe recommendation, action allowlist, planner identity, sanction identity/timestamps and the explicit boundary `ADVISORY_NO_STATE_MUTATION_NO_CLOSURE`.
- Added stale-plan protection: sanction fails if the issue no longer matches the state observed by the planner. Recommendations are limited by current authoritative state.
- Added deterministic plans for delayed/rejected `ACTION_PENDING`, `BLOCKED` and `HUMAN_REVIEW` work. A rejected or delayed evidence path recommends a fresh observation through the existing trusted integration; it cannot reuse evidence, record evidence or close work.
- Added Operations UI controls to generate and explicitly sanction a plan. Fresh evidence is enabled as the next governed action only after sanction. Recovery records are visible in issue detail and the governed lifecycle trace.
- Added a reproducible deployment script, focused recovery contract tests and production-readiness assertions for service identity, environment binding, invoker isolation and inspectable sanctioned-recovery evidence.

## What was deliberately not changed

- Firestore remains authoritative and State Authority remains the sole Next Shift Firestore writer.
- Recovery Planner was not given Firestore access, operational mutation, trusted-evidence recording, verification or closure capability.
- Operations sanctions a recommendation but still cannot record trusted evidence or independently close work.
- Specialist ownership and capability boundaries were not broadened. A recovery recommendation never changes owner.
- Memory remains advisory; the recovery contract records only bounded authoritative issue history in this phase and does not allow memory to establish current state.
- No new clinical workflow, public demo clinical content, presentation mock, fabricated evidence or fake telemetry was added.
- No Git branch change, commit, push, merge or pull request was performed.

## Exact validation performed

- `bash -n deploy_recovery_planner.sh verify_readiness.sh`: success.
- `python -m compileall -q services/state_authority services/recovery_planner_runtime services/operations_ui`: success.
- `git diff --check`: success.
- `pytest -q`: `124 passed, 49 subtests passed`.
- Focused tests prove that verification failure produces `REQUEST_FRESH_EVIDENCE`, planner history context is advisory, the planner lacks evidence/closure capabilities, recovery capabilities have no state transitions, and the lifecycle trace exposes sanction plus the no-mutation/no-closure boundary.
- `./deploy_recovery_planner.sh` plus the final authentication-error hardening redeploy: deployed State Authority `next-shift-state-authority-00023-66k`, Recovery Planner `next-shift-recovery-planner-00001-r6m`, and Operations `next-shift-operations-00023-gzg`, all serving 100% traffic.
- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh`: `PASS=177 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`. The two warnings are exactly the controller-authorized branch and dirty phase worktree.
- Queried current-revision error logs for the recovery, trusted-evidence and verifier path after acceptance; no error-severity records were returned.
- Deleted the temporary Cloud Run acceptance job after successful execution; no acceptance-only job or IAM grant remains.

## Live GCP evidence

A real synthetic, non-clinical EVS work item already waiting in `ACTION_PENDING` was recovered through the deployed path.

- Issue: `dOHgjChDQvDJcTQhwGTZ`
- Owner: `EVSThroughput`
- Recovery plan: `LBKZFwvyKFeM5jb8EZFz`
- Fresh trusted evidence: `eLwGJuqJw8mTl3NbEoaN`
- Evidence transition: `I0FszJmDk7Hlu9S5YPJG`
- Independent closure transition: `nUGY3J161vkt15fOHvpW`

Correlated State Authority audit records prove this order and separation of authority:

1. `ns-coverage-critic` used `recovery.read` against current Firestore state.
2. The same advisory identity used `recovery.plan`; State Authority persisted the proposed plan without changing issue state.
3. `ns-operations-ui` separately used `recovery.sanction` for that exact plan and observed state.
4. `ns-trusted-evidence` recorded a fresh external synthetic EVS observation and moved work to `VERIFYING`.
5. `ns-verifier` read verification context.
6. `ns-evidence-inspector` independently inspected the evidence.
7. `ns-verifier` alone used `verification.close` and closed the issue.

The final readiness gate independently finds plan `LBKZFwvyKFeM5jb8EZFz` as an inspectable production sanction proof. Project IAM confirms State Authority is still the sole Next Shift Firestore writer and Operations is the only direct Next Shift Firestore viewer. Recovery Planner is callable only by Operations; State Authority retains its exact least-privilege invoker set.

## Remaining risks

- The runner cannot directly query Firestore or pass the IAP-protected Operations UI. Authoritative results were inspected through State Authority security audit records, current Cloud Run configuration and readiness checks without broadening IAM.
- The available runner cannot create a new service account. Recovery Planner therefore uses the existing `ns-coverage-critic` advisory identity. This preserves the important technical boundary (no Firestore access, no mutation, no evidence, no closure) but does not provide a separately named managed identity for the two advisory services.
- The planner is deliberately deterministic. It uses current state, the latest verification failure and issue history; managed Memory Bank recommendations are not yet incorporated into per-issue recovery planning. This avoids turning advisory memory into operational truth.
- `BLOCKED` and `HUMAN_REVIEW` recommendations are contract-tested but the live phase acceptance used a delayed `ACTION_PENDING` work item to avoid manufacturing an operational failure.

The phase goal is satisfied: a real deployed recovery path understands delayed/rejected work, persists a safe bounded alternative, requires an independent sanction, preserves least privilege, and proceeds through fresh evidence and independent verification to closure.

PHASE_RESULT: PASS
