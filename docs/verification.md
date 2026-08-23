# Reproducible verification

## Local contracts

```bash
cd /home/patrick/next-shift
source .venv/bin/activate
python -m compileall -q next_shift services workers tests
python -m pytest -q
git diff --check
```

## Read-only production readiness

```bash
gcloud config set project next-shift-506004
bash verify_readiness.sh
```

Success on a submission revision requires:

```text
WARN=0
FAIL=0
NEXT_SHIFT_READINESS=PASS
```

The exact PASS count grows as protections are added. `159` is the pre-autonomy golden baseline, not a fixed current count.

Controller-managed work can explicitly exempt only repository state:

```bash
READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh
```

Those variables do not suppress cloud, IAM, evidence, integration, or security failures and must not be used for the final submission freeze.

## Gateway and Model Armor behavior

```bash
bash scripts/verify_gateway_model_armor_trace.sh
```

This reads the live runtime/gateway/policy/template binding, sends a benign synthetic handover and an instruction-bypass probe through the same endpoint, expects HTTP 200 and HTTP 403, and requires inspectable Cloud Logging proof. It does not call State Authority or create work.

## Mutating acceptance

`acceptance_async.py` and UI-driven acceptance create synthetic Firestore work and publish real events. Run them only with explicit authorization. Record issue/event/evidence/inspection/verifier IDs, inspect final authoritative truth, check current-revision error logs, and rerun readiness.

## Claim-to-proof map

| Claim | Proof |
|---|---|
| Least-privilege fleet | readiness identity, invoker, datastore-role, and Pub/Sub checks |
| Independent closure | evidence + inspector PASS + verifier identity in `/trace/<issue_id>` and readiness |
| Gateway/Model Armor real path | `scripts/verify_gateway_model_armor_trace.sh` |
| Registered lifecycle | readiness Agent Registry assertions |
| Advisory Memory Bank intelligence | Operations advisor provenance and readiness |
| Controlled recovery | sanctioned plan in issue detail/trace and readiness |
| Durable observability | `/trace/<issue_id>` plus Cloud Run request trace/span fields |
| Native application OTLP spans | not claimed; export was unavailable at the current permission boundary |

An external reviewer should be able to identify the active revision, run readiness, inspect a real issue trace, distinguish an unverified claim from trusted evidence, identify inspector/verifier principals, see a denial without state mutation, and confirm memory/recovery are advisory.

