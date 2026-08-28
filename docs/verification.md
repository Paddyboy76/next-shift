# Reproducible verification

## Local contracts

```bash
cd /home/patrick/next-shift
source .venv/bin/activate
python -m compileall -q next_shift services workers tests
python -m pytest -q
git diff --check
```

Final clean-main local result:

```text
152 passed
49 subtests passed
```

## Final composed submission gate

Use the submission wrapper rather than running isolated checks manually:

```bash
gcloud config set project next-shift-506004
bash scripts/verify_submission.sh
```

Final accepted result on clean current `main` (`882975f89595f6306f9c6246bd5a6983fa0d5bb1`):

```text
PASS=180
WARN=0
FAIL=0
NEXT_SHIFT_READINESS=PASS
MODEL_ASSERT all_demo_gemini_3_5=true
NEXT_SHIFT_SUBMISSION=PASS
```

The wrapper composes the production readiness gate with the compact judge-facing model/security proof. It does not suppress cloud, IAM, evidence, integration, security, or model failures.

## Audit proof freshness

Several readiness claims intentionally depend on durable Cloud Logging evidence: stale Human Reach denial, Gateway/Model Armor allow-deny behavior, and controlled recovery sanction.

`gcloud logging read` has a short implicit freshness window. Submission-time proof queries therefore use an explicit seven-day window so a valid accepted audit record does not disappear merely because the CLI default ages out. The predicates themselves are unchanged and remain strict.

Accepted stale Human Reach proof:

```text
issue=Qej662s5TWLs3nXYzA6l
decision=DENY
reason=human_reach_stale_response
expected=ACTION_PENDING
current=CLOSED
```

## Compact live product proof

```bash
bash scripts/demo_proof_snapshot.sh
```

This is read-only. It inspects deployed Cloud Run revisions and service identities, asserts the demo-facing Gemini services are configured on `gemini-3.5-flash`, and reads the latest inspectable Gateway/Model Armor allow-deny proof, stale Human Reach denial, and controlled-recovery sanction.

Final accepted model assertion:

```text
GEMINI spoken=gemini-3.5-flash critic=gemini-3.5-flash photo=gemini-3.5-flash chat_photo=gemini-3.5-flash memory=gemini-3.5-flash
MODEL_ASSERT all_demo_gemini_3_5=true
```

The managed ADK intake agent is also configured on `gemini-3.5-flash` in `next_shift/agent.py`; its governed live path is exercised through the Agent Runtime / Gateway proof and normal intake acceptance.

## Gateway and Model Armor behavior

```bash
bash scripts/verify_gateway_model_armor_trace.sh
```

This reads the live runtime/gateway/policy/template binding, sends a benign synthetic handover and an instruction-bypass probe through the same endpoint, expects HTTP 200 and HTTP 403, and requires inspectable Cloud Logging proof. It does not call State Authority or create work.

Final accepted proof:

```text
trace=mission11-15a4d988-17ef-41e5-b5b3-3656019215f0
benign=200/ALLOW
bypass=403/DENY
fail_open=false
```

## Mutating acceptance

`acceptance_async.py` and UI-driven acceptance create synthetic Firestore work and publish real events. Do not rerun them merely for presentation. The feature phase is frozen; mutating acceptance should be repeated only if a genuine runtime defect requires it.

## Claim-to-proof map

| Claim | Proof |
|---|---|
| Least-privilege fleet | readiness identity, invoker, datastore-role, and Pub/Sub checks |
| Gemini 3.5 demo-facing model set | `scripts/demo_proof_snapshot.sh` plus managed ADK intake source/runtime acceptance |
| Human claim is not closure | Google Chat `CLAIMED · UNVERIFIED` + authoritative State Authority state |
| Facilities multimodal support | Chat BEFORE/AFTER record + Gemini inspection + private hashes |
| Independent closure | trusted evidence + inspector PASS + verifier identity in `/trace/<issue_id>` |
| Stale action protection | `human_reach_stale_response` DENY with unchanged CLOSED state |
| Gateway/Model Armor real path | `scripts/verify_gateway_model_armor_trace.sh` + structured proof log |
| Registered lifecycle | Agent Registry/runtime platform reads and readiness |
| Advisory Memory Bank intelligence | Operations advisor provenance, Memory Bank record, Gemini 3.5 model proof |
| Controlled recovery | `recovery_action_sanctioned` proof; planner remains advisory |
| Durable observability | `/trace/<issue_id>` plus Cloud Logging / Cloud Run request telemetry |
| Native application OTLP spans | not claimed; export was unavailable at the current permission boundary |

An external reviewer should be able to identify the active revision, run the composed submission gate, inspect the compact live proof, inspect a real issue trace, distinguish an unverified claim from trusted evidence, identify inspector/verifier principals, see a denial without state mutation, and confirm memory/recovery are advisory.

The durable final record is `docs/autonomy/evidence/101-final-submission-freeze-20260828.md`.
