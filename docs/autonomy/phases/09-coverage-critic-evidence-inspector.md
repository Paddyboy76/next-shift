# Mission 09 — Coverage Critic + Evidence Inspector

Strengthen the perception and reality that Next Shift is an agentic fleet rather than one intake LLM wrapped in microservices.

Evaluate and implement, where materially useful:

- an independent Coverage Critic that examines whether messy handover intake missed, duplicated, conflated, or incorrectly routed operational work;
- an Evidence Inspector that independently evaluates evidence coverage/provenance before verification;
- an independent model role such as Gemma only where it creates genuine architectural independence.

Rules:

- critics do not mutate authoritative Firestore state directly;
- critics do not replace deterministic routing, policy, or verifier authority;
- disagreements must be visible;
- uncertain cases may route to human review;
- do not add model calls merely to increase model count.

Evidence file:

`docs/autonomy/evidence/09-coverage-critic-evidence-inspector.md`
