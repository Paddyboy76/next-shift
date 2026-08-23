#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"
REPO="/home/patrick/next-shift"
BUILDER_SA="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
OPS_SA="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
PLANNER_SA="ns-coverage-critic@${PROJECT_ID}.iam.gserviceaccount.com"

[[ "$(gcloud config get-value project 2>/dev/null)" == "${PROJECT_ID}" ]]

STATE_URL="$(gcloud run services describe next-shift-state-authority --project="${PROJECT_ID}" \
  --region="${REGION}" --format='value(status.url)')"

gcloud run deploy next-shift-state-authority --project="${PROJECT_ID}" --region="${REGION}" \
  --source="${REPO}/services/state_authority" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
  --service-account="${STATE_SA}" --no-allow-unauthenticated \
  --update-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL},HUMAN_REACH_TOPIC=next-shift-human-reach-requested" --quiet

gcloud run deploy next-shift-recovery-planner --project="${PROJECT_ID}" --region="${REGION}" \
  --source="${REPO}/services/recovery_planner_runtime" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
  --service-account="${PLANNER_SA}" --no-allow-unauthenticated \
  --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL}" --quiet

PLANNER_URL="$(gcloud run services describe next-shift-recovery-planner --project="${PROJECT_ID}" \
  --region="${REGION}" --format='value(status.url)')"

gcloud run services add-iam-policy-binding next-shift-recovery-planner --project="${PROJECT_ID}" \
  --region="${REGION}" --member="serviceAccount:${OPS_SA}" --role=roles/run.invoker --quiet >/dev/null

gcloud run deploy next-shift-operations --project="${PROJECT_ID}" --region="${REGION}" \
  --source="${REPO}/services/operations_ui" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
  --service-account="${OPS_SA}" --no-allow-unauthenticated \
  --update-env-vars="RECOVERY_PLANNER_URL=${PLANNER_URL}" --quiet

echo "STATE_AUTHORITY_URL=${STATE_URL}"
echo "RECOVERY_PLANNER_URL=${PLANNER_URL}"
