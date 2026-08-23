#!/usr/bin/env bash

set -u
set -o pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"
ENGINE_ID="8140616966286082048"
GATEWAY="next-shift-ingress"
AUTHZ_EXTENSION="next-shift-ingress-model-armor"
AUTHZ_POLICY="next-shift-ingress-model-armor-policy"
MODEL_ARMOR_TEMPLATE="next-shift-intake-guard"
STATE_AUTHORITY_URL="https://next-shift-state-authority-mycnigy7dq-as.a.run.app"
COVERAGE_CRITIC_URL="https://next-shift-coverage-critic-mycnigy7dq-as.a.run.app"
EVIDENCE_INSPECTOR_URL="https://next-shift-evidence-inspector-mycnigy7dq-as.a.run.app"
HUMAN_REACH_TOPIC="next-shift-human-reach-requested"
HANDOVER_TOPIC="next-shift-handover-received"
DLQ_TOPIC="next-shift-dead-letter"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'PASS  %s\n' "$1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf 'FAIL  %s\n' "$1"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf 'WARN  %s\n' "$1"
}

section() {
    printf '\n===== %s =====\n' "$1"
}

require_command() {
    if command -v "$1" >/dev/null 2>&1; then
        pass "command available: $1"
    else
        fail "missing required command: $1"
    fi
}

json_get() {
    local file="$1"
    local expression="$2"
    jq -r "${expression} // empty" "${file}" 2>/dev/null
}

expect_equal() {
    local actual="$1"
    local expected="$2"
    local label="$3"

    if [[ "${actual}" == "${expected}" ]]; then
        pass "${label}"
    else
        fail "${label} (expected=${expected@Q} actual=${actual@Q})"
    fi
}

expect_contains() {
    local actual="$1"
    local expected="$2"
    local label="$3"

    if [[ "${actual}" == *"${expected}"* ]]; then
        pass "${label}"
    else
        fail "${label} (missing ${expected@Q})"
    fi
}

fetch_run_service() {
    local service="$1"
    local output="$2"

    gcloud run services describe "${service}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format=json >"${output}" 2>/dev/null
}

check_run_service() {
    local service="$1"
    local expected_sa="$2"
    local file="${TMP_DIR}/${service}.json"

    if ! fetch_run_service "${service}" "${file}"; then
        fail "Cloud Run service exists: ${service}"
        return
    fi

    pass "Cloud Run service exists: ${service}"

    local ready
    local latest
    local sa
    local traffic
    ready="$(json_get "${file}" '.status.latestReadyRevisionName')"
    latest="$(json_get "${file}" '.status.latestCreatedRevisionName')"
    sa="$(json_get "${file}" '.spec.template.spec.serviceAccountName')"
    traffic="$(jq -r '[.status.traffic[]? | select(.latestRevision == true) | .percent] | add // 0' "${file}")"

    if [[ -n "${ready}" && "${ready}" == "${latest}" ]]; then
        pass "${service} latest revision is ready (${ready})"
    else
        fail "${service} latest revision readiness (ready=${ready@Q} latest=${latest@Q})"
    fi

    expect_equal "${sa}" "${expected_sa}" "${service} service account"
    expect_equal "${traffic}" "100" "${service} serves 100% latest traffic"
}

check_invokers() {
    local service="$1"
    local expected_csv="$2"
    local file="${TMP_DIR}/${service}-iam.json"

    if ! gcloud run services get-iam-policy "${service}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format=json >"${file}" 2>/dev/null; then
        fail "read Cloud Run IAM: ${service}"
        return
    fi

    local actual
    actual="$(jq -r '[.bindings[]? | select(.role == "roles/run.invoker") | .members[]?] | sort | join(",")' "${file}")"

    local expected
    expected="$(printf '%s' "${expected_csv}" | tr ',' '\n' | sort | paste -sd, -)"

    expect_equal "${actual}" "${expected}" "${service} invoker isolation"
}

