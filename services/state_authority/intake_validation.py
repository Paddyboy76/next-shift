from __future__ import annotations

import json
from typing import Any

from policy import INTAKE_OWNERS
from security import AuthorizationError


ALLOWED_PROPOSAL_FIELDS = frozenset(
    {
        "title",
        "description",
        "owner",
        "workflow_input",
        "human_approval_required",
    }
)


def validated_text(
    value: Any,
    *,
    field: str,
    maximum: int,
) -> str:
    if not isinstance(value, str):
        raise AuthorizationError(
            reason="invalid_intake_value",
            details={"field": field},
        )

    cleaned = value.strip()

    if (
        not cleaned
        or len(cleaned) > maximum
        or any(
            ord(char) < 32
            and char not in "\n\r\t"
            for char in cleaned
        )
    ):
        raise AuthorizationError(
            reason="invalid_intake_value",
            details={"field": field},
        )

    return cleaned


def validate_proposal(
    proposal: dict[str, Any],
) -> dict[str, Any]:
    extra_fields = (
        set(proposal)
        - ALLOWED_PROPOSAL_FIELDS
    )

    if extra_fields:
        raise AuthorizationError(
            reason="intake_field_not_authorized",
            details={
                "fields": sorted(extra_fields),
            },
        )

    title = validated_text(
        proposal.get("title"),
        field="title",
        maximum=200,
    )
    description = validated_text(
        proposal.get("description"),
        field="description",
        maximum=4000,
    )
    owner = validated_text(
        proposal.get("owner"),
        field="owner",
        maximum=64,
    )

    if owner not in INTAKE_OWNERS:
        raise AuthorizationError(
            reason="invalid_intake_owner",
            target_owner=owner,
        )

    workflow_input = proposal.get(
        "workflow_input",
        {},
    )

    if not isinstance(workflow_input, dict):
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        )

    try:
        serialized_workflow_input = json.dumps(
            workflow_input,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        ) from exc

    if len(serialized_workflow_input) > 8000:
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        )

    human_approval_required = proposal.get(
        "human_approval_required",
        False,
    )

    if not isinstance(
        human_approval_required,
        bool,
    ):
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "human_approval_required",
            },
        )

    return {
        "title": title,
        "description": description,
        "owner": owner,
        "workflow_input": dict(workflow_input),
        "human_approval_required": (
            human_approval_required
        ),
    }


def validate_source(
    *,
    source_type: str,
    source_reference: str,
) -> tuple[str, str]:
    return (
        validated_text(
            source_type,
            field="source_type",
            maximum=64,
        ),
        validated_text(
            source_reference,
            field="source_reference",
            maximum=200,
        ),
    )
