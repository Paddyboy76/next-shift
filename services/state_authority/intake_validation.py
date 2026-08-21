from __future__ import annotations

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

WORKFLOW_FIELDS_BY_OWNER: dict[
    str,
    frozenset[str],
] = {
    "Facilities": frozenset(
        {
            "facility_type",
            "location",
        }
    ),
    "AssetLogistics": frozenset(
        {
            "destination",
        }
    ),
    "LanguageAccess": frozenset(
        {
            "language",
            "service_location",
        }
    ),
    "DischargeDME": frozenset(
        {
            "equipment_type",
            "delivery_destination",
        }
    ),
    "EVSThroughput": frozenset(
        {
            "room",
            "zone",
        }
    ),
    "PatientTransport": frozenset(
        {
            "origin",
            "destination",
            "transport_type",
        }
    ),
}


CANONICAL_VALUES: dict[
    tuple[str, str],
    frozenset[str],
] = {
    (
        "Facilities",
        "facility_type",
    ): frozenset(
        {
            "plumbing",
            "air_conditioning",
            "electrical",
            "room_maintenance",
        }
    ),
    (
        "DischargeDME",
        "equipment_type",
    ): frozenset(
        {
            "home_oxygen",
            "hospital_bed",
            "walker",
            "wheelchair",
        }
    ),
    (
        "EVSThroughput",
        "zone",
    ): frozenset(
        {
            "North Tower",
            "South Tower",
        }
    ),
    (
        "PatientTransport",
        "transport_type",
    ): frozenset(
        {
            "wheelchair",
            "walking_assist",
            "stretcher",
        }
    ),
}


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


def _validated_workflow_input(
    *,
    owner: str,
    workflow_input: Any,
) -> dict[str, str]:
    if not isinstance(workflow_input, dict):
        raise AuthorizationError(
            reason="invalid_intake_value",
            target_owner=owner,
            details={
                "field": "workflow_input",
            },
        )

    allowed_fields = (
        WORKFLOW_FIELDS_BY_OWNER[owner]
    )
    extra_fields = (
        set(workflow_input)
        - allowed_fields
    )

    if extra_fields:
        raise AuthorizationError(
            reason=(
                "workflow_input_field_not_authorized"
            ),
            target_owner=owner,
            details={
                "fields": sorted(extra_fields),
            },
        )

    validated: dict[str, str] = {}

    for field, value in workflow_input.items():
        cleaned = validated_text(
            value,
            field=f"workflow_input.{field}",
            maximum=200,
        )

        canonical = CANONICAL_VALUES.get(
            (owner, field)
        )

        if (
            canonical is not None
            and cleaned not in canonical
        ):
            raise AuthorizationError(
                reason="invalid_intake_value",
                target_owner=owner,
                details={
                    "field": (
                        f"workflow_input.{field}"
                    ),
                },
            )

        validated[field] = cleaned

    return validated


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

    workflow_input = (
        _validated_workflow_input(
            owner=owner,
            workflow_input=proposal.get(
                "workflow_input",
                {},
            ),
        )
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
        "workflow_input": workflow_input,
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
