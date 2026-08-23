#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="next-shift-506004"; REGION="asia-southeast1"; REPO="/home/patrick/next-shift"
BUILDER="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
STATE="next-shift-state-authority"; STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
OPS="next-shift-operations"; OPS_SA="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
VERIFIER="next-shift-verifier"; VERIFIER_SA="ns-verifier@${PROJECT_ID}.iam.gserviceaccount.com"
CRITIC="next-shift-coverage-critic"; CRITIC_NAME="ns-coverage-critic"; CRITIC_SA="${CRITIC_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
INSPECTOR="next-shift-evidence-inspector"; INSPECTOR_NAME="ns-evidence-inspector"; INSPECTOR_SA="${INSPECTOR_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
[[ "$(gcloud config get-value project 2>/dev/null)" == "${PROJECT_ID}" ]]
for pair in "${CRITIC_NAME}|Next Shift Coverage Critic" "${INSPECTOR_NAME}|Next Shift Evidence Inspector"; do
  name="${pair%%|*}"; display="${pair#*|}"
  gcloud iam service-accounts describe "${name}@${PROJECT_ID}.iam.gserviceaccount.com" --project="${PROJECT_ID}" >/dev/null 2>&1 || gcloud iam service-accounts create "${name}" --display-name="${display}" --project="${PROJECT_ID}" --quiet
done
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${CRITIC_SA}" --role="roles/aiplatform.user" --quiet >/dev/null
STATE_URL="$(gcloud run services describe "${STATE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
gcloud run deploy "${STATE}" --source="${REPO}/services/state_authority" --region="${REGION}" --project="${PROJECT_ID}" --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER}" --service-account="${STATE_SA}" --no-allow-unauthenticated --set-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL},HUMAN_REACH_TOPIC=next-shift-human-reach-requested" --quiet
for service_account in "${CRITIC_SA}" "${INSPECTOR_SA}"; do gcloud run services add-iam-policy-binding "${STATE}" --region="${REGION}" --project="${PROJECT_ID}" --member="serviceAccount:${service_account}" --role="roles/run.invoker" --quiet >/dev/null; done
gcloud run deploy "${CRITIC}" --source="${REPO}/services/coverage_critic_runtime" --region="${REGION}" --project="${PROJECT_ID}" --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER}" --service-account="${CRITIC_SA}" --no-allow-unauthenticated --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL},CRITIC_MODEL=gemini-3.5-flash" --quiet
gcloud run deploy "${INSPECTOR}" --source="${REPO}/services/evidence_inspector_runtime" --region="${REGION}" --project="${PROJECT_ID}" --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER}" --service-account="${INSPECTOR_SA}" --no-allow-unauthenticated --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL}" --quiet
CRITIC_URL="$(gcloud run services describe "${CRITIC}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
INSPECTOR_URL="$(gcloud run services describe "${INSPECTOR}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
gcloud run services add-iam-policy-binding "${CRITIC}" --region="${REGION}" --project="${PROJECT_ID}" --member="serviceAccount:${OPS_SA}" --role="roles/run.invoker" --quiet >/dev/null
gcloud run services add-iam-policy-binding "${INSPECTOR}" --region="${REGION}" --project="${PROJECT_ID}" --member="serviceAccount:${VERIFIER_SA}" --role="roles/run.invoker" --quiet >/dev/null
gcloud run deploy "${VERIFIER}" --source="${REPO}/services/verifier_runtime" --region="${REGION}" --project="${PROJECT_ID}" --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER}" --service-account="${VERIFIER_SA}" --no-allow-unauthenticated --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL},EVIDENCE_INSPECTOR_URL=${INSPECTOR_URL}" --quiet
EVIDENCE_URL="$(gcloud run services describe next-shift-trusted-evidence --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
VERIFIER_URL="$(gcloud run services describe "${VERIFIER}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
gcloud run deploy "${OPS}" --source="${REPO}/services/operations_ui" --region="${REGION}" --project="${PROJECT_ID}" --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER}" --service-account="${OPS_SA}" --no-allow-unauthenticated --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL},EVIDENCE_SERVICE_URL=${EVIDENCE_URL},VERIFIER_SERVICE_URL=${VERIFIER_URL},COVERAGE_CRITIC_URL=${CRITIC_URL}" --quiet
echo "CRITIC_INSPECTOR_DEPLOY_OK=1"
