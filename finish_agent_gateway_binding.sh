#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"
ENGINE_ID="8140616966286082048"

GATEWAY="next-shift-ingress"
REGISTRY_SERVICE="next-shift-runtime"

ENGINE_URL="https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${ENGINE_ID}"
GATEWAY_RESOURCE="projects/${PROJECT_ID}/locations/${REGION}/agentGateways/${GATEWAY}"

echo "===== VERIFY PROJECT ====="

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "ERROR: active project=${ACTIVE_PROJECT}"
    exit 1
fi

echo "project=${ACTIVE_PROJECT}"

echo
echo "===== ENABLE REQUIRED APIS ====="

gcloud services enable \
    agentregistry.googleapis.com \
    iap.googleapis.com \
    --project="${PROJECT_ID}"

echo
echo "===== CURRENT RUNTIME BINDING ====="

CURRENT_CONFIG="$(
    curl -fsS \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        "${ENGINE_URL}" \
        | jq -c '.spec.deploymentSpec.agentGatewayConfig'
)"

echo "${CURRENT_CONFIG}" | jq .

if [[ "${CURRENT_CONFIG}" == "null" ]]; then
    echo
    echo "===== BIND RUNTIME TO CLIENT-TO-AGENT GATEWAY ====="

    curl -fsS \
        -X PATCH \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{
          \"spec\": {
            \"deploymentSpec\": {
              \"agentGatewayConfig\": {
                \"clientToAgentConfig\": {
                  \"agentGateway\": \"${GATEWAY_RESOURCE}\"
                }
              }
            }
          }
        }" \
        "${ENGINE_URL}?updateMask=spec.deploymentSpec.agentGatewayConfig" \
        >/tmp/next-shift-gateway-patch.json

    echo "PATCH_ACCEPTED"
    cat /tmp/next-shift-gateway-patch.json | jq .

    echo
    echo "===== WAIT FOR RUNTIME UPDATE ====="

    BOUND="false"

    for attempt in $(seq 1 36)
    do
        CONFIG="$(
            curl -fsS \
                -H "Authorization: Bearer $(gcloud auth print-access-token)" \
                "${ENGINE_URL}" \
                | jq -c '.spec.deploymentSpec.agentGatewayConfig'
        )"

        echo "attempt=${attempt} config=${CONFIG}"

        if [[ "${CONFIG}" != "null" ]]; then
            BOUND="true"
            break
        fi

        sleep 5
    done

    if [[ "${BOUND}" != "true" ]]; then
        echo "ERROR: Runtime still not bound to Agent Gateway"
        exit 1
    fi
fi

echo
echo "===== VERIFY MANAGED AGENT IDENTITY ====="

EFFECTIVE_IDENTITY="$(
    curl -fsS \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        "${ENGINE_URL}" \
        | jq -r '.spec.effectiveIdentity // ""'
)"

echo "effective_identity=${EFFECTIVE_IDENTITY}"

if [[ "${EFFECTIVE_IDENTITY}" != agents.global.* ]]; then
    echo "ERROR: managed Agent Identity not present"
    exit 1
fi

echo
echo "===== REGISTER RUNTIME IN AGENT REGISTRY ====="

if gcloud agent-registry services describe \
    "${REGISTRY_SERVICE}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    >/dev/null 2>&1
then
    echo "REGISTRY_SERVICE_EXISTS"

    REGISTRY_RESOURCE="$(
        gcloud agent-registry services describe \
            "${REGISTRY_SERVICE}" \
            --project="${PROJECT_ID}" \
            --location="${REGION}" \
            --format='value(registryResource)'
    )"
else
    REGISTRY_RESOURCE="$(
        gcloud agent-registry services create \
            "${REGISTRY_SERVICE}" \
            --project="${PROJECT_ID}" \
            --location="${REGION}" \
            --display-name="Next Shift Runtime" \
            --endpoint-spec-type=no-spec \
            --interfaces="url=https://${REGION}-aiplatform.mtls.googleapis.com/v1/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${ENGINE_ID},protocolBinding=jsonrpc" \
            --format='value(registryResource)'
    )"
fi

echo "registry_resource=${REGISTRY_RESOURCE}"

if [[ -z "${REGISTRY_RESOURCE}" ]]; then
    echo "ERROR: registry resource missing"
    exit 1
fi

ENDPOINT_ID="${REGISTRY_RESOURCE##*/}"
MEMBER="principal://${EFFECTIVE_IDENTITY}"

echo
echo "===== AUTHORIZE AGENT IDENTITY TO REGISTRY ====="

gcloud iap web add-iam-policy-binding \
    --resource-type=agent-registry \
    --endpoint="${ENDPOINT_ID}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="roles/iap.egressor"

echo
echo "===== FINAL RUNTIME BINDING ====="

curl -fsS \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    "${ENGINE_URL}" \
    | jq '.spec.deploymentSpec.agentGatewayConfig'

echo
echo "===== REGISTERED RUNTIME ====="

gcloud agent-registry services describe \
    "${REGISTRY_SERVICE}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --format='yaml(name,displayName,registryResource,interfaces)'

echo
echo "===== GATEWAY ====="

gcloud network-services agent-gateways describe \
    "${GATEWAY}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --format='yaml(name,googleManaged)'

echo
echo "AGENT_GATEWAY_BINDING_OK"