check_push_subscription() {
    local sub="$1"
    local owner="$2"
    local endpoint="$3"
    local push_sa="$4"
    local audience="$5"
    local filter_expected="$6"
    local file="${TMP_DIR}/${sub}.json"

    if ! gcloud pubsub subscriptions describe "${sub}" \
        --project="${PROJECT_ID}" \
        --format=json >"${file}" 2>/dev/null; then
        fail "Pub/Sub subscription exists: ${sub}"
        return
    fi

    pass "Pub/Sub subscription exists: ${sub}"

    expect_equal "$(json_get "${file}" '.topic')" \
        "projects/${PROJECT_ID}/topics/${owner}" \
        "${sub} topic"

    expect_equal "$(json_get "${file}" '.pushConfig.pushEndpoint')" \
        "${endpoint}" \
        "${sub} push endpoint"

    expect_equal "$(json_get "${file}" '.pushConfig.oidcToken.serviceAccountEmail')" \
        "${push_sa}" \
        "${sub} OIDC identity"

    expect_equal "$(json_get "${file}" '.pushConfig.oidcToken.audience')" \
        "${audience}" \
        "${sub} OIDC audience"

    if [[ -n "${filter_expected}" ]]; then
        expect_equal "$(json_get "${file}" '.filter')" \
            "${filter_expected}" \
            "${sub} owner filter"
    fi

    expect_equal "$(json_get "${file}" '.retryPolicy.minimumBackoff')" \
        "10s" \
        "${sub} minimum retry backoff"
    expect_equal "$(json_get "${file}" '.retryPolicy.maximumBackoff')" \
        "60s" \
        "${sub} maximum retry backoff"
    expect_equal "$(json_get "${file}" '.deadLetterPolicy.maxDeliveryAttempts')" \
        "5" \
        "${sub} maximum delivery attempts"
    expect_equal "$(json_get "${file}" '.deadLetterPolicy.deadLetterTopic')" \
        "projects/${PROJECT_ID}/topics/${DLQ_TOPIC}" \
        "${sub} dead-letter topic"
}

section "LOCAL PREREQUISITES"
require_command gcloud
require_command git
require_command jq
require_command curl

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
expect_equal "${ACTIVE_PROJECT}" "${PROJECT_ID}" "active gcloud project"

section "REPOSITORY"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    pass "running inside a Git repository"

    git fetch origin main --quiet 2>/dev/null || warn "could not refresh origin/main; using local remote ref"

    HEAD_SHA="$(git rev-parse HEAD 2>/dev/null || true)"
    MAIN_SHA="$(git rev-parse origin/main 2>/dev/null || true)"
    BRANCH="$(git branch --show-current 2>/dev/null || true)"

    if [[ "${HEAD_SHA}" == "${MAIN_SHA}" && "${BRANCH}" == "main" ]]; then
        pass "main matches origin/main (${HEAD_SHA})"
    elif [[ "${READINESS_ALLOW_BRANCH:-0}" == "1" ]]; then
        warn "non-main verification allowed (branch=${BRANCH} head=${HEAD_SHA} origin/main=${MAIN_SHA})"
    else
        fail "repository must be cleanly on current main (branch=${BRANCH} head=${HEAD_SHA} origin/main=${MAIN_SHA})"
    fi

    if [[ -z "$(git status --porcelain 2>/dev/null)" ]]; then
        pass "working tree clean"
    elif [[ "${READINESS_ALLOW_DIRTY:-0}" == "1" ]]; then
        warn "working-tree changes allowed for autonomous phase verification"
    else
        fail "working tree has local changes"
    fi
else
    fail "not running inside the Next Shift Git repository"
fi

section "CLOUD RUN SERVICES"
check_run_service next-shift-state-authority \
    "ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-operations \
    "ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-human-reach \
    "ns-human-reach@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-trusted-evidence \
    "ns-trusted-evidence@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-verifier \
    "ns-verifier@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-coverage-critic \
    "ns-coverage-critic@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-evidence-inspector \
    "ns-evidence-inspector@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-recovery-planner \
    "ns-coverage-critic@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-facilities \
    "ns-worker-facilities@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-asset-logistics \
    "ns-worker-asset-logistics@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-language-access \
    "ns-worker-language-access@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-discharge-dme \
    "ns-worker-discharge-dme@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-evs-throughput \
    "ns-worker-evs-throughput@${PROJECT_ID}.iam.gserviceaccount.com"
check_run_service next-shift-patient-transport \
    "ns-worker-patient-transport@${PROJECT_ID}.iam.gserviceaccount.com"

