from __future__ import annotations

from typing import Any

from security import AuthorizationError


DELIVERY_SCHEMA_VERSION = "human-reach.delivery.v1"
DELIVERY_EVENT_TYPE = "human_reach.delivery.requested"
DELIVERY_COLLECTION = "human_reach_deliveries"

SUPPORTED_OWNERS = frozenset(
    {
        "Facilities",
        "AssetLogistics",
        "LanguageAccess",
        "DischargeDME",
        "EVSThroughput",
        "PatientTransport",
    }
)


def _required_text(
    issue: dict[str, Any],
    field: str,
    *,
    owner: str,
) -> str:
    value = issue.get(field)

    if not isinstance(value, str):
        raise AuthorizationError(
            reason="human_reach_context_invalid",
            target_owner=owner,
            details={"field": field},
        )

    cleaned = value.strip()

    if not cleaned or len(cleaned) > 500:
        raise AuthorizationError(
            reason="human_reach_context_invalid",
            target_owner=owner,
            details={"field": field},
        )

    return cleaned


def _issue_title(issue: dict[str, Any], owner: str) -> str:
    return _required_text(
        issue,
        "title",
        owner=owner,
    )


def _issue_description(issue: dict[str, Any], owner: str) -> str:
    return _required_text(
        issue,
        "description",
        owner=owner,
    )


def build_delivery_request(
    *,
    issue_id: str,
    issue: dict[str, Any],
    requested_at: str,
) -> dict[str, Any]:
    owner = str(issue.get("owner", "UNKNOWN"))

    if owner not in SUPPORTED_OWNERS:
        raise AuthorizationError(
            reason="human_reach_owner_unsupported",
            target_owner=owner,
        )

    who: str
    where: str
    work_order: str

    if owner == "Facilities":
        who = _required_text(
            issue,
            "facilities_team_name",
            owner=owner,
        )
        where = _required_text(
            issue,
            "facilities_location",
            owner=owner,
        )
        work_order = _required_text(
            issue,
            "facilities_work_order_id",
            owner=owner,
        )
    elif owner == "AssetLogistics":
        who = "Asset Logistics Dispatch"
        where = _required_text(
            issue,
            "dispatch_destination",
            owner=owner,
        )
        work_order = _required_text(
            issue,
            "assigned_asset_id",
            owner=owner,
        )
    elif owner == "LanguageAccess":
        who = _required_text(
            issue,
            "interpreter_name",
            owner=owner,
        )
        where = _required_text(
            issue,
            "interpreter_service_location",
            owner=owner,
        )
        work_order = _required_text(
            issue,
            "interpreter_booking_id",
            owner=owner,
        )
    elif owner == "DischargeDME":
        who = _required_text(
            issue,
            "dme_provider_name",
            owner=owner,
        )
        where = _required_text(
            issue,
            "dme_delivery_destination",
            owner=owner,
        )
        work_order = _required_text(
            issue,
            "dme_order_id",
            owner=owner,
        )
    elif owner == "EVSThroughput":
        who = _required_text(
            issue,
            "evs_team_name",
            owner=owner,
        )
        where = _required_text(
            issue,
            "evs_room",
            owner=owner,
        )
        work_order = _required_text(
            issue,
            "evs_cleaning_id",
            owner=owner,
        )
    else:
        who = _required_text(
            issue,
            "transporter_name",
            owner=owner,
        )
        origin = _required_text(
            issue,
            "transport_origin",
            owner=owner,
        )
        destination = _required_text(
            issue,
            "transport_destination",
            owner=owner,
        )
        where = f"{origin} -> {destination}"
        work_order = _required_text(
            issue,
            "transport_request_id",
            owner=owner,
        )

    return {
        "delivery_id": issue_id,
        "issue_id": issue_id,
        "schema_version": DELIVERY_SCHEMA_VERSION,
        "owner": owner,
        "routing_key": owner,
        "who": who,
        "what": _issue_title(issue, owner),
        "where": where,
        "work_order": work_order,
        "issue_title": _issue_title(issue, owner),
        "issue_description": _issue_description(issue, owner),
        "workflow_state": "ACTION_PENDING",
        "delivery_status": "PENDING",
        "event_dispatch_status": "PENDING",
        "requested_at": requested_at,
        "response_history": [],
    }
