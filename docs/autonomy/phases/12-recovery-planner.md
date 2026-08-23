# Mission 12 — Controlled Recovery Planner

Add or strengthen controlled operational replanning where it produces real enterprise value.

The Recovery Planner should help when work becomes blocked, delayed, rejected, or verification fails.

It may use:

- authoritative current Firestore state;
- trusted failure evidence;
- advisory historical Memory context;
- SLA/history patterns.

It must not:

- invent completion;
- bypass policy;
- directly override authoritative state;
- self-close work;
- silently broaden specialist authority.

Desired judge-visible behavior:

failure
→ reason understood
→ safe alternative/recommendation
→ sanctioned action or human review
→ evidence
→ independent verification

Keep this generalizable to 24/7 enterprise operations.

Evidence file:

`docs/autonomy/evidence/12-recovery-planner.md`