OPS_FILE="${TMP_DIR}/next-shift-operations.json"
if [[ -s "${OPS_FILE}" ]]; then
    expect_equal "$(json_get "${OPS_FILE}" '.metadata.annotations["run.googleapis.com/iap-enabled"]')" \
        "true" \
        "Operations UI is protected by IAP"
    expect_equal "$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name == "COVERAGE_CRITIC_URL") | .value' "${OPS_FILE}")" \
        "${COVERAGE_CRITIC_URL}" \
        "Operations uses the independent Coverage Critic"
    expect_equal "$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name == "RECOVERY_PLANNER_URL") | .value' "${OPS_FILE}")" \
        "https://next-shift-recovery-planner-mycnigy7dq-as.a.run.app" \
        "Operations uses the controlled Recovery Planner"
fi

VERIFIER_FILE="${TMP_DIR}/next-shift-verifier.json"
if [[ -s "${VERIFIER_FILE}" ]]; then
    expect_equal "$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name == "EVIDENCE_INSPECTOR_URL") | .value' "${VERIFIER_FILE}")" \
        "${EVIDENCE_INSPECTOR_URL}" \
        "Verifier requires the independent Evidence Inspector"
fi

STATE_FILE="${TMP_DIR}/next-shift-state-authority.json"
if [[ -s "${STATE_FILE}" ]]; then
    expect_equal "$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name == "STATE_AUTHORITY_AUDIENCE") | .value' "${STATE_FILE}")" \
        "${STATE_AUTHORITY_URL}" \
        "State Authority audience"
    expect_equal "$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name == "HUMAN_REACH_TOPIC") | .value' "${STATE_FILE}")" \
        "${HUMAN_REACH_TOPIC}" \
        "State Authority Human Reach topic"
fi

section "FIRESTORE AUTHORITY"
PROJECT_IAM="${TMP_DIR}/project-iam.json"
if gcloud projects get-iam-policy "${PROJECT_ID}" --format=json >"${PROJECT_IAM}" 2>/dev/null; then
    DATASTORE_USERS="$(jq -r '[.bindings[]? | select(.role == "roles/datastore.user") | .members[]? | select(startswith("serviceAccount:ns-"))] | sort | join(",")' "${PROJECT_IAM}")"
    DATASTORE_VIEWERS="$(jq -r '[.bindings[]? | select(.role == "roles/datastore.viewer") | .members[]? | select(startswith("serviceAccount:ns-"))] | sort | join(",")' "${PROJECT_IAM}")"

    expect_equal "${DATASTORE_USERS}" \
        "serviceAccount:ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com" \
        "State Authority is sole Next Shift Firestore writer"

    expect_equal "${DATASTORE_VIEWERS}" \
        "serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com" \
        "Operations UI is the only Next Shift Firestore viewer"
else
    fail "read project IAM policy"
fi

section "CLOUD RUN INVOKER ISOLATION"
check_invokers next-shift-facilities \
    "serviceAccount:ns-push-facilities@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-asset-logistics \
    "serviceAccount:ns-push-asset-logistics@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-language-access \
    "serviceAccount:ns-push-language-access@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-discharge-dme \
    "serviceAccount:ns-push-discharge-dme@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-evs-throughput \
    "serviceAccount:ns-push-evs-throughput@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-patient-transport \
    "serviceAccount:ns-push-patient-transport@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-human-reach \
    "serviceAccount:ns-push-human-reach@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-trusted-evidence \
    "serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-verifier \
    "serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-coverage-critic \
    "serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-evidence-inspector \
    "serviceAccount:ns-verifier@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-recovery-planner \
    "serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
check_invokers next-shift-operations \
    "serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com"
check_invokers next-shift-state-authority \
    "serviceAccount:ns-coverage-critic@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-evidence-inspector@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-human-reach@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-trusted-evidence@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-verifier@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-asset-logistics@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-discharge-dme@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-evs-throughput@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-facilities@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-language-access@${PROJECT_ID}.iam.gserviceaccount.com,serviceAccount:ns-worker-patient-transport@${PROJECT_ID}.iam.gserviceaccount.com"

section "PUB/SUB DELIVERY"
for entry in \
    "Facilities|facilities" \
    "AssetLogistics|asset-logistics" \
    "LanguageAccess|language-access" \
    "DischargeDME|discharge-dme" \
    "EVSThroughput|evs-throughput" \
    "PatientTransport|patient-transport"
