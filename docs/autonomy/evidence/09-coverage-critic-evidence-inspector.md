# Mission 09 — Coverage Critic + Evidence Inspector

Audit date: 2026-08-23 UTC  
Repository: `Paddyboy76/next-shift`  
Project: `next-shift-506004` (`963749706976`)  
Region: `asia-southeast1`

## What was inspected

- Read all 809 lines of `AGENTS.md` before architectural changes.
- Fetched origin and verified the controller branch remained `codex/autonomous-final-attack` at `a34cc5e2836b1a80217c0a4fe1b27280a33a191f`; preserved the controller's pre-existing `docs/autonomy/STATUS.md` edit.
- Inspected the typed Agent Runtime intake contract, Operations intake orchestration, State Authority intake validation and policy, evidence envelope and closure transaction, verifier runtime, lifecycle trace, deployment scripts and regressions.
- Inspected live Cloud Run services/revisions/identities, Pub/Sub topics, enabled Vertex AI/Cloud Run/Firestore/Pub/Sub APIs, current project, and readiness state.
- Attempted Firestore database and billing inspection; the runner cannot read Firestore database metadata and Cloud Billing API is disabled/inaccessible to this identity. No API was enabled merely to satisfy documentation.

## What was changed in the repository

- Added a dedicated Coverage Critic runtime. It uses a separate Gemini call to compare raw handover text with typed intake proposals for missed, duplicated, conflated, misrouted or uncertain operational work.
- The critic has no issue-mutation API. It can only submit a bounded review to State Authority, which persists a message hash, findings, decision, model, principal and source reference in `coverage_reviews`.
- Operations now requires a durable critic PASS before persistence. A disagreement returns `human_review_required`, creates no issue, dispatches no event and exposes the findings to the operator.
- Added a deterministic Evidence Inspector runtime with its own proposed identity and no direct Firestore access. It independently evaluates evidence issuer, provenance, observation mode, timestamps, capability/source/subject/details and coverage.
- Added State Authority inspection-context and inspection-record endpoints with narrow capabilities. Inspections persist in `evidence_inspections`.
- Added a hard closure gate: State Authority refuses verifier closure unless a PASS inspection exists for the exact issue and evidence ID. The verifier invokes the inspector before requesting closure.
- Added a reproducible deployment script and focused adversarial tests for accepted provenance, specialist claims and wrong-capability evidence.

## What was deliberately not changed

- Firestore remains authoritative; neither critic nor inspector is designed to receive a direct Firestore role.
- Critics do not change issue state, routing policy, evidence or verifier authority.
- Deterministic routing and both existing verifier and State Authority evidence checks remain in place. The inspector is an additional gate, not a replacement.
- No Gemma call was added merely to increase model count. Semantic coverage uses Gemini; evidence policy remains deterministic.
- No clinical workflow, proprietary data, fabricated telemetry or presentation mock was added.
- No Cloud Run revision was deployed after the IAM failure, so the previously green production path was not weakened.

## Exact validation performed

- `.venv/bin/python -m py_compile services/state_authority/*.py services/coverage_critic_runtime/main.py services/evidence_inspector_runtime/main.py services/operations_ui/*.py services/verifier_runtime/main.py`: success.
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`: 119 tests passed.
- `git diff --check`: success.
- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash ./verify_readiness.sh`: exited 0; observed checks remained PASS with only the authorized controller-branch and dirty-worktree warnings.
- `bash ./deploy_critic_inspector.sh`: stopped before deployment when creation of `ns-coverage-critic` was denied. The exact missing permission is `iam.serviceAccounts.create`.
- Direct describes confirmed the proposed `ns-coverage-critic` and `ns-evidence-inspector` identities are absent or hidden, while existing `ns-verifier` and `ns-trusted-evidence` identities are readable.
- Project IAM inspection shows the runner has `roles/resourcemanager.projectIamAdmin`, `roles/run.admin`, `roles/run.sourceDeveloper` and `roles/aiplatform.admin`, but no service-account administration role.

## Relevant live GCP evidence

- Active project: `next-shift-506004`.
- Production remains on State Authority `next-shift-state-authority-00020-l6b`, Operations `next-shift-operations-00016-dkn`, trusted evidence `next-shift-trusted-evidence-00002-mlc`, and verifier `next-shift-verifier-00002-8cn`, each serving 100% traffic at readiness inspection.
- Existing specialist services and owner-specific identities remain ready.
- No `next-shift-coverage-critic` or `next-shift-evidence-inspector` Cloud Run service was created.
- The failed IAM request made no repository, Firestore, Cloud Run traffic, Pub/Sub or workflow mutation.

## Remaining risks and blocker

The phase cannot be declared complete without two distinct least-privilege runtime identities. Reusing Operations for the critic or the verifier/trusted-evidence identity for the inspector would undermine the exact architectural independence this mission exists to prove. The controller identity cannot create the required service accounts and cannot list service accounts generally.

Required external action: grant the controller temporary `roles/iam.serviceAccountAdmin` (and service-account-user authority as needed), or pre-create `ns-coverage-critic@next-shift-506004.iam.gserviceaccount.com` and `ns-evidence-inspector@next-shift-506004.iam.gserviceaccount.com`. Then rerun `bash ./deploy_critic_inspector.sh`, execute live PASS/disagreement coverage scenarios and an evidence-to-inspection-to-verifier closure, inspect the durable records, and rerun readiness.

PHASE_RESULT: BLOCKED
