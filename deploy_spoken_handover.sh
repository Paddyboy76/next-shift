#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"
SERVICE="next-shift-operations"
SERVICE_ACCOUNT="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
BUILDER_ACCOUNT="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
MODEL="gemini-3.5-flash"
SOURCE="/home/patrick/next-shift/services/operations_ui"

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    printf 'ERROR: active project is %s\n' "${ACTIVE_PROJECT}"
    exit 1
fi

gcloud run deploy "${SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${SOURCE}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_ACCOUNT}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --no-allow-unauthenticated \
    --update-env-vars="SPOKEN_HANDOVER_MODEL=${MODEL}" \
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
