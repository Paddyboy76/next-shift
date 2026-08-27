#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"
SERVICE="next-shift-operations"
SERVICE_ACCOUNT="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
BUILDER_ACCOUNT="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
MODEL="gemini-3.5-flash"
PHOTO_MODEL="gemini-3.5-flash"
PHOTO_BUCKET="${PROJECT_ID}-photo-evidence"
SOURCE="/home/patrick/next-shift/services/operations_ui"

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    printf 'ERROR: active project is %s\n' "${ACTIVE_PROJECT}"
    exit 1
fi

HUMAN_REACH_URL="$(gcloud run services describe next-shift-human-reach \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)')"

if [[ -z "${HUMAN_REACH_URL}" ]]; then
    printf 'ERROR: Human Reach service URL not found\n'
    exit 1
fi

gcloud run services add-iam-policy-binding next-shift-human-reach \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

if ! gcloud storage buckets describe "gs://${PHOTO_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${PHOTO_BUCKET}" \
        --project="${PROJECT_ID}" \
        --location="${REGION}" \
        --uniform-bucket-level-access \
        --quiet
fi

gcloud storage buckets add-iam-policy-binding "gs://${PHOTO_BUCKET}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin" \
    --quiet >/dev/null

gcloud run deploy "${SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${SOURCE}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_ACCOUNT}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --no-allow-unauthenticated \
    --update-env-vars="SPOKEN_HANDOVER_MODEL=${MODEL},PHOTO_EVIDENCE_MODEL=${PHOTO_MODEL},PHOTO_EVIDENCE_BUCKET=${PHOTO_BUCKET},HUMAN_REACH_URL=${HUMAN_REACH_URL}" \
    --quiet

LIVE_MODEL="$(gcloud run services describe "${SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format=json | jq -r '.spec.template.spec.containers[0].env[] | select(.name == "SPOKEN_HANDOVER_MODEL") | .value')"

if [[ "${LIVE_MODEL}" != "${MODEL}" ]]; then
    printf 'ERROR: live spoken handover model is %s\n' "${LIVE_MODEL}"
    exit 1
fi

printf 'SPOKEN_HANDOVER_DEPLOY_OK=1\n'
printf 'PHOTO_EVIDENCE_BUCKET=%s\n' "${PHOTO_BUCKET}"
