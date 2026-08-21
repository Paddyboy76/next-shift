#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"
REPO="/home/patrick/next-shift"

STATE_SERVICE="next-shift-state-authority"
STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
OPERATIONS_SERVICE="next-shift-operations"
OPERATIONS_SA="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
BUILDER_SA="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
TOPIC="next-shift-handover-received"

STATE_DIR="${REPO}/services/state_authority"
OPERATIONS_DIR="${REPO}/services/operations_ui"


echo "===== VERIFY PROJECT ====="
ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "ERROR: active project is ${ACTIVE_PROJECT}"
    exit 1
fi

echo "project=${ACTIVE_PROJECT}"


echo
echo "===== VERIFY SOURCE ====="
test -f "${STATE_DIR}/main.py"
test -f "${STATE_DIR}/intake.py"
test -f "${OPERATIONS_DIR}/main.py"
test -f "${OPERATIONS_DIR}/state_authority.py"
echo "SOURCE_OK=1"


echo
echo "===== EXISTING STATE AUTHORITY URL ====="
STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "STATE_AUTHORITY_URL=${STATE_URL}"


echo
echo "===== DEPLOY STATE AUTHORITY ====="
gcloud run deploy "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${STATE_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${STATE_SA}" \
    --no-allow-unauthenticated \
    --set-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL}" \
    --quiet

STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "STATE_AUTHORITY_URL=${STATE_URL}"


echo
echo "===== GRANT NARROW INTAKE IAM ====="
gcloud run services add-iam-policy-binding \
    "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${OPERATIONS_SA}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

echo "OPERATIONS_TO_STATE_AUTHORITY_INVOKER_OK=1"


gcloud pubsub topics add-iam-policy-binding \
    "${TOPIC}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${STATE_SA}" \
    --role="roles/pubsub.publisher" \
    --quiet >/dev/null

echo "STATE_AUTHORITY_TOPIC_PUBLISHER_OK=1"


echo
echo "===== DEPLOY OPERATIONS UI ====="
gcloud run deploy "${OPERATIONS_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${OPERATIONS_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${OPERATIONS_SA}" \
    --no-allow-unauthenticated \
    --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL}" \
    --quiet


echo
echo "===== VERIFY IDENTITIES AND ENV ====="
gcloud run services describe "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(spec.template.spec.serviceAccountName)'

gcloud run services describe "${OPERATIONS_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='yaml(status.url,spec.template.spec.serviceAccountName,spec.template.spec.containers[0].env)'


echo
echo "FORTIFIED_INTAKE_DEPLOY_OK=1"
