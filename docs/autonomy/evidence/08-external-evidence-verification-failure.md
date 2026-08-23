# Mission 08 — External Evidence and Verification Failure

Audit date: 2026-08-23 UTC  
Repository: `Paddyboy76/next-shift`  
Project: `next-shift-506004` (`963749706976`)  
Region: `asia-southeast1`

## What was inspected

- Read `AGENTS.md` completely before changing the repository.
- Fetched origin and verified the controller branch remained `codex/autonomous-final-attack`; no branch, commit, push, merge or PR operation was performed.
- Preserved the controller's pre-existing `docs/autonomy/STATUS.md` change.
- Inspected the State Authority evidence and closure transactions, verifier runtime, trusted-evidence runtime, principal policies, Cloud Run deployment configuration, Operations lifecycle trace and existing regressions.
- Inspected the live State Authority, trusted-evidence, verifier and Operations revisions, runtime service accounts, invoker IAM, project-level Firestore roles, Pub/Sub delivery configuration and correlated production logs.
- Verified that trusted evidence and the verifier have separate runtime identities and neither identity has a direct Firestore role.

## What changed

- Added a versioned evidence envelope (`schema_version=1.0`) with judge-visible provenance: State Authority, issuer identity, source integration, observation mode, observation timestamp and the authoritative workflow state observed.
- Added deterministic evidence validation at both verifier and State Authority boundaries. Closure now rejects missing or malformed provenance, an untrusted issuer, issue/owner mismatch, malformed/future timestamps, evidence older than 24 hours, malformed details, and a capability/source/subject mismatch.
- Kept State Authority as the final closure authority. Even if verifier-runtime logic were bypassed, State Authority independently revalidates the complete evidence contract transactionally before `VERIFYING → CLOSED`.
- Added the dedicated `verification.reject` capability to the independent verifier only.
- Added authoritative `verification_attempts` records for failed verification. A rejection records verifier identity, reason, candidate evidence, recovery state and timestamps, then performs the canonical recoverable `VERIFYING → ACTION_PENDING` transition. It never closes the issue.
- Added verification-failure and detailed provenance entries to the judge-visible lifecycle trace.
- Added focused adversarial regressions for specialist claims, stale timestamps, malformed timestamps, wrong-capability evidence, all six valid capability contracts, independent identities and recoverable rejection.
- Fixed `deploy_verification_path.sh` so redeploying State Authority preserves the required `HUMAN_REACH_TOPIC` environment binding. Readiness detected this deployment-definition defect during the phase; State Authority was immediately repaired and the final readiness run is green.

## What was deliberately not changed

- Gemini Vision was evaluated but not implemented. Next Shift does not yet have an independently authenticated image-capture/attestation channel. Adding image analysis alone would make Gemini output a decorative specialist claim, not independent operational evidence. No clinical imagery or clinical decision path was introduced.
- Firestore remains authoritative. Evidence and verifier services still have no direct Firestore role and can mutate state only through State Authority.
- Specialists and Human Reach were not granted evidence or closure capability. No existing evidence or least-privilege requirement was weakened.
- No arbitrary evidence-upload API was added. The trusted-evidence service continues to derive capability-specific evidence from authoritative issue context rather than trusting caller-supplied completion fields.
- No permanent acceptance-only GCP resource or IAM grant was left behind. Two short-lived Cloud Run Job definitions used the existing Operations and verifier identities and were deleted after inspection.

## Exact validation performed

- `python -m py_compile` across changed State Authority, verifier and Operations modules: success.
- `python -m unittest tests.test_fortified_verification_path tests.test_lifecycle_trace`: 11 tests passed.
- `python -m unittest discover -s tests -p 'test_*.py'`: 116 tests passed.
- `git diff --check`: success.
- Deployed the affected path with `bash ./deploy_verification_path.sh`.
- Final live revisions serving 100% traffic:
  - State Authority `next-shift-state-authority-00020-l6b`
  - trusted evidence `next-shift-trusted-evidence-00002-mlc`
  - verifier `next-shift-verifier-00002-8cn`
  - Operations `next-shift-operations-00016-dkn`
- `READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash ./verify_readiness.sh`: `PASS=157 WARN=2 FAIL=0`, `NEXT_SHIFT_READINESS=PASS`. The two warnings are exactly the authorized controller branch and phase worktree.
- Confirmed current invoker isolation and project IAM: State Authority is the only Next Shift Firestore writer; Operations is the only Next Shift Firestore viewer; trusted evidence and verifier have no direct data role.
- Queried current-revision error logs after deployment; no error-severity records were returned for State Authority, trusted evidence, verifier or Operations in the inspected deployment window.

## Live GCP evidence

A real synthetic, non-clinical Patient Transport acceptance ran through the deployed path under existing least-privilege identities.

- Issue: `Vy5LMNVo1nDcDgtJcmdG`
- Intake event: `b66151db-275f-42cc-a70e-ffea8c027382`
- Evidence: `gLaRxTgrXXaHb4q1sabC`
- Evidence transition: `AsNkTPccHGdELaiUkhoj`
- Closure transition: `SFEpA9m2hIPye7trft7B`
- Trusted-evidence response: HTTP `201`
- Independent-verifier response: HTTP `200`

Correlated State Authority audit records show:

1. `ns-operations-ui` created the issue.
2. `ns-worker-patient-transport` performed the three canonical specialist transitions to `ACTION_PENDING`.
3. `ns-trusted-evidence` recorded evidence and moved the issue to `VERIFYING`.
4. `ns-verifier` separately read verification context and closed the issue.

An authoritative verification-context inspection under the verifier identity returned:

- issue state `CLOSED`, verification status `VERIFIED`;
- evidence schema `1.0`;
- source `synthetic_transport_system` and subject `TRN-597117E1`;
- recorder `ns-trusted-evidence@next-shift-506004.iam.gserviceaccount.com`;
- provenance authority `state_authority`;
- observation mode `synthetic_external_system`;
- workflow state observed `ACTION_PENDING`;
- verifier `ns-verifier@next-shift-506004.iam.gserviceaccount.com`.

This proves the deployed success path uses distinct coordination, evidence and verification authorities. The adversarial regressions prove the same matcher rejects specialist-only claims, absent provenance, stale/malformed timestamps and wrong-capability evidence. State Authority repeats those checks before closure and durably records recoverable verifier rejection.

## Remaining risks

- The phase runner cannot directly read Firestore, impersonate service accounts or pass IAP. Authoritative state was therefore inspected through the deployed verifier-authorized State Authority context and correlated Cloud Logging, without broadening IAM.
- A live stale-evidence rejection would require waiting beyond the deterministic 24-hour freshness window or corrupting authoritative data. Neither was justified. The rejection path is protected by focused deterministic tests and deployed code; live acceptance exercised the valid evidence path.
- Vision evidence remains intentionally deferred until an authenticated, non-clinical capture source can provide genuine independent provenance. An image model alone must never become workflow authority.
- The failed initial temporary-job executions are retained honestly in Cloud Run execution history: one had CLI argument splitting and one used a slim image without `jq`. Neither reached evidence or verification mutation. The successful execution and all product audit records are separately identified above.

The phase goal is satisfied: evidence independence is technically enforced, provenance is operator-visible, bad evidence cannot close work, verifier identity remains separate, and failed verification has a durable recoverable path.

PHASE_RESULT: PASS
