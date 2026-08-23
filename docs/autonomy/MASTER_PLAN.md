# Next Shift — Autonomous Final Attack

## Mission

Finish Next Shift to the strongest defensible submission for Google's All Things Agentic Hackathon, targeting Fortified Enterprise Fleet and the Grand Prize.

Core statement:

**Next Shift does not summarize the handover. It finishes the operational work left behind by it.**

The synthetic hospital is the demonstration environment. The product is for shift handovers and operational continuity across general 24/7 enterprise operations.

## Authority

Before every phase:

1. Read `AGENTS.md` completely.
2. Verify current Git state.
3. Inspect relevant live Google Cloud state.
4. Treat repository state and deployed GCP state as authoritative.
5. Do not assume earlier documentation is still current.

## Golden baseline

Starting `main`:

`ce7baed79f07ecfb958225f37291d7949312e342`

Production readiness before autonomous work:

- PASS: 159
- WARN: 0
- FAIL: 0
- NEXT_SHIFT_READINESS=PASS

Never knowingly leave production weaker than this baseline.

## Hard boundaries

- Synthetic data only.
- No proprietary hospital data, systems, branding, screenshots, identifiers, or workflows.
- Do not mention interviews, interview findings, user validation, validation interviews, nursing-director interviews, or any similar source in product copy, documentation, submission copy, demo material, or public explanation.
- Non-clinical operations only.
- Do not add clinical workflows.
- Do not add medication, dietary, diagnostic, treatment, or clinical-decision functionality.
- Existing deterministic safety-boundary regressions may remain, but do not expand clinical content or make it part of the public demo.
- Firestore remains authoritative workflow truth.
- Memory is advisory historical context only.
- Specialists may never self-certify closure.
- Trusted evidence and independent verification remain mandatory.
- Least privilege must remain technically enforced.
- Invalid and unauthorized actions must fail visibly.
- Do not weaken security or evidence requirements to make a demo pass.
- Do not fabricate telemetry, integrations, evidence, completion, judge results, or deployment status.
- Do not replace real GCP integrations with presentation mocks.
- Do not make unnecessary architectural rewrites.
- Keep modules focused and modular.
- Do not change Git branch.
- Do not commit, push, merge, or create PRs. The controller owns Git.

## Judge strategy

Previous independent judge reviews converged on these points:

Strongest:
- real autonomous operational execution;
- durable state across shifts;
- least-privilege specialist fleet;
- evidence-backed independent closure;
- real deployed Google Cloud architecture.

Highest-value gaps:
- evidence independence must be unmistakable;
- Agent Registry / lifecycle should be real and visible where valuable;
- Memory Bank should provide useful operational intelligence without becoming workflow truth;
- native Agent Observability / OpenTelemetry should be judge-visible;
- Agent Gateway + Model Armor must be proven in the actual path, not merely configured;
- controlled recovery/replanning is high-value;
- visible Gemini multimodality can improve judge impact if it is genuinely integrated.

Prioritized enhancements:
1. Registry / lifecycle / observability gaps.
2. Evidence independence and evidence inspection.
3. Vision-backed operational evidence.
4. Controlled Recovery Planner.
5. Spoken handover only after the system remains green.

Rejected low-value gimmicks:
- maps unless operationally necessary;
- Veo;
- Lyria;
- decorative model proliferation;
- chain-of-thought displays;
- presentation-only fake functionality.

## Development discipline

For every meaningful change:

inspect
→ implement
→ syntax/test
→ deploy if required
→ run real integration
→ inspect authoritative state/evidence
→ rerun readiness
→ document evidence

Tests should protect meaningful behavior, not inflate test counts.

## Phase completion contract

Every phase must create:

`docs/autonomy/evidence/<phase-name>.md`

The evidence file must state:

- what was inspected;
- what was changed;
- what was deliberately not changed;
- exact validation performed;
- relevant live GCP evidence;
- remaining risks;
- `PHASE_RESULT: PASS`

Only write `PHASE_RESULT: PASS` if the phase goal is genuinely satisfied.

If a material blocker prevents completion, write:

`PHASE_RESULT: BLOCKED`

and explain the blocker.

Do not falsely declare success.

## Final goal

The final deployed product should visibly prove:

messy operational handover
→ structured issues
→ deterministic routing
→ least-privilege specialists
→ operational execution
→ durable authoritative state
→ trusted evidence
→ independent verification
→ closure
→ cross-shift continuity
→ historical operational intelligence
→ controlled recovery when execution fails

with judge-visible security, observability, and real Google platform leverage.
