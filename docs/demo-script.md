# Next Shift final demo script

## Objective

In four minutes, prove that Next Shift is a governed operational fleet—not a summarizer, chatbot collection, or decorative dashboard. Use only prepared synthetic operational data and live, already-verified product paths.

## 0:00–0:20 — opening

“Every 24/7 operation has the same failure point: work crosses a shift, context gets compressed, and nobody can prove what happened next. Next Shift does not summarize the handover. It finishes the operational work left behind by it.”

Show the IAP-protected Operations Control home screen.

Point once to the visible `Interpret → Route → Execute → Prove → Verify` chain. It is the structure of the demonstration, not a simulated progress indicator.

If the spoken path has been rehearsed successfully immediately before recording, record one short synthetic operational sentence, stop, and show the Gemini transcript plus audit reference. Review the text before sending. Otherwise use the prepared text directly; spoken input is optional and must never put the four-minute proof at risk.

## 0:20–0:55 — messy handover to governed work

Click **Load six-team synthetic handover**, review the prepared non-clinical text, then submit it. The button only fills the text box; submission still traverses the real governed path. The handover contains a missing wheelchair, interpreter coordination, home oxygen delivery, EVS turnaround, a leaking sink, and patient transport.

“The managed Agent Runtime decomposes one messy note into six typed proposals. A separate Gemini Coverage Critic checks for omissions, duplication, conflation, uncertainty, and routing errors. Only then does State Authority create durable Firestore work.”

Show all six owners and the critic result. Do not claim success until the queue visibly contains the expected issues.

## 0:55–1:20 — least-privilege execution

“Owner-filtered Pub/Sub wakes six dedicated Cloud Run specialists. Each has its own identity and can request only its owner-specific capabilities. State Authority is the only runtime identity that writes workflow truth.”

Show one issue progressing to `ACTION_PENDING` and its principal/capability trace entries.

## 1:20–2:05 — the trust boundary

Open a prepared Google Chat work card and click **Completed**.

“A frontline person says the work is complete. Next Shift records the claim—but does not trust it as proof.”

Show `CLAIMED · UNVERIFIED`. Record trusted synthetic evidence, then show `VERIFYING`.

“A separate Evidence Inspector checks the exact evidence issuer, provenance, subject, capability, timestamp, and coverage. Only after PASS may the independent verifier request closure.”

Run verification and show `CLOSED · VERIFIED`, including evidence ID, inspector identity/result, and verifier identity.

## 2:05–2:35 — trace and denial

Open `/trace/<issue_id>`.

“This trace is assembled from authoritative durable records: intake, event, route, specialist, human claim, evidence, inspection, verifier, and final state. Cloud Run request telemetry remains separately inspectable; we do not fabricate one distributed trace.”

Show the prepared stale-action denial: `decision=DENY`, reason `human_reach_stale_response`, expected `ACTION_PENDING`, current `CLOSED`. Confirm that issue state and Human Reach history did not change.

## 2:35–3:05 — controlled recovery

Open the prepared delayed/rejected operational work example and generate a Recovery Planner recommendation.

“Recovery is also least privilege. The planner can understand current state and recommend an allowlisted next action, but it cannot mutate work, record evidence, change owner, or close anything.”

Show the explicit Operations sanction and the `ADVISORY_NO_STATE_MUTATION_NO_CLOSURE` boundary. Then use the prepared proof of fresh evidence and independent closure; do not create a failure during recording.

## 3:05–3:30 — platform and memory

Show the architecture diagram and Operational Improvement Advisor.

“The ADK runtime uses managed Agent Identity and is registered in Agent Registry. Agent Gateway and fail-closed Model Armor govern the client-to-agent path. Gemini turns synthetic history into evidence-linked recommendations stored in Memory Bank, but memory is advisory only—Firestore remains current-state truth.”

Briefly show recommendation provenance and `may_mutate_workflow=false`.

## 3:30–3:50 — security proof

Show the prepared successful output of:

```bash
bash scripts/verify_gateway_model_armor_trace.sh
```

Point to benign HTTP 200, instruction-bypass HTTP 403, managed identity, fail-open false, and inspectable trace ID. The probe creates no operational work.

Show only the final readiness summary from clean current `main`: zero warnings, zero failures, `NEXT_SHIFT_READINESS=PASS`. Do not hard-code the pre-autonomy pass count as the current count.

## 3:50–4:00 — close

“Next Shift is built around one principle: no agent claim is trusted merely because an LLM said it. Operational truth must be persisted, permissioned, and verifiable. The handover ends. The work does not.”

## Recording checklist

Capture and rehearse these live facts in advance:

1. expected six-owner intake plus Coverage Critic result;
2. specialist principal/capability trace;
3. Google Chat claim remaining unverified;
4. evidence ID, inspection PASS, verifier identity, and closed state;
5. stale-action denial with unchanged state;
6. sanctioned recovery boundary and completed recovery proof;
7. Registry/Memory advisor provenance;
8. Gateway/Model Armor behavioral proof;
9. final clean-main readiness result.

If a live step fails, show the failure truthfully or use an already-inspected durable proof record. Never imply that a planned or configured feature executed when it did not.
