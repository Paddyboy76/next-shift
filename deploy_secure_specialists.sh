#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"

REPO="/home/patrick/next-shift"
STATE_DIR="${REPO}/services/state_authority"
RUNTIME_DIR="${REPO}/services/specialist_runtime"

BUILDER_SA="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"

STATE_SERVICE="next-shift-state-authority"
STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"

TOPIC="next-shift-handover-received"
DLQ_TOPIC="next-shift-dead-letter"

echo "===== VERIFY PROJECT ====="
ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "ERROR: active project is ${ACTIVE_PROJECT}"
    exit 1
fi

echo "project=${ACTIVE_PROJECT}"

echo
echo "===== VERIFY SOURCE DIRECTORIES ====="

test -f "${STATE_DIR}/main.py"
test -f "${STATE_DIR}/policy.py"
test -f "${RUNTIME_DIR}/main.py"
test -f "${RUNTIME_DIR}/workflow.py"

echo "SOURCE_OK"

echo
echo "===== DEPLOY UPDATED STATE AUTHORITY ====="

STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

cd "${STATE_DIR}"

gcloud run deploy "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source=. \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${STATE_SA}" \
    --no-allow-unauthenticated \
    --min-instances=0 \
    --max-instances=2 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL}" \
    --quiet

STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "STATE_AUTHORITY_URL=${STATE_URL}"

deploy_specialist() {
    local slug="$1"
    local owner="$2"

    local service="next-shift-${slug}"
    local worker_sa="ns-worker-${slug}@${PROJECT_ID}.iam.gserviceaccount.com"
    local push_sa="ns-push-${slug}@${PROJECT_ID}.iam.gserviceaccount.com"
    local subscription="next-shift-${slug}-push"

    echo
    echo "========================================"
    echo "DEPLOY ${owner}"
    echo "========================================"

    echo
    echo "--- grant worker -> State Authority ---"

    gcloud run services add-iam-policy-binding \
        "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --member="serviceAccount:${worker_sa}" \
        --role="roles/run.invoker" \
        --quiet >/dev/null

    echo "STATE_AUTHORITY_INVOKER_OK"

    echo
    echo "--- deploy ${service} ---"

    cd "${RUNTIME_DIR}"

    gcloud run deploy "${service}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --source=. \
        --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
        --service-account="${worker_sa}" \
        --no-allow-unauthenticated \
        --min-instances=0 \
        --max-instances=2 \
        --memory=512Mi \
        --cpu=1 \
        --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL},SPECIALIST_OWNER=${owner}" \
        --quiet

    local service_url

    service_url="$(
        gcloud run services describe "${service}" \
            --project="${PROJECT_ID}" \
            --region="${REGION}" \
            --format='value(status.url)'
    )"

    echo "SERVICE_URL=${service_url}"

    echo
    echo "--- grant matching Pub/Sub identity ---"

    gcloud run services add-iam-policy-binding \
        "${service}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --member="serviceAccount:${push_sa}" \
        --role="roles/run.invoker" \
        --quiet >/dev/null

    echo "PUSH_INVOKER_OK"

    echo
    echo "--- create authenticated push subscription ---"

    if gcloud pubsub subscriptions describe \
        "${subscription}" \
        --project="${PROJECT_ID}" \
        >/dev/null 2>&1
    then
        echo "SUBSCRIPTION_EXISTS=${subscription}"
    else
        gcloud pubsub subscriptions create \
            "${subscription}" \
            --project="${PROJECT_ID}" \
            --topic="${TOPIC}" \
            --push-endpoint="${service_url}/pubsub" \
            --push-auth-service-account="${push_sa}" \
            --push-auth-token-audience="${service_url}" \
            --message-filter="attributes.owner=\"${owner}\"" \
            --dead-letter-topic="${DLQ_TOPIC}" \
            --max-delivery-attempts=5 \
            --min-retry-delay=10s \
            --max-retry-delay=60s \
            --quiet

        echo "SUBSCRIPTION_CREATED=${subscription}"
    fi
}

deploy_specialist \
    "asset-logistics" \
    "AssetLogistics"

deploy_specialist \
    "language-access" \
    "LanguageAccess"

deploy_specialist \
    "discharge-dme" \
    "DischargeDME"

deploy_specialist \
    "evs-throughput" \
    "EVSThroughput"

deploy_specialist \
    "patient-transport" \
    "PatientTransport"

echo
echo "===== VERIFY CLOUD RUN SERVICES ====="

gcloud run services list \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --filter='metadata.name:next-shift-' \
    --format='table(metadata.name,status.url,spec.template.spec.serviceAccountName)'

echo
echo "===== VERIFY SECURE PUSH SUBSCRIPTIONS ====="

for subscription in \
    next-shift-facilities-push \
    next-shift-asset-logistics-push \
    next-shift-language-access-push \
    next-shift-discharge-dme-push \
    next-shift-evs-throughput-push \
    next-shift-patient-transport-push
do
    echo
    echo "--- ${subscription} ---"

    gcloud pubsub subscriptions describe \
        "${subscription}" \
        --project="${PROJECT_ID}" \
        --format='yaml(filter,pushConfig.oidcToken,pushConfig.pushEndpoint)'
done

echo
echo "SECURE_SPECIALIST_ROLLOUT_OK"
