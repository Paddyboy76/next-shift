# Reproducible deployment guide

This guide describes the deployed Next Shift topology in project `next-shift-506004`, region `asia-southeast1`. Deployment mutates live resources: inspect current state, IAM, revisions, and environment variables first.

## Prerequisites and preflight

- Google Cloud CLI authenticated to an identity authorized for the targeted resources
- Python 3.12 environment at `.venv`; `gcloud`, `curl`, `jq`, and Git
- Existing project service accounts, Firestore, IAP, APIs, Agent Runtime, Gateway, and Model Armor resources expected by the scripts
- Google Chat app/spaces when deploying Human Reach
- synthetic data only; no real hospital identifiers, images, or operational records

```bash
cd /home/patrick/next-shift
source .venv/bin/activate
gcloud config get-value project
git status --short --branch
git rev-parse HEAD
gcloud run services list --project next-shift-506004 --region asia-southeast1
```

Stop if the active project is not `next-shift-506004`.

## Deployment units

These are scoped deployment units, not a blind one-command installer:

| Script | Scope |
|---|---|
| `deploy_agent.py` | update existing managed ADK Agent Runtime |
| `deploy_agent_gateway.sh` | Agent Gateway and Model Armor binding |
| `deploy_secure_specialists.sh` | State Authority, six specialists, filtered Pub/Sub paths |
| `deploy_human_reach.sh` | original Human Reach / Google Chat deployment unit |
| `deploy_intake_path.sh` | State Authority and Operations intake |
| `deploy_verification_path.sh` | trusted evidence, verifier, Operations bindings |
| `deploy_critic_inspector.sh` | Coverage Critic, Evidence Inspector, verifier/Operations bindings |
| `deploy_recovery_planner.sh` | Recovery Planner and State Authority/Operations bindings |
| `deploy_spoken_handover.sh` | current Operations deployment with Gemini 3.5 spoken handover, photo-evidence audit access, and Human Reach refresh binding |
| `deploy_chat_photo_proof.sh` | current Human Reach Facilities photo-proof path plus the current Operations deployment |

Several older scripts redeploy shared services and may predate later environment bindings. Compare `--set-env-vars` and `--update-env-vars` behavior with the serving revision before use. For the final product, prefer the narrow current script associated with the changed path.

## Current Human Reach + photo-proof deployment

The final Facilities multimodal path uses Google Chat as the frontline submission surface and Operations as read-only audit display.

`deploy_chat_photo_proof.sh`:

1. verifies the active project;
2. resolves the trusted-evidence Cloud Run URL;
3. ensures the private `next-shift-506004-photo-evidence` bucket exists;
4. grants Human Reach only the required bucket, Vertex AI, and Trusted Evidence invocation permissions;
5. deploys Human Reach with `PHOTO_EVIDENCE_MODEL=gemini-3.5-flash`;
6. runs `deploy_spoken_handover.sh` to deploy the current Operations service with Gemini 3.5 speech, photo audit access, and Human Reach refresh binding.

For Cloud Shell sessions that may disconnect during source builds, run the deployment detached:

```bash
nohup bash /home/patrick/next-shift/deploy_chat_photo_proof.sh \
  > /tmp/chat-photo-deploy.log 2>&1 &

tail -f /tmp/chat-photo-deploy.log
```

Success ends with:

```text
SPOKEN_HANDOVER_DEPLOY_OK=1
CHAT_PHOTO_PROOF_DEPLOY_OK=1
PHOTO_EVIDENCE_MODEL=gemini-3.5-flash
```

## Existing-project rebuild order

The repository is reproducible for its existing synthetic project but does not claim zero-touch bootstrap of a brand-new Google Cloud organization/project.

For an authorized rebuild, use dependency order and validate after every unit:

1. `python deploy_agent.py`
2. `bash deploy_agent_gateway.sh`
3. `bash deploy_secure_specialists.sh`
4. deploy the trusted evidence / verifier / critic / inspector path
5. deploy Recovery Planner
6. deploy current Human Reach + Operations with `bash deploy_chat_photo_proof.sh`
7. run full readiness and live acceptance

Do not blindly run every historical deployment script in sequence after the final product is already serving. Shared-service environment values and IAM bindings must match the current architecture.

## Current critical runtime bindings

Final readiness expects, among other controls:

- State Authority is the sole Next Shift Firestore writer;
- Operations is the only direct Next Shift Firestore viewer;
- Operations invokes Coverage Critic, Recovery Planner, Trusted Evidence, Verifier, and Human Reach refresh only through their private Cloud Run paths;
- Human Reach accepts Pub/Sub delivery and authenticated Google Chat callbacks, refreshes cards from State Authority, and may invoke Trusted Evidence only for the accepted Facilities photo-proof path;
- Verifier invokes the independent Evidence Inspector;
- specialist Cloud Run services are callable only by their owner-specific Pub/Sub push identities;
- Operations uses `SPOKEN_HANDOVER_MODEL=gemini-3.5-flash`;
- Facilities photo proof uses `PHOTO_EVIDENCE_MODEL=gemini-3.5-flash` and the private synthetic photo bucket.

## Post-deployment proof

```bash
bash verify_readiness.sh
bash scripts/verify_gateway_model_armor_trace.sh

gcloud run services list \
  --project next-shift-506004 \
  --region asia-southeast1 \
  --format='table(metadata.name,status.latestReadyRevisionName,spec.template.spec.serviceAccountName,status.url)'
```

Final submission success requires clean current `main`, zero warnings, zero failures, and `NEXT_SHIFT_READINESS=PASS`.

Do not claim deployment success unless:

- the targeted revision is ready and receives 100% traffic;
- the expected service account is attached;
- IAM/invoker isolation passes;
- required Gemini 3.5 model env values are correct;
- the relevant real integration succeeds;
- authoritative records are inspectable;
- the final readiness gate passes.

Cloud Run uses bounded instances and scale-to-zero where configured; Pub/Sub drives specialists without manually supervised workers. Before rollback, identify the exact prior ready revision and verify its environment/IAM compatibility. Do not roll back State Authority independently from a changed contract consumer.
