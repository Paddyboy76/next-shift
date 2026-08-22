#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"
REPO="/home/patrick/next-shift"

STATE_SERVICE="next-shift-state-authority"
STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
HUMAN_REACH_SERVICE="next-shift-human-reach"
HUMAN_REACH_SA_NAME="ns-human-reach"
HUMAN_REACH_SA="${HUMAN_REACH_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
PUSH_SA_NAME="ns-push-human-reach"
PUSH_SA="${PUSH_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
OPERATIONS_SERVICE="next-shift-operations"
OPERATIONS_SA="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
EVIDENCE_SERVICE="next-shift-trusted-evidence"
VERIFIER_SERVICE="next-shift-verifier"
BUILDER_SA="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
PUBSUB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
CHAT_INVOKER="chat@system.gserviceaccount.com"

HUMAN_REACH_TOPIC="next-shift-human-reach-requested"
HUMAN_REACH_SUBSCRIPTION="next-shift-human-reach-push"
DLQ_TOPIC="next-shift-dead-letter"

STATE_DIR="${REPO}/services/state_authority"
HUMAN_REACH_DIR="${REPO}/services/human_reach_runtime"
OPERATIONS_DIR="${REPO}/services/operations_ui"

DEFAULT_ROUTES_JSON='{"Facilities":"Next Shift - Facilities Ops","AssetLogistics":"Next Shift - Facilities Ops","EVSThroughput":"Next Shift - Facilities Ops","LanguageAccess":"Next Shift - Patient Flow","DischargeDME":"Next Shift - Patient Flow","PatientTransport":"Next Shift - Patient Flow"}'
ROUTES_JSON="${HUMAN_REACH_ROUTES_JSON:-${DEFAULT_ROUTES_JSON}}"


assert_no_direct_data_roles() {
    local service_account="$1"
    local role

    while IFS= read -r role; do
        [[ -z "${role}" ]] && continue

        case "${role}" in
            roles/datastore.*|roles/firebase.*|roles/editor|roles/owner)
                echo "ERROR: ${service_account} has prohibited direct-data role ${role}"
                exit 1
                ;;
        esac
    done < <(
        gcloud projects get-iam-policy "${PROJECT_ID}" \
            --flatten='bindings[].members' \
            --filter="bindings.members:serviceAccount:${service_account}" \
            --format='value(bindings.role)'
    )
}


echo "===== VERIFY PROJECT ====="
ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "ERROR: active project is ${ACTIVE_PROJECT}"
    exit 1
fi

echo "project=${ACTIVE_PROJECT}"


echo
echo "===== VERIFY BILLING ====="
gcloud billing projects describe "${PROJECT_ID}" \
    --format='value(billingEnabled)' | grep -qx 'True'
echo "BILLING_OK=1"


echo
echo "===== VERIFY SOURCE ====="
test -f "${STATE_DIR}/human_reach.py"
test -f "${STATE_DIR}/human_reach_contract.py"
test -f "${STATE_DIR}/human_reach_dispatch.py"
test -f "${STATE_DIR}/human_reach_transition.py"
test -f "${HUMAN_REACH_DIR}/main.py"
test -f "${HUMAN_REACH_DIR}/entrypoint.py"
test -f "${OPERATIONS_DIR}/data.py"
echo "SOURCE_OK=1"


echo
echo "===== ENABLE GOOGLE CHAT API ====="
gcloud services enable \
    chat.googleapis.com \
    pubsub.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet
echo "APIS_OK=1"


echo
echo "===== ENSURE HUMAN REACH IDENTITIES ====="
if ! gcloud iam service-accounts describe "${HUMAN_REACH_SA}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${HUMAN_REACH_SA_NAME}" \
        --project="${PROJECT_ID}" \
        --display-name="Next Shift Human Reach" \
        --quiet
fi

if ! gcloud iam service-accounts describe "${PUSH_SA}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${PUSH_SA_NAME}" \
        --project="${PROJECT_ID}" \
        --display-name="Next Shift Human Reach PubSub Push" \
        --quiet
fi

echo "HUMAN_REACH_SA=${HUMAN_REACH_SA}"
echo "HUMAN_REACH_PUSH_SA=${PUSH_SA}"


echo
echo "===== ENFORCE HUMAN REACH LEAST PRIVILEGE ====="
assert_no_direct_data_roles "${HUMAN_REACH_SA}"
echo "HUMAN_REACH_NO_DIRECT_DATA_ROLES=1"

# Required for this service account to consume enabled Google APIs under the
# project quota context; it does not grant access to Firestore workflow data.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${HUMAN_REACH_SA}" \
    --role="roles/serviceusage.serviceUsageConsumer" \
    --quiet >/dev/null

echo "HUMAN_REACH_SERVICE_USAGE_OK=1"


echo
echo "===== ENSURE HUMAN REACH TOPIC ====="
if gcloud pubsub topics describe "${HUMAN_REACH_TOPIC}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "TOPIC_EXISTS=${HUMAN_REACH_TOPIC}"
else
    gcloud pubsub topics create "${HUMAN_REACH_TOPIC}" \
        --project="${PROJECT_ID}" \
        --quiet
    echo "TOPIC_CREATED=${HUMAN_REACH_TOPIC}"
fi

gcloud pubsub topics add-iam-policy-binding \
    "${HUMAN_REACH_TOPIC}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${STATE_SA}" \
    --role="roles/pubsub.publisher" \
    --quiet >/dev/null

