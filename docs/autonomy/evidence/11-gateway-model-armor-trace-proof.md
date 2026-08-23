# Mission 11 — Gateway + Model Armor Trace Proof

Date: 2026-08-23 UTC

## What was inspected

- Read `AGENTS.md` in full (809 lines) before changes.
- Verified the controller-owned branch remained `codex/autonomous-final-attack`; phase start was `7d0cc0ace260437856cfe9a2e00b6f2f810f2c38`, while `origin/main` remained the golden `ce7baed79f07ecfb958225f37291d7949312e342`.
- Preserved the pre-existing modification to `docs/autonomy/STATUS.md`.
- Confirmed active project `next-shift-506004`, active principal `ns-codex-runner@next-shift-506004.iam.gserviceaccount.com`, and serving Google Cloud resources.
- Read the live Agent Runtime REST resource, Agent Gateway, authorization extension, content authorization policy, Model Armor template, Cloud Run Operations service, IAM bindings and Cloud Logging evidence.
- Billing linkage could not be refreshed because the Cloud Billing API is disabled and the runner cannot enable/read it. This is unchanged from Mission 07; the deployed project remained active and serving.

## What changed

- Added correlation-safe governed-ingress decision logging to the Operations UI runtime. It records request ID, caller, operational request type, gateway, policy, template, runtime, HTTP status and `ALLOW`/`DENY`/`ERROR`, but never prompt content.
- Moved creation of the Operations intake reference ahead of Agent Runtime invocation so the same correlation ID follows a request from governed analysis into durable State Authority creation when allowed.
- Added `tests/test_gateway_model_armor_trace.py` to protect denial correlation and prompt non-disclosure.
- Added `scripts/verify_gateway_model_armor_trace.sh`, a repeatable synthetic verifier for live binding/configuration plus benign and bypass requests.
- Added the private `next-shift-gateway-trace-proof` Cloud Run Job. It independently reads live control-plane settings, calls the production `reasoningEngines:streamQuery` path, asserts allow/deny behavior and emits one structured Cloud Logging proof event.
- Added a readiness assertion requiring an inspectable successful Gateway/Model Armor allow/deny proof.
- Deployed Operations revision `next-shift-operations-00022-689` at 100% traffic.
- Granted the existing Operations identity only four read-only roles needed by the proof job: `roles/networkservices.viewer`, `roles/networkservices.serviceExtensionsViewer`, `roles/networksecurity.viewer`, and `roles/modelarmor.viewer`. Existing `roles/aiplatform.user` authorizes the governed runtime probe. The job is non-public.
- Temporary build-only `roles/storage.admin` access was removed after image build. An attempted `roles/logging.logWriter` grant to the controller was also removed after its credential boundary still denied direct writes.

## Live proof

Live configuration read on 2026-08-23:

- Runtime: `projects/next-shift-506004/locations/asia-southeast1/reasoningEngines/8140616966286082048`.
- Effective identity: `agents.global.org-268393301563.system.id.goog/resources/aiplatform/projects/963749706976/locations/asia-southeast1/reasoningEngines/8140616966286082048`.
- Identity type: `AGENT_IDENTITY`.
- Runtime client-to-agent binding: `projects/next-shift-506004/locations/asia-southeast1/agentGateways/next-shift-ingress`.
- Gateway governed access path: `CLIENT_TO_AGENT`.
- Authorization policy: `CONTENT_AUTHZ`, action `CUSTOM`, targeted to `next-shift-ingress` and backed by `next-shift-ingress-model-armor`.
- Extension service: `modelarmor.asia-southeast1.rep.googleapis.com`; timeout `5s`; `failOpen` is false by API default/omission and explicitly false in deployment source.
- Model Armor template: `next-shift-intake-guard`; prompt-injection/jailbreak enforcement `ENABLED`; confidence `MEDIUM_AND_ABOVE`; latest filter version.

Controlled live production-path result:

- Benign synthetic handover through `reasoningEngines:streamQuery`: HTTP 200 and a valid AssetLogistics proposal.
- Synthetic instruction-bypass attempt through the same endpoint: HTTP 403, `PERMISSION_DENIED`, with `Model Armor: Prompt violates content security configurations`.
- Neither probe called State Authority, so no operational issue was persisted.
- Successful Cloud Run Job execution: `next-shift-gateway-trace-proof-ffxz9`.
- Inspectable structured Cloud Logging trace: `mission11-e4f1c413-23a4-43f7-8bdf-7f980086d360` (and a later successful verifier execution produced `mission11-e4f1c413-23a4-43f7-8bdf-7f980086d360` as the queried proof at validation time).
- The trace correlates `operational_request=handover_intake`, governed path, runtime Agent Identity, gateway, policy, template, `fail_open=false`, filter enforcement, benign `200/ALLOW`, bypass `403/DENY`, and `prompt_content_logged=false`.

Cloud Logging query:

```text
resource.type="cloud_run_job"
resource.labels.job_name="next-shift-gateway-trace-proof"
jsonPayload.event_type="gateway.model_armor_trace_proof"
```

## Exact validation

- `python -m py_compile services/operations_ui/runtime.py services/operations_ui/main.py tests/test_gateway_model_armor_trace.py services/gateway_trace_runtime/main.py`: success.
- `pytest -q`: `121 passed, 49 subtests passed` (170 checks; no failures).
- `scripts/verify_gateway_model_armor_trace.sh`: `GATEWAY_MODEL_ARMOR_TRACE_PROOF=PASS`; benign HTTP 200; bypass HTTP 403; fail-open false; filter enforcement enabled; managed Agent Identity present; inspectable trace found.
- Cloud Run Job execution `next-shift-gateway-trace-proof-ffxz9`: completed successfully.
- Operations revision `next-shift-operations-00022-689`: ready and serving 100% traffic under IAP with the existing `ns-operations-ui` identity and existing downstream endpoint configuration preserved.
- `bash verify_readiness.sh`: all 170 production/platform checks passed, `WARN=0`; the script reported exactly two expected repository-controller failures because it hard-codes `main == origin/main` and a clean worktree while this authorized autonomous phase runs on the controller branch with uncommitted phase output. No cloud, security, runtime, evidence or integration readiness check failed.
- Verified temporary builder and controller logging grants were absent after validation.

## Deliberately not changed

- Did not rebuild or replace Agent Gateway, Model Armor template, authorization extension, policy or Runtime binding.
- Did not weaken IAP to invoke the Operations UI as the controller identity.
- Did not enable fail-open behavior or reduce filter confidence/enforcement.
- Did not persist either controlled probe as operational work.
- Did not log prompt bodies, system prompts or model output.
- Did not change Firestore authority, specialist authority, evidence rules, independent verification, branch or Git history.

## Remaining risks

- The managed Gateway/Model Armor data plane does not currently expose a native per-request decision log visible to this project principal. The controlled Cloud Run Job therefore supplies repeatable, factual behavioral evidence in Cloud Logging; Operations ingress also emits correlated decision records for authenticated product requests that reach it.
- The proof job uses the Operations service identity plus read-only control-plane viewers. This is intentionally non-mutating, but a future dedicated proof identity could isolate judge-verification reads if operational cost and lifecycle justify it.
- Two failed proof-job executions remain visible before the successful run: the first exposed an overridden buildpack command, and the second occurred before read-only IAM propagation. Both failures are truthful and superseded by successful executions.
- Cloud Billing API access remains unavailable to the controller; live serving state was verified, but billing linkage was not re-read.

PHASE_RESULT: PASS
