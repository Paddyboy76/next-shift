from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _event(
    *,
    stage: str,
    title: str,
    at: Any,
    actor: Any = None,
    authority: str,
    status: str,
    identifiers: dict[str, Any] | None = None,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "stage": stage,
        "title": title,
        "at": _text(at),
        "actor": _text(actor),
        "authority": authority,
        "status": status,
        "identifiers": {
            key: _text(value)
            for key, value in (identifiers or {}).items()
            if value not in {None, ""}
        },
        "detail": detail,
    }


def build_lifecycle_trace(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    issue = bundle.get("issue") or {}
    transitions = list(bundle.get("transitions") or [])
    evidence = list(bundle.get("evidence") or [])
    human_reach = bundle.get("human_reach") or None
    verification_attempts = list(bundle.get("verification_attempts") or [])
    recovery_plans = list(bundle.get("recovery_plans") or [])

    issue_id = _text(issue.get("id"))
    owner = _text(issue.get("owner"))
    items: list[dict[str, Any]] = []

    items.append(
        _event(
            stage="INTAKE",
            title="Governed handover persisted",
            at=issue.get("created_at"),
            actor=issue.get("intake_principal"),
            authority="State Authority",
            status="RECEIVED",
            identifiers={
                "issue_id": issue_id,
                "source_reference": issue.get("source_reference"),
                "handover_event_id": issue.get("handover_received_event_id"),
                "handover_message_id": issue.get("handover_received_message_id"),
            },
            detail=(
                "The intake runtime proposed operational work; State Authority "
                "persisted the durable issue and published its routed event."
            ),
        )
    )

    transitions.sort(
        key=lambda item: _text(
            item.get("committed_at")
            or item.get("authority_observed_at")
        )
    )

    for transition in transitions:
        to_state = _text(transition.get("to_state")) or "UNKNOWN"
        from_state = _text(transition.get("from_state")) or "START"
        capability = _text(transition.get("capability"))
        stage = "SPECIALIST"
        authority = "State Authority"

        if capability == "evidence.record":
            stage = "EVIDENCE"
        elif capability == "verification.close":
            stage = "VERIFIER"
        elif capability == "verification.reject":
            stage = "VERIFICATION_FAILURE"

        items.append(
            _event(
                stage=stage,
                title=f"{from_state} → {to_state}",
                at=(
                    transition.get("committed_at")
                    or transition.get("authority_observed_at")
                ),
                actor=transition.get("principal"),
                authority=authority,
                status=to_state,
                identifiers={
                    "transition_event_id": transition.get("id"),
                    "capability": capability,
                },
                detail=_text(transition.get("reason")),
            )
        )

    if human_reach:
        items.append(
            _event(
                stage="HUMAN_REACH",
                title="Frontline work delivered",
                at=(
                    human_reach.get("delivered_at")
                    or human_reach.get("requested_at")
                ),
                actor="ns-human-reach",
                authority="Human Reach / Google Chat",
                status=_text(human_reach.get("delivery_status")) or "PENDING",
                identifiers={
                    "human_reach_event_id": human_reach.get("human_reach_event_id"),
                    "human_reach_message_id": human_reach.get("human_reach_message_id"),
                    "chat_message": human_reach.get("chat_message_name"),
                    "destination": human_reach.get("destination_display_name"),
                    "work_order": human_reach.get("work_order"),
                },
                detail=(
                    f"WHO: {_text(human_reach.get('who'))} · "
                    f"WHAT: {_text(human_reach.get('what'))} · "
                    f"WHERE: {_text(human_reach.get('where'))}"
                ),
            )
        )

        for response in human_reach.get("response_history") or []:
            items.append(
                _event(
                    stage="HUMAN_REACH",
                    title=(
                        f"Frontline response: "
                        f"{_text(response.get('to_status') or response.get('action'))}"
                    ),
                    at=response.get("at"),
                    actor=(
                        response.get("actor_display_name")
                        or response.get("actor_user")
                    ),
                    authority="Human Reach",
                    status=_text(
                        response.get("to_status")
                        or response.get("action")
                    ),
                    identifiers={
                        "actor_user": response.get("actor_user"),
                    },
                    detail=(
                        "A frontline response is coordination evidence only; "
                        "it does not independently mutate or close operational truth."
                    ),
                )
            )

    evidence.sort(
        key=lambda item: _text(item.get("created_at"))
    )

    for item in evidence:
        items.append(
            _event(
                stage="EVIDENCE",
                title=f"Trusted evidence: {_text(item.get('evidence_type'))}",
                at=item.get("created_at"),
                actor=item.get("recorded_by"),
                authority="Trusted Evidence",
                status=(
                    "VERIFIED"
                    if item.get("verified_by")
                    else "RECORDED"
                ),
                identifiers={
                    "evidence_id": item.get("id"),
                    "source": item.get("source"),
                    "subject": item.get("subject"),
                    "verified_by": item.get("verified_by"),
                    "schema_version": item.get("schema_version"),
                    "provenance_authority": (item.get("provenance") or {}).get("authority"),
                    "observation_mode": (item.get("provenance") or {}).get("observation_mode"),
                    "observed_at": (item.get("provenance") or {}).get("observed_at"),
                },
                detail=_text(item.get("details")),
            )
        )

    for attempt in verification_attempts:
        items.append(_event(
            stage="VERIFICATION_FAILURE",
            title="Independent verification rejected",
            at=attempt.get("created_at"),
            actor=attempt.get("verifier"),
            authority="State Authority",
            status="RECOVERABLE",
            identifiers={
                "verification_attempt_id": attempt.get("id"),
                "evidence_id": attempt.get("evidence_id"),
                "recovery_state": attempt.get("recovery_state"),
            },
            detail=(
                f"Reason: {_text(attempt.get('reason'))}. "
                "No closure occurred; work returned for new trusted evidence."
            ),
        ))

    for plan in recovery_plans:
        items.append(_event(
            stage="CONTROLLED_RECOVERY",
            title=f"Recovery plan {str(plan.get('status', 'PROPOSED')).lower()}",
            at=plan.get("sanctioned_at") or plan.get("created_at"),
            actor=plan.get("sanctioned_by") or plan.get("planner"),
            authority="State Authority",
            status=_text(plan.get("status")),
            identifiers={"recovery_plan_id": plan.get("id"),
                         "recommended_action": plan.get("recommended_action"),
                         "state_observed": plan.get("state_observed")},
            detail=(f"Failure: {_text(plan.get('failure_reason'))}. "
                    f"{_text(plan.get('recommendation'))} Boundary: "
                    f"{_text(plan.get('authority_boundary'))}."),
        ))

    items.sort(key=lambda item: item.get("at") or "")

    return {
        "issue_id": issue_id,
        "owner": owner,
        "title": _text(issue.get("title")),
        "current_state": _text(issue.get("state")),
        "verification_status": _text(issue.get("verification_status")),
        "work_order": _text(
            (human_reach or {}).get("work_order")
            or issue.get("transport_request_id")
            or issue.get("facilities_work_order_id")
            or issue.get("evs_cleaning_id")
            or issue.get("interpreter_booking_id")
            or issue.get("dme_order_id")
            or issue.get("assigned_asset_id")
        ),
        "items": items,
    }
