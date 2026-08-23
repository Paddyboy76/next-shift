# Reproducible deployment guide

This guide describes the deployed Next Shift topology in project `next-shift-506004`, region `asia-southeast1`. Deployment mutates live resources: inspect current state, IAM, revisions, and environment variables first.

## Prerequisites and preflight

- Google Cloud CLI authenticated to an identity authorized for the targeted resources
- Python 3.12 environment at `.venv`; `gcloud`, `curl`, `jq`, and Git
- Existing project service accounts, Firestore, staging bucket, IAP, and APIs expected by the scripts
- Google Chat app/spaces only when deploying Human Reach; no Chat space IDs or real user addresses in source control

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
| `deploy_human_reach.sh` | Human Reach, Google Chat delivery, Operations dependencies |
| `deploy_intake_path.sh` | State Authority and Operations intake |
| `deploy_verification_path.sh` | trusted evidence, verifier, Operations bindings |
| `deploy_critic_inspector.sh` | Coverage Critic, Evidence Inspector, verifier/Operations bindings |
| `deploy_recovery_planner.sh` | Recovery Planner and State Authority/Operations bindings |

Several scripts redeploy shared services. Compare their `--set-env-vars` and `--update-env-vars` behavior with the serving revision before use so a targeted deployment does not erase later bindings. Prefer the narrow unit associated with the source change.

## Existing-project rebuild order

The repository is reproducible for its existing synthetic project but does not claim zero-touch bootstrap of a new Google Cloud project. For an authorized rebuild, use dependency order and validate after every unit:

1. `python deploy_agent.py`
2. `bash deploy_agent_gateway.sh`
3. `bash deploy_secure_specialists.sh`
4. `bash deploy_human_reach.sh`
5. `bash deploy_intake_path.sh`
6. `bash deploy_verification_path.sh`
7. `bash deploy_critic_inspector.sh`
8. `bash deploy_recovery_planner.sh`

Preserve the complete current environment set when shared services are redeployed. Human Reach setup is documented in `docs/human-reach-google-chat-setup.md`.

## Post-deployment proof

```bash
bash verify_readiness.sh
bash scripts/verify_gateway_model_armor_trace.sh
gcloud run services list \
  --project next-shift-506004 \
  --region asia-southeast1 \
  --format='table(metadata.name,status.latestReadyRevisionName,spec.template.spec.serviceAccountName,status.url)'
```

Do not claim success unless the targeted revision is ready at 100% traffic, IAM/invoker checks pass, the relevant real integration succeeds, authoritative records are inspectable, and readiness ends with zero warnings/failures on clean current `main`.

Cloud Run uses bounded instances and scale-to-zero where configured; Pub/Sub drives specialists without manually supervised workers. Before rollback, identify the exact prior ready revision and verify its environment/IAM compatibility. Do not roll back State Authority independently from a changed contract consumer.

