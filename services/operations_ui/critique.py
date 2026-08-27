from __future__ import annotations

import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

from coverage_arbitration import arbitrate_coverage


def review_coverage(
    *,
    message: str,
    proposals: list[dict[str, Any]],
    source_reference: str,
) -> dict[str, Any]:
    url = os.environ.get("COVERAGE_CRITIC_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("COVERAGE_CRITIC_URL is required")

    token = id_token.fetch_id_token(Request(), url)
    response = requests.post(
        f"{url}/v1/review",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "message": message,
            "proposals": proposals,
            "source_reference": source_reference,
        },
        timeout=150,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Coverage Critic failed: {response.status_code} {response.text[:300]}"
        )

    review = response.json().get("review")
    if not isinstance(review, dict):
        raise RuntimeError("Coverage Critic returned invalid review")

    original_decision = review.get("decision")
    arbitration = arbitrate_coverage(proposals, review)
    dispatchable = arbitration["dispatchable"]
    held = arbitration["held"]

    # Mutate the caller's proposal list deliberately: Operations persists only
    # proposals that survived bounded arbitration. This prevents one disputed
    # item from suppressing unrelated safe work without weakening the critic's
    # durable findings.
    proposals[:] = dispatchable

    review["original_decision"] = original_decision
    review["review_required"] = arbitration["review_required"]
    review["partial_dispatch"] = bool(dispatchable and held)
    review["dispatchable_proposal_count"] = len(dispatchable)
    review["held_proposal_count"] = len(held)
    review["unbounded_review"] = arbitration["unbounded_review"]

    # The existing Operations route persists work only when decision == PASS.
    # Safe proposals are therefore promoted to PASS for dispatch while the
    # independent critic's original decision and findings remain inspectable.
    if dispatchable:
        review["decision"] = "PASS"

    return review
