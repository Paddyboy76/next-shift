#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"

if [[ "$(gcloud config get-value project 2>/dev/null)" != "${PROJECT_ID}" ]]; then
    printf 'ERROR active_project=%s expected=%s\n' \
        "$(gcloud config get-value project 2>/dev/null)" "${PROJECT_ID}"
    exit 1
fi

printf '=== NEXT SHIFT LIVE GOOGLE CLOUD PROOF ===\n'

for service in \
    next-shift-operations \
    next-shift-human-reach \
    next-shift-coverage-critic \
    next-shift-memory-sync \
    next-shift-state-authority \
    next-shift-verifier
do
    gcloud run services describe "${service}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(metadata.name,status.latestReadyRevisionName,spec.template.spec.serviceAccountName)' \
        | awk '{printf "CLOUD_RUN  service=%s  revision=%s  identity=%s\n", $1, $2, $3}'
done

OPS_JSON="$(mktemp)"
HR_JSON="$(mktemp)"
MEMORY_JSON="$(mktemp)"
trap 'rm -f "${OPS_JSON}" "${HR_JSON}" "${MEMORY_JSON}"' EXIT

gcloud run services describe next-shift-operations \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format=json >"${OPS_JSON}"

gcloud run services describe next-shift-human-reach \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format=json >"${HR_JSON}"

gcloud run services describe next-shift-memory-sync \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format=json >"${MEMORY_JSON}"

SPOKEN_MODEL="$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name=="SPOKEN_HANDOVER_MODEL") | .value' "${OPS_JSON}")"
OPS_PHOTO_MODEL="$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name=="PHOTO_EVIDENCE_MODEL") | .value' "${OPS_JSON}")"
HR_PHOTO_MODEL="$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name=="PHOTO_EVIDENCE_MODEL") | .value' "${HR_JSON}")"
ADVISOR_MODEL="$(jq -r '.spec.template.spec.containers[0].env[]? | select(.name=="ADVISOR_MODEL") | .value' "${MEMORY_JSON}")"

printf 'GEMINI     spoken=%s  photo=%s  chat_photo=%s  memory_advisor=%s\n' \
    "${SPOKEN_MODEL:-UNKNOWN}" "${OPS_PHOTO_MODEL:-UNKNOWN}" "${HR_PHOTO_MODEL:-UNKNOWN}" "${ADVISOR_MODEL:-UNKNOWN}"

GATEWAY_PROOF="$(gcloud logging read \
    'resource.type="cloud_run_job" AND resource.labels.job_name="next-shift-gateway-trace-proof" AND jsonPayload.event_type="gateway.model_armor_trace_proof" AND jsonPayload.benign_decision="ALLOW" AND jsonPayload.bypass_decision="DENY" AND jsonPayload.fail_open=false' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --order=desc \
    --format='value(jsonPayload.trace_id,jsonPayload.benign_http_status,jsonPayload.bypass_http_status)' 2>/dev/null || true)"

if [[ -n "${GATEWAY_PROOF}" ]]; then
    read -r TRACE_ID BENIGN_HTTP BYPASS_HTTP <<<"${GATEWAY_PROOF}"
    printf 'GATEWAY    trace=%s  benign=%s/ALLOW  bypass=%s/DENY  fail_open=false\n' \
        "${TRACE_ID}" "${BENIGN_HTTP}" "${BYPASS_HTTP}"
else
    printf 'GATEWAY    proof=NOT_FOUND\n'
fi

STALE_PROOF="$(gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="next-shift-state-authority" AND jsonPayload.reason="human_reach_stale_response" AND jsonPayload.decision="DENY"' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --order=desc \
    --format='value(jsonPayload.issue_id,jsonPayload.details.expected,jsonPayload.details.current)' 2>/dev/null || true)"

if [[ -n "${STALE_PROOF}" ]]; then
    read -r STALE_ISSUE EXPECTED_STATE CURRENT_STATE <<<"${STALE_PROOF}"
    printf 'STALE_CHAT issue=%s  decision=DENY  expected=%s  current=%s\n' \
        "${STALE_ISSUE}" "${EXPECTED_STATE}" "${CURRENT_STATE}"
else
    printf 'STALE_CHAT proof=NOT_FOUND\n'
fi

RECOVERY_PROOF="$(gcloud logging read \
    'resource.type="cloud_run_revision" AND resource.labels.service_name="next-shift-state-authority" AND jsonPayload.event_type="authorization.decision" AND jsonPayload.capability="recovery.sanction" AND jsonPayload.decision="ALLOW" AND jsonPayload.reason="recovery_action_sanctioned"' \
    --project="${PROJECT_ID}" \
    --limit=1 \
    --order=desc \
    --format='value(jsonPayload.issue_id,jsonPayload.details.plan_id)' 2>/dev/null || true)"

if [[ -n "${RECOVERY_PROOF}" ]]; then
    read -r RECOVERY_ISSUE RECOVERY_PLAN <<<"${RECOVERY_PROOF}"
    printf 'RECOVERY   issue=%s  plan=%s  sanction=ALLOW\n' \
        "${RECOVERY_ISSUE}" "${RECOVERY_PLAN}"
else
    printf 'RECOVERY   proof=NOT_FOUND\n'
fi

printf '=== END LIVE PROOF ===\n'
