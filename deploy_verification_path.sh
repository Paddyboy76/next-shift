#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
REGION="asia-southeast1"
REPO="/home/patrick/next-shift"

STATE_SERVICE="next-shift-state-authority"
STATE_SA="ns-state-authority@${PROJECT_ID}.iam.gserviceaccount.com"
EVIDENCE_SERVICE="next-shift-trusted-evidence"
EVIDENCE_SA_NAME="ns-trusted-evidence"
EVIDENCE_SA="${EVIDENCE_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
VERIFIER_SERVICE="next-shift-verifier"
VERIFIER_SA_NAME="ns-verifier"
VERIFIER_SA="${VERIFIER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
OPERATIONS_SERVICE="next-shift-operations"
OPERATIONS_SA="ns-operations-ui@${PROJECT_ID}.iam.gserviceaccount.com"
BUILDER_SA="ns-cloud-run-builder@${PROJECT_ID}.iam.gserviceaccount.com"
TOPIC="next-shift-handover-received"
HUMAN_REACH_TOPIC="next-shift-human-reach-requested"

STATE_DIR="${REPO}/services/state_authority"
EVIDENCE_DIR="${REPO}/services/evidence_runtime"
VERIFIER_DIR="${REPO}/services/verifier_runtime"
OPERATIONS_DIR="${REPO}/services/operations_ui"


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
echo "===== VERIFY SOURCE ====="
test -f "${STATE_DIR}/evidence.py"
test -f "${EVIDENCE_DIR}/main.py"
test -f "${VERIFIER_DIR}/main.py"
test -f "${OPERATIONS_DIR}/completion.py"
echo "SOURCE_OK=1"


echo
echo "===== ENSURE SERVICE IDENTITIES ====="
if ! gcloud iam service-accounts describe "${EVIDENCE_SA}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${EVIDENCE_SA_NAME}" \
        --project="${PROJECT_ID}" \
        --display-name="Next Shift Trusted Evidence" \
        --quiet
fi

if ! gcloud iam service-accounts describe "${VERIFIER_SA}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${VERIFIER_SA_NAME}" \
        --project="${PROJECT_ID}" \
        --display-name="Next Shift Independent Verifier" \
        --quiet
fi

echo "EVIDENCE_SA=${EVIDENCE_SA}"
echo "VERIFIER_SA=${VERIFIER_SA}"


echo
echo "===== ENFORCE NO DIRECT FIRESTORE ACCESS ====="
assert_no_direct_data_roles "${EVIDENCE_SA}"
assert_no_direct_data_roles "${VERIFIER_SA}"
echo "COMPLETION_IDENTITIES_NO_DIRECT_DATA_ROLES=1"


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
    --set-env-vars="STATE_AUTHORITY_AUDIENCE=${STATE_URL},HUMAN_REACH_TOPIC=${HUMAN_REACH_TOPIC}" \
    --quiet

STATE_URL="$(
    gcloud run services describe "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "STATE_AUTHORITY_URL=${STATE_URL}"


echo
echo "===== STATE AUTHORITY IAM ====="
for MEMBER in "${OPERATIONS_SA}" "${EVIDENCE_SA}" "${VERIFIER_SA}"; do
    gcloud run services add-iam-policy-binding \
        "${STATE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --member="serviceAccount:${MEMBER}" \
        --role="roles/run.invoker" \
        --quiet >/dev/null
done

echo "STATE_AUTHORITY_INVOKERS_OK=1"

gcloud pubsub topics add-iam-policy-binding \
    "${TOPIC}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${STATE_SA}" \
    --role="roles/pubsub.publisher" \
    --quiet >/dev/null


echo
echo "===== DEPLOY TRUSTED EVIDENCE ====="
gcloud run deploy "${EVIDENCE_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${EVIDENCE_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${EVIDENCE_SA}" \
    --no-allow-unauthenticated \
    --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL}" \
    --quiet

EVIDENCE_URL="$(
    gcloud run services describe "${EVIDENCE_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "EVIDENCE_SERVICE_URL=${EVIDENCE_URL}"


echo
echo "===== DEPLOY INDEPENDENT VERIFIER ====="
gcloud run deploy "${VERIFIER_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --source="${VERIFIER_DIR}" \
    --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILDER_SA}" \
    --service-account="${VERIFIER_SA}" \
    --no-allow-unauthenticated \
    --set-env-vars="STATE_AUTHORITY_URL=${STATE_URL}" \
    --quiet

VERIFIER_URL="$(
    gcloud run services describe "${VERIFIER_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='value(status.url)'
)"

echo "VERIFIER_SERVICE_URL=${VERIFIER_URL}"


echo
echo "===== OPERATIONS TO COMPLETION SERVICES IAM ====="
for SERVICE in "${EVIDENCE_SERVICE}" "${VERIFIER_SERVICE}"; do
    gcloud run services add-iam-policy-binding \
        "${SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --member="serviceAccount:${OPERATIONS_SA}" \
        --role="roles/run.invoker" \
        --quiet >/dev/null
done

echo "OPERATIONS_COMPLETION_INVOKERS_OK=1"


echo
echo "===== DEPLOY OPERATIONS UI ====="
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
echo "===== VERIFY IDENTITIES ====="
for SERVICE in "${STATE_SERVICE}" "${EVIDENCE_SERVICE}" "${VERIFIER_SERVICE}" "${OPERATIONS_SERVICE}"; do
    gcloud run services describe "${SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format='table(metadata.name,status.latestReadyRevisionName,spec.template.spec.serviceAccountName)'
done


echo
echo "===== VERIFY OPERATIONS ENV ====="
gcloud run services describe "${OPERATIONS_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='yaml(spec.template.spec.containers[0].env)'


echo
echo "FORTIFIED_VERIFICATION_DEPLOY_OK=1"
