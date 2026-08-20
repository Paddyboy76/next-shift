from __future__ import annotations

from typing import Any

from next_shift.persistence.evidence import (
    create_evidence,
    list_issue_evidence,
)
from next_shift.persistence.firestore import (
    update_issue_document,
)
from next_shift.workflows.handover import (
    get_issue,
    transition_issue,
)


TRUSTED_SOURCE = "synthetic_transport_system"
VERIFIER_ACTOR = "independent_verifier"


def record_transport_arrival(
    *,
    issue_id: str,
    transport_request_id: str,
    destination: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "PatientTransport":
        raise ValueError(
            f"Cannot record transport evidence for owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "ACTION_PENDING":
        raise ValueError(
            f"Expected ACTION_PENDING issue, got: "
            f"{issue['state']}"
        )

    if transport_request_id != issue.get(
        "transport_request_id"
    ):
        raise ValueError(
            "Transport request ID does not match"
        )

    if destination != issue.get(
        "transport_destination"
    ):
        raise ValueError(
            "Transport destination does not match"
        )

    evidence = create_evidence(
        issue_id=issue_id,
        evidence_type="transport_arrival",
        source=TRUSTED_SOURCE,
        subject=transport_request_id,
        details={
            "destination": destination,
            "status": "ARRIVED",
        },
    )

    update_issue_document(
        issue_id,
        {
            "transport_status": "ARRIVED",
        },
    )

    updated = transition_issue(
        issue_id=issue_id,
        new_state="VERIFYING",
        actor=TRUSTED_SOURCE,
        reason=(
            f"Trusted transport system confirmed "
            f"arrival at {destination}."
        ),
    )

    return {
        "issue": updated,
        "evidence": evidence,
    }


def verify_transport_and_close(
    issue_id: str,
) -> dict[str, Any]:
    issue = get_issue(issue_id)

    if issue["owner"] != "PatientTransport":
        raise ValueError(
            f"Verifier cannot close owner: "
            f"{issue['owner']}"
        )

    if issue["state"] != "VERIFYING":
        raise ValueError(
            f"Expected VERIFYING issue, got: "
            f"{issue['state']}"
        )

    request_id = issue.get(
        "transport_request_id"
    )
    destination = issue.get(
        "transport_destination"
    )

    matching = None

    for evidence in list_issue_evidence(issue_id):
        details = evidence.get("details", {})

        if (
            evidence.get("evidence_type")
            == "transport_arrival"
            and evidence.get("source")
            == TRUSTED_SOURCE
            and evidence.get("subject")
            == request_id
            and details.get("destination")
            == destination
            and details.get("status") == "ARRIVED"
        ):
            matching = evidence
            break

    if matching is None:
        raise ValueError(
            "Trusted transport arrival evidence not found; "
            "issue cannot be closed"
        )

    closed = transition_issue(
        issue_id=issue_id,
        new_state="CLOSED",
        actor=VERIFIER_ACTOR,
        reason=(
            f"Independent verifier accepted transport "
            f"evidence {matching['id']} confirming arrival "
            f"at {destination}."
        ),
    )

    return {
        "issue": closed,
        "evidence": matching,
    }
