from __future__ import annotations

from typing import Any


BLOCKING_FINDING_TYPES = frozenset({
    "DUPLICATED",
    "CONFLATED",
    "MISROUTED",
})


def arbitrate_coverage(
    proposals: list[dict[str, Any]],
    coverage_review: dict[str, Any],
) -> dict[str, Any]:
    """Keep safe work moving while isolating critic-disputed proposals.

    The Coverage Critic is advisory over intake coverage. An UNCERTAIN finding
    should remain visible to operators but must not become a global kill switch
    when the proposed work is still safe to dispatch. Findings that indicate a
    proposal is duplicated, conflated, or misrouted quarantine only the
    implicated proposals. A malformed blocking finding with no usable proposal
    index falls back to full review because its blast radius cannot be bounded.
    """

    findings = coverage_review.get("findings")
    if not isinstance(findings, list):
        return {
            "dispatchable": [],
            "held": list(proposals),
            "review_required": True,
            "unbounded_review": True,
        }

    blocked_indexes: set[int] = set()
    unbounded_review = False

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        finding_type = str(finding.get("type") or "").upper()
        if finding_type not in BLOCKING_FINDING_TYPES:
            continue

        raw_indexes = finding.get("proposal_indexes")
        valid_indexes = {
            index
            for index in raw_indexes
            if isinstance(index, int) and 0 <= index < len(proposals)
        } if isinstance(raw_indexes, list) else set()

        if not valid_indexes:
            unbounded_review = True
            continue

        blocked_indexes.update(valid_indexes)

    if unbounded_review:
        blocked_indexes = set(range(len(proposals)))

    dispatchable = [
        proposal
        for index, proposal in enumerate(proposals)
        if index not in blocked_indexes
    ]
    held = [
        proposal
        for index, proposal in enumerate(proposals)
        if index in blocked_indexes
    ]

    return {
        "dispatchable": dispatchable,
        "held": held,
        "review_required": bool(held) or coverage_review.get("decision") != "PASS",
        "unbounded_review": unbounded_review,
    }
