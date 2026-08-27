#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"
REPO="/home/patrick/next-shift"
BUILDER_ACCOUNT="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
HUMAN_REACH_SERVICE="next-shift-human-reach"
HUMAN_REACH_SA="ns-human-reach@${PROJECT_ID}.iam.gserviceaccount.com"
EVIDENCE_SERVICE="next-shift-trusted-evidence"
PHOTO_BUCKET="${PROJECT_ID}-photo-evidence"
PHOTO_MODEL="gemini-3.5-flash"

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    printf 'ERROR: active project is %s\n' "${ACTIVE_PROJECT}"
    exit 1
fi

EVIDENCE_URL="$(gcloud run services describe "${EVIDENCE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)')"

if [[ -z "${EVIDENCE_URL}" ]]; then
    printf 'ERROR: trusted evidence service URL not found\n'
    exit 1
fi

if ! gcloud storage buckets describe "gs://${PHOTO_BUCKET}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${PHOTO_BUCKET}" \
        --project="${PROJECT_ID}" \
        --location="${REGION}" \
        --uniform-bucket-level-access \
        --quiet
fi

gcloud storage buckets add-iam-policy-binding "gs://${PHOTO_BUCKET}" \
    --member="serviceAccount:${HUMAN_REACH_SA}" \
    --role="roles/storage.objectAdmin" \
    --quiet >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${HUMAN_REACH_SA}" \
    --role="roles/aiplatform.user" \
    --quiet >/dev/null

gcloud run services add-iam-policy-binding "${EVIDENCE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${HUMAN_REACH_SA}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

gcloud run deploy "${HUMAN_REACH_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${REPO}/services/human_reach_runtime" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_ACCOUNT}" \
    --service-account="${HUMAN_REACH_SA}" \
    --no-invoker-iam-check \
    --update-env-vars="PHOTO_EVIDENCE_MODEL=${PHOTO_MODEL},PHOTO_EVIDENCE_BUCKET=${PHOTO_BUCKET},EVIDENCE_SERVICE_URL=${EVIDENCE_URL}" \
    --quiet

bash "${REPO}/deploy_spoken_handover.sh"

printf 'CHAT_PHOTO_PROOF_DEPLOY_OK=1\n'
printf 'PHOTO_EVIDENCE_BUCKET=%s\n' "${PHOTO_BUCKET}"
printf 'PHOTO_EVIDENCE_MODEL=%s\n' "${PHOTO_MODEL}"
