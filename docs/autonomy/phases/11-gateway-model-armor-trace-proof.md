# Mission 11 — Gateway + Model Armor Trace Proof

Prove the governed ingress/security path instead of merely describing it.

Verify:

- Agent Gateway is in the actual supported path;
- Model Armor policy is active;
- fail-open behavior is not silently weakening protection;
- bypass attempts are rejected or visibly constrained;
- prompt-injection/security events are inspectable;
- effective Agent Identity is visible;
- security outcomes can be traced to operational requests.

Do not rebuild working Gateway/Model Armor architecture unnecessarily.

Prefer proof, traceability, and regression protection over additional components.

Evidence file:

`docs/autonomy/evidence/11-gateway-model-armor-trace-proof.md`