echo "STATE_AUTHORITY_HUMAN_REACH_PUBLISHER_OK=1"


echo
echo "===== DEPLOY STATE AUTHORITY ====="
STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

gcloud run deploy "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${STATE_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${STATE_SA}" \
    --no-allow-unauthenticated \
    --min-instances=0 \
    --max-instances=2 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL},HUMAN_REACH_TOPIC=${HUMAN_REACH_TOPIC}" \
    --quiet

STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "STATE_AUTHORITY_URL=${STATE_URL}"


gcloud run services add-iam-policy-binding \
    "${STATE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${HUMAN_REACH_SA}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

echo "HUMAN_REACH_TO_STATE_AUTHORITY_INVOKER_OK=1"


echo
echo "===== DEPLOY HUMAN REACH ====="
gcloud run deploy "${HUMAN_REACH_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${HUMAN_REACH_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${HUMAN_REACH_SA}" \
    --no-allow-unauthenticated \
    --min-instances=0 \
    --max-instances=2 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="^~^STATE_AUTHORITY_URL=${STATE_URL}~HUMAN_REACH_ROUTES_JSON=${ROUTES_JSON}" \
    --quiet

HUMAN_REACH_URL="$(
    gcloud run services describe "${HUMAN_REACH_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "HUMAN_REACH_URL=${HUMAN_REACH_URL}"


echo
echo "===== AUTHORIZE PUBSUB + GOOGLE CHAT INVOCATION ====="
gcloud run services add-iam-policy-binding \
    "${HUMAN_REACH_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${PUSH_SA}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

gcloud run services add-iam-policy-binding \
    "${HUMAN_REACH_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="serviceAccount:${CHAT_INVOKER}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null

echo "HUMAN_REACH_PRIVATE_INVOKERS_OK=1"

# Permit only the Pub/Sub service agent to mint the OIDC token for this push
# identity. This is narrower than granting token creation project-wide.
gcloud iam service-accounts add-iam-policy-binding \
    "${PUSH_SA}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${PUBSUB_SERVICE_AGENT}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --quiet >/dev/null

echo "HUMAN_REACH_PUSH_TOKEN_CREATOR_OK=1"


echo
echo "===== CONFIGURE AUTHENTICATED HUMAN REACH PUSH ====="
if gcloud pubsub subscriptions describe "${HUMAN_REACH_SUBSCRIPTION}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud pubsub subscriptions modify-push-config \
        "${HUMAN_REACH_SUBSCRIPTION}" \
        --project="${PROJECT_ID}" \
        --push-endpoint="${HUMAN_REACH_URL}/pubsub" \
        --push-auth-service-account="${PUSH_SA}" \
        --push-auth-token-audience="${HUMAN_REACH_URL}" \
        --quiet
    echo "SUBSCRIPTION_UPDATED=${HUMAN_REACH_SUBSCRIPTION}"
else
    gcloud pubsub subscriptions create \
        "${HUMAN_REACH_SUBSCRIPTION}" \
        --project="${PROJECT_ID}" \
        --topic="${HUMAN_REACH_TOPIC}" \
        --push-endpoint="${HUMAN_REACH_URL}/pubsub" \
        --push-auth-service-account="${PUSH_SA}" \
        --push-auth-token-audience="${HUMAN_REACH_URL}" \
        --dead-letter-topic="${DLQ_TOPIC}" \
        --max-delivery-attempts=5 \
        --min-retry-delay=10s \
        --max-retry-delay=60s \
        --quiet
    echo "SUBSCRIPTION_CREATED=${HUMAN_REACH_SUBSCRIPTION}"
fi


echo
echo "===== DEPLOY OPERATIONS UI WITH HUMAN REACH VISIBILITY ====="
EVIDENCE_URL="$(
    gcloud run services describe "${EVIDENCE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"
VERIFIER_URL="$(
    gcloud run services describe "${VERIFIER_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

gcloud run deploy "${OPERATIONS_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${OPERATIONS_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${OPERATIONS_SA}" \
    --no-allow-unauthenticated \
    --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL},EVIDENCE_SERVICE_URL=${EVIDENCE_URL},VERIFIER_SERVICE_URL=${VERIFIER_URL}" \
    --quiet


echo
echo "===== VERIFY HUMAN REACH DEPLOYMENT ====="
gcloud run services describe "${HUMAN_REACH_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='table(metadata.name,status.latestReadyRevisionName,spec.template.spec.serviceAccountName,status.url)'

gcloud pubsub subscriptions describe "${HUMAN_REACH_SUBSCRIPTION}" \
    --project="${PROJECT_ID}" \
    --format='yaml(topic,pushConfig.pushEndpoint,pushConfig.oidcToken,deadLetterPolicy,retryPolicy)'


echo
echo "===== GOOGLE CHAT CONFIGURATION REQUIRED ONCE ====="
echo "CHAT_APP_NAME=Next Shift Human Reach"
echo "CHAT_HTTP_ENDPOINT=${HUMAN_REACH_URL}"
echo "CHAT_AUTHENTICATION_AUDIENCE=HTTP endpoint URL"
echo "CHAT_FUNCTIONALITY=Join spaces and group conversations"
echo "CHAT_ROUTE_FACILITIES_OPS=Next Shift - Facilities Ops"
echo "CHAT_ROUTE_PATIENT_FLOW=Next Shift - Patient Flow"
echo "HUMAN_REACH_ROUTES_JSON=${ROUTES_JSON}"


echo
echo "HUMAN_REACH_DEPLOY_OK=1"