do
    OWNER="${entry%%|*}"
    SLUG="${entry##*|}"
    SERVICE="next-shift-${SLUG}"
    URL="https://${SERVICE}-mycnigy7dq-as.a.run.app"
    check_push_subscription \
        "${SERVICE}-push" \
        "${HANDOVER_TOPIC}" \
        "${URL}/pubsub" \
        "ns-push-${SLUG}@${PROJECT_ID}.iam.gserviceaccount.com" \
        "${URL}" \
        "attributes.owner=\"${OWNER}\""
done

HUMAN_REACH_URL="https://next-shift-human-reach-mycnigy7dq-as.a.run.app"
check_push_subscription \
    "next-shift-human-reach-push" \
    "${HUMAN_REACH_TOPIC}" \
    "${HUMAN_REACH_URL}/pubsub" \
    "ns-push-human-reach@${PROJECT_ID}.iam.gserviceaccount.com" \
    "${HUMAN_REACH_URL}" \
    ""

DLQ_FILE="${TMP_DIR}/dlq.json"
if gcloud pubsub subscriptions describe next-shift-dead-letter-review \
    --project="${PROJECT_ID}" \
    --format=json >"${DLQ_FILE}" 2>/dev/null; then
    expect_equal "$(json_get "${DLQ_FILE}" '.topic')" \
        "projects/${PROJECT_ID}/topics/${DLQ_TOPIC}" \
        "dead-letter review subscription"
else
    fail "dead-letter review subscription exists"
fi

section "STALE HUMAN REACH GUARD"
STALE_DENY="$(gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="next-shift-state-authority" AND jsonPayload.event_type="authorization.decision" AND jsonPayload.reason="human_reach_stale_response" AND jsonPayload.decision="DENY"' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --format='value(jsonPayload.issue_id)' 2>/dev/null || true)"

if [[ -n "${STALE_DENY}" ]]; then
    pass "production stale Human Reach denial is auditable (${STALE_DENY})"
else
    fail "no audited production human_reach_stale_response denial found"
fi

section "AGENT RUNTIME AND IDENTITY"
ACCESS_TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
ENGINE_FILE="${TMP_DIR}/engine.json"
if [[ -n "${ACCESS_TOKEN}" ]] && curl -fsS \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${ENGINE_ID}" \
    >"${ENGINE_FILE}" 2>/dev/null; then
    pass "managed Agent Runtime is readable"

    EFFECTIVE_IDENTITY="$(json_get "${ENGINE_FILE}" '.spec.effectiveIdentity')"
    if [[ "${EFFECTIVE_IDENTITY}" == agents.global.* ]]; then
        pass "managed Agent Identity enabled"
    else
        fail "managed Agent Identity missing (${EFFECTIVE_IDENTITY@Q})"
    fi

    expect_equal "$(json_get "${ENGINE_FILE}" '.spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway')" \
        "projects/${PROJECT_ID}/locations/${REGION}/agentGateways/${GATEWAY}" \
        "Agent Runtime bound to client-to-agent gateway"
else
    fail "read managed Agent Runtime"
fi

section "AGENT GATEWAY"
GATEWAY_FILE="${TMP_DIR}/gateway.json"
if gcloud network-services agent-gateways describe "${GATEWAY}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --format=json >"${GATEWAY_FILE}" 2>/dev/null; then
    pass "Agent Gateway exists"
    expect_equal "$(json_get "${GATEWAY_FILE}" '.googleManaged.governedAccessPath')" \
        "CLIENT_TO_AGENT" \
        "Agent Gateway governed access path"
    PROTOCOLS="$(jq -r '.protocols // [] | sort | join(",")' "${GATEWAY_FILE}")"
    expect_contains "${PROTOCOLS}" "MCP" "Agent Gateway MCP protocol"
else
    fail "Agent Gateway exists"
fi

