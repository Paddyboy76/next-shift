#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="next-shift-506004"
PROJECT_NUMBER="963749706976"
REGION="asia-southeast1"
REASONING_ENGINE_ID="8140616966286082048"

GATEWAY="next-shift-ingress"
TEMPLATE="next-shift-intake-guard"

AUTHZ_EXTENSION="${GATEWAY}-model-armor"
AUTHZ_POLICY="${GATEWAY}-model-armor-policy"

CFG_DIR="/home/patrick/next-shift/gateway"

DEP_SA="service-${PROJECT_NUMBER}@gcp-sa-dep.iam.gserviceaccount.com"
RE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

mkdir -p "${CFG_DIR}"

echo "===== VERIFY PROJECT ====="

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "ERROR: active project is ${ACTIVE_PROJECT}"
    exit 1
fi

echo "project=${ACTIVE_PROJECT}"

echo
echo "===== ENABLE GATEWAY APIS ====="

gcloud services enable \
    networkservices.googleapis.com \
    networksecurity.googleapis.com \
    serviceusage.googleapis.com \
    modelarmor.googleapis.com \
    --project="${PROJECT_ID}"

echo
echo "===== VERIFY EXISTING AGENT IDENTITY ====="

ENGINE_JSON="$(
    curl -fsS \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${REASONING_ENGINE_ID}"
)"

EFFECTIVE_IDENTITY="$(
    printf '%s' "${ENGINE_JSON}" \
        | jq -r '.spec.effectiveIdentity // ""'
)"

echo "effective_identity=${EFFECTIVE_IDENTITY}"

if [[ "${EFFECTIVE_IDENTITY}" != agents.global.* ]]; then
    echo "ERROR: Reasoning Engine is not using managed Agent Identity."
    echo "Do not bind the gateway until this is resolved."
    exit 1
fi

echo "AGENT_IDENTITY_OK"

echo
echo "===== CREATE CLIENT-TO-AGENT GATEWAY ====="

cat > "${CFG_DIR}/${GATEWAY}.yaml" <<EOF
name: ${GATEWAY}
protocols:
  - MCP
googleManaged:
  governedAccessPath: CLIENT_TO_AGENT
EOF

gcloud network-services agent-gateways import \
    "${GATEWAY}" \
    --source="${CFG_DIR}/${GATEWAY}.yaml" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet

echo
echo "===== VERIFY GATEWAY ====="

gcloud network-services agent-gateways describe \
    "${GATEWAY}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="yaml(name,state,googleManaged,agentGatewayCard)"

echo
echo "===== GRANT MODEL ARMOR CALLOUT PERMISSIONS ====="

for ROLE in \
    roles/modelarmor.calloutUser \
    roles/serviceusage.serviceUsageConsumer \
    roles/modelarmor.user
do
    gcloud projects add-iam-policy-binding \
        "${PROJECT_ID}" \
        --member="serviceAccount:${DEP_SA}" \
        --role="${ROLE}" \
        --quiet >/dev/null
done

for ROLE in \
    roles/modelarmor.calloutUser \
    roles/modelarmor.user
do
    gcloud projects add-iam-policy-binding \
        "${PROJECT_ID}" \
        --member="serviceAccount:${RE_SA}" \
        --role="${ROLE}" \
        --quiet >/dev/null
done

echo "MODEL_ARMOR_IAM_OK"

echo
echo "===== CREATE MODEL ARMOR AUTHORIZATION EXTENSION ====="

cat > "${CFG_DIR}/${AUTHZ_EXTENSION}.yaml" <<EOF
name: ${AUTHZ_EXTENSION}
service: modelarmor.${REGION}.rep.googleapis.com
metadata:
  model_armor_settings: '[
    {
      "request_template_id": "projects/${PROJECT_ID}/locations/${REGION}/templates/${TEMPLATE}",
      "response_template_id": "projects/${PROJECT_ID}/locations/${REGION}/templates/${TEMPLATE}"
    }
  ]'
failOpen: false
timeout: 5s
EOF

gcloud service-extensions authz-extensions import \
    "${AUTHZ_EXTENSION}" \
    --source="${CFG_DIR}/${AUTHZ_EXTENSION}.yaml" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet

echo
echo "===== CREATE CONTENT AUTHORIZATION POLICY ====="

cat > "${CFG_DIR}/${AUTHZ_POLICY}.yaml" <<EOF
name: ${AUTHZ_POLICY}
target:
  resources:
    - "projects/${PROJECT_ID}/locations/${REGION}/agentGateways/${GATEWAY}"
policyProfile: CONTENT_AUTHZ
action: CUSTOM
customProvider:
  authzExtension:
    resources:
      - "projects/${PROJECT_ID}/locations/${REGION}/authzExtensions/${AUTHZ_EXTENSION}"
EOF

gcloud beta network-security authz-policies import \
    "${AUTHZ_POLICY}" \
    --source="${CFG_DIR}/${AUTHZ_POLICY}.yaml" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet

echo
echo "===== VERIFY MODEL ARMOR POLICY ====="

gcloud beta network-security authz-policies describe \
    "${AUTHZ_POLICY}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="yaml(name,policyProfile,action,target,customProvider)"

echo
echo "===== BIND EXISTING AGENT RUNTIME TO GATEWAY ====="

GATEWAY_RESOURCE="projects/${PROJECT_ID}/locations/${REGION}/agentGateways/${GATEWAY}"

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
    "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${REASONING_ENGINE_ID}?updateMask=spec.deploymentSpec.agentGatewayConfig" \
    >/tmp/next-shift-gateway-bind.json

cat /tmp/next-shift-gateway-bind.json | jq '.spec.deploymentSpec.agentGatewayConfig'

echo
echo "===== VERIFY LIVE RUNTIME BINDING ====="

curl -fsS \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${REASONING_ENGINE_ID}" \
    | jq '.spec.deploymentSpec.agentGatewayConfig'

echo
echo "===== VERIFY RESOURCES ====="

gcloud network-services agent-gateways list \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="table(name.basename(),state)"

gcloud service-extensions authz-extensions list \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="table(name.basename(),service,failOpen)"

gcloud beta network-security authz-policies list \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="table(name.basename(),policyProfile,action)"

echo
echo "AGENT_GATEWAY_MODEL_ARMOR_OK"
