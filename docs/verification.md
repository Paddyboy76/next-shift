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

Final submission success requires:

```text
WARN=0
FAIL=0
NEXT_SHIFT_READINESS=PASS
```

The exact PASS count grows as protections are added. The pre-autonomy `159` baseline is historical, not a fixed target.

During authorized branch work only, repository-state exceptions can be explicit:

```bash
READINESS_ALLOW_BRANCH=1 READINESS_ALLOW_DIRTY=1 bash verify_readiness.sh
```

These flags do **not** suppress cloud, IAM, evidence, integration, security, or proof failures and must not be used for the final submission freeze.

Final branch acceptance on `final/visual-hierarchy-polish` produced:

```text
PASS=179
WARN=1   # authorized non-main branch only
FAIL=0
NEXT_SHIFT_READINESS=PASS
```

## Gateway and Model Armor behavior

Run the full repeatable probe:

```bash
bash scripts/verify_gateway_model_armor_trace.sh
```

This reads the live Agent Runtime / Agent Gateway / authorization policy / Model Armor template binding, sends a benign synthetic handover and an instruction-bypass probe through the same managed runtime endpoint, expects HTTP 200 and HTTP 403, and requires inspectable Cloud Logging proof. It does not call State Authority or create operational work.

The final acceptance proof record can be queried directly:

```bash
gcloud logging read \
'resource.type="cloud_run_job" AND
 resource.labels.job_name="next-shift-gateway-trace-proof" AND
 jsonPayload.event_type="gateway.model_armor_trace_proof" AND
 jsonPayload.benign_decision="ALLOW" AND
 jsonPayload.bypass_decision="DENY" AND
 jsonPayload.fail_open=false' \
--project=next-shift-506004 \
--limit=1 \
--order=desc \
--format='table(timestamp,jsonPayload.trace_id,jsonPayload.benign_http_status,jsonPayload.bypass_http_status)'
```

Final accepted result: benign `200`, bypass `403`, `fail_open=false`.

## Stale Human Reach denial proof

```bash
gcloud logging read \
'jsonPayload.reason="human_reach_stale_response"' \
--project=next-shift-506004 \
--limit=5 \
--order=desc \
--format='table(timestamp,jsonPayload.decision,jsonPayload.reason,jsonPayload.issue_id,jsonPayload.details.expected,jsonPayload.details.current)'
```

Final acceptance includes a production `DENY` against a CLOSED Facilities issue with expected `ACTION_PENDING`, current `CLOSED`, and no workflow mutation.

## Controlled recovery sanction proof

```bash
gcloud logging read \
'resource.type="cloud_run_revision" AND
 resource.labels.service_name="next-shift-state-authority" AND
 jsonPayload.event_type="authorization.decision" AND
 jsonPayload.capability="recovery.sanction" AND
 jsonPayload.decision="ALLOW" AND
 jsonPayload.reason="recovery_action_sanctioned"' \
--project=next-shift-506004 \
--limit=1 \
--order=desc \
--format='table(timestamp,jsonPayload.issue_id,jsonPayload.details.plan_id,jsonPayload.reason)'
```

Final accepted plan ID: `8Wxxoy4mAV04CeTZmt1l`.

## Gemini 3.5 serving configuration

Spoken handover and Facilities photo proof must both use Gemini 3.5:

```bash
gcloud run services describe next-shift-operations \
  --project=next-shift-506004 \
  --region=asia-southeast1 \
  --format=json \
  | jq -r '.spec.template.spec.containers[0].env[] | select(.name=="SPOKEN_HANDOVER_MODEL" or .name=="PHOTO_EVIDENCE_MODEL" or .name=="PHOTO_EVIDENCE_BUCKET") | "\(.name)=\(.value)"'

gcloud run services describe next-shift-human-reach \
  --project=next-shift-506004 \
  --region=asia-southeast1 \
  --format=json \
  | jq -r '.spec.template.spec.containers[0].env[] | select(.name=="PHOTO_EVIDENCE_MODEL" or .name=="PHOTO_EVIDENCE_BUCKET") | "\(.name)=\(.value)"'
```

## Human Reach + Facilities photo acceptance

The live acceptance sequence is:

1. create a fresh synthetic Facilities issue;
2. wait for the Google Chat Human Reach work card;
3. click **Completed** once;
4. confirm the card remains an unverified completion claim and requests BEFORE + AFTER photos;
5. reply in the same work thread with exactly two synthetic images and @mention Next Shift;
6. confirm Gemini 3.5 visual comparison is stored as `SUPPORTING_VISUAL_EVIDENCE_ONLY` with `may_close_work=false`;
7. confirm the separate trusted Facilities evidence path moves the issue to `VERIFYING`;
8. run the Independent Verifier;
9. confirm `VERIFYING → CLOSED` and the same Chat card refreshes to green **Verified complete**;
10. inspect the read-only photo evidence and exact verifier/inspector records in Operations.

## Mutating acceptance

`acceptance_async.py` and UI-driven acceptance create synthetic Firestore work and publish real events. Run them only with explicit authorization. Record issue/event/evidence/inspection/verifier IDs, inspect final authoritative truth, check current-revision error logs, and rerun readiness.

## Claim-to-proof map

| Claim | Proof |
|---|---|
| Gemini 3.5 requirement | serving env values + spoken/photo live acceptance |
| Messy multi-item normalization | accepted durable issues + held proposal accounting |
| Least-privilege fleet | readiness identity, invoker, datastore-role, and Pub/Sub checks |
| Human claim is not closure | `CLAIMED · UNVERIFIED` in Google Chat and Operations |
| Facilities multimodal proof | Chat BEFORE/AFTER record + Gemini inspection + private hashes |
| Independent closure | trusted evidence + inspector PASS + verifier identity in `/trace/<issue_id>` |
| Stale action protection | `human_reach_stale_response` DENY log |
| Gateway / Model Armor real path | `scripts/verify_gateway_model_armor_trace.sh` + structured proof log |
| Registered lifecycle | Agent Registry / managed runtime evidence in readiness and platform view |
| Persistent advisory context | Memory Bank provenance + `may_mutate_workflow=false` |
| Controlled recovery | sanctioned plan + `recovery_action_sanctioned` audit record |
| Durable observability | `/trace/<issue_id>` + Cloud Logging / Cloud Run request telemetry |

## Observability scope

The project exposes truthful platform telemetry and durable lifecycle correlation rather than fabricating a single synthetic trace. `/trace/<issue_id>` correlates persisted operational records, while Cloud Logging / Cloud Run retain request, revision, authorization, denial, proof, and security records.

Native application OTLP span export was attempted during development but could not be authorized within the available project permission boundary, so exported application OTLP spans are not claimed. This does not weaken the deployed lifecycle trace or the real Cloud Run / Cloud Logging evidence used in acceptance.

An external reviewer should be able to identify the active revision, run readiness, inspect a real issue trace, distinguish a claim from trusted evidence, identify inspector/verifier principals, see a stale denial without mutation, inspect Gateway/Model Armor behavior, and confirm Memory Bank and Recovery Planner remain advisory.