section "MODEL ARMOR"
EXT_FILE="${TMP_DIR}/extension.json"
if gcloud service-extensions authz-extensions describe "${AUTHZ_EXTENSION}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --format=json >"${EXT_FILE}" 2>/dev/null; then
    pass "Model Armor authorization extension exists"
    expect_equal "$(json_get "${EXT_FILE}" '.service')" \
        "modelarmor.${REGION}.rep.googleapis.com" \
        "Model Armor regional service"
    expect_equal "$(json_get "${EXT_FILE}" '.timeout')" \
        "5s" \
        "Model Armor extension timeout"

    FAIL_OPEN_RAW="$(jq -r 'if has("failOpen") then (.failOpen|tostring) else "OMITTED" end' "${EXT_FILE}")"
    if [[ "${FAIL_OPEN_RAW}" == "false" || "${FAIL_OPEN_RAW}" == "OMITTED" ]]; then
        pass "Model Armor extension is not configured fail-open (${FAIL_OPEN_RAW})"
    else
        fail "Model Armor extension failOpen=${FAIL_OPEN_RAW}"
    fi

    SETTINGS="$(json_get "${EXT_FILE}" '.metadata.model_armor_settings')"
    expect_contains "${SETTINGS}" "templates/${MODEL_ARMOR_TEMPLATE}" \
        "Model Armor request/response template binding"
else
    fail "Model Armor authorization extension exists"
fi

POLICY_FILE="${TMP_DIR}/authz-policy.json"
if gcloud beta network-security authz-policies describe "${AUTHZ_POLICY}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --format=json >"${POLICY_FILE}" 2>/dev/null; then
    pass "Model Armor content authorization policy exists"
    expect_equal "$(json_get "${POLICY_FILE}" '.policyProfile')" \
        "CONTENT_AUTHZ" \
        "Model Armor policy profile"
    expect_equal "$(json_get "${POLICY_FILE}" '.action')" \
        "CUSTOM" \
        "Model Armor policy action"

    POLICY_TARGETS="$(jq -r '.target.resources // [] | join(",")' "${POLICY_FILE}")"
    expect_contains "${POLICY_TARGETS}" "/agentGateways/${GATEWAY}" \
        "Model Armor policy targets Agent Gateway"

    PROVIDERS="$(jq -r '.customProvider.authzExtension.resources // [] | join(",")' "${POLICY_FILE}")"
    expect_contains "${PROVIDERS}" "/authzExtensions/${AUTHZ_EXTENSION}" \
        "Model Armor policy uses authorization extension"
else
    fail "Model Armor content authorization policy exists"
fi

TRACE_PROOF="$(gcloud logging read \
    'resource.type="cloud_run_job" AND resource.labels.job_name="next-shift-gateway-trace-proof" AND jsonPayload.event_type="gateway.model_armor_trace_proof" AND jsonPayload.benign_decision="ALLOW" AND jsonPayload.bypass_decision="DENY" AND jsonPayload.fail_open=false' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --format='value(jsonPayload.trace_id)' 2>/dev/null || true)"

if [[ -n "${TRACE_PROOF}" ]]; then
    pass "governed Gateway and Model Armor allow/deny trace is inspectable (${TRACE_PROOF})"
else
    fail "no inspectable governed Gateway and Model Armor allow/deny trace"
fi

RECOVERY_PROOF="$(gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="next-shift-state-authority" AND jsonPayload.event_type="authorization.decision" AND jsonPayload.capability="recovery.sanction" AND jsonPayload.decision="ALLOW" AND jsonPayload.reason="recovery_action_sanctioned"' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --format='value(jsonPayload.details.plan_id)' 2>/dev/null || true)"

if [[ -n "${RECOVERY_PROOF}" ]]; then
    pass "sanctioned controlled-recovery proof is inspectable (${RECOVERY_PROOF})"
else
    fail "no inspectable sanctioned controlled-recovery proof"
fi

section "REQUIRED APIS"
for api in \
    aiplatform.googleapis.com \
    networkservices.googleapis.com \
    networksecurity.googleapis.com \
    modelarmor.googleapis.com
do
    if gcloud services list \
        --project="${PROJECT_ID}" \
        --enabled \
        --filter="config.name=${api}" \
        --format='value(config.name)' 2>/dev/null \
        | grep -qx "${api}"; then
        pass "API enabled: ${api}"
    else
        fail "API missing: ${api}"
    fi
done

section "RESULT"
printf 'PASS=%d  WARN=%d  FAIL=%d\n' "${PASS_COUNT}" "${WARN_COUNT}" "${FAIL_COUNT}"

if (( FAIL_COUNT > 0 )); then
    printf 'NEXT_SHIFT_READINESS=FAIL\n'
    exit 1
fi

printf 'NEXT_SHIFT_READINESS=PASS\n'
