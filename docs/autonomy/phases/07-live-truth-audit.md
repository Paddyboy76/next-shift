# Mission 07 — Live Truth Audit

Perform an adversarial audit of current `main`-derived branch and the live project `next-shift-506004`.

Goals:

- establish current repository and deployed truth;
- run relevant tests and readiness verification;
- inspect Cloud Run, Firestore authority, Pub/Sub, DLQ, Agent Runtime, Agent Identity, Gateway, Model Armor, observability, UI, Human Reach, evidence path and verifier;
- identify documentation/deployment drift;
- identify anything that is claimed but not actually deployed or proven;
- fix only material correctness, deployment, security, reliability, or judge-visible truth gaps.

Do not add speculative features in this phase.

Finish with a clean, deployed, reproducible foundation for later missions.

Evidence file:

`docs/autonomy/evidence/07-live-truth-audit.md`
