from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Callable

from state_authority import transition_issue


CAPABILITIES = {
    "AssetLogistics": (
        "asset_logistics.coordinate"
    ),
    "LanguageAccess": (
        "language_access.coordinate"
    ),
    "DischargeDME": (
        "discharge_dme.coordinate"
    ),
    "EVSThroughput": (
        "evs_throughput.coordinate"
    ),
    "PatientTransport": (
        "patient_transport.coordinate"
    ),
}


def _text(
    value: Any,
    *,
    default: str,
    maximum: int = 200,
) -> str:
    if value is None:
        value = default

    if not isinstance(value, str):
        raise ValueError(
            "Expected text input"
        )

    value = value.strip()

    if (
        not value
        or len(value) > maximum
    ):
        raise ValueError(
            "Invalid text input"
        )

    return value


def _transition(
    *,
    owner: str,
    issue_id: str,
    expected_state: str,
    new_state: str,
    reason: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    return transition_issue(
        issue_id=issue_id,
        capability=CAPABILITIES[owner],
        expected_state=expected_state,
        new_state=new_state,
        reason=reason,
        updates=updates,
    )


def _asset(
    issue_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    destination = _text(
        data.get("destination"),
        default="Room 402",
    )

    asset = {
        "asset_id": "WC-041",
        "asset_type": (
            "standard_wheelchair"
        ),
        "location": (
            "Floor 3 - Lift Lobby"
        ),
    }

    _transition(
        owner="AssetLogistics",
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "AssetLogistics accepted the "
            "routed asset request."
        ),
        updates={},
    )

    _transition(
        owner="AssetLogistics",
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"Synthetic RTLS located "
            f"{asset['asset_id']} at "
            f"{asset['location']}."
        ),
        updates={},
    )

    return _transition(
        owner="AssetLogistics",
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"Dispatch requested for "
            f"{asset['asset_id']} to "
            f"{destination}."
        ),
        updates={
            "assigned_asset_id": (
                asset["asset_id"]
            ),
            "assigned_asset_type": (
                asset["asset_type"]
            ),
            "assigned_asset_origin": (
                asset["location"]
            ),
            "dispatch_destination": (
                destination
            ),
            "dispatch_status": "IN_TRANSIT",
        },
    )


def _language(
    issue_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    language = _text(
        data.get("language"),
        default="Spanish",
        maximum=40,
    )

    location = _text(
        data.get("service_location"),
        default="Room 402",
    )

    interpreters = {
        "Spanish": (
            "INT-ESP-014",
            "Elena Ruiz",
            "19:15",
        ),
        "Thai": (
            "INT-THA-008",
            "Narin S.",
            "19:05",
        ),
        "Mandarin": (
            "INT-MAN-021",
            "Lin Wei",
            "19:30",
        ),
    }

    if language not in interpreters:
        raise ValueError(
            "No qualified interpreter available"
        )

    interpreter_id, name, slot = (
        interpreters[language]
    )

    booking_id = (
        f"LANG-{uuid.uuid4().hex[:8].upper()}"
    )

    _transition(
        owner="LanguageAccess",
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "LanguageAccess accepted the "
            "routed interpreter request."
        ),
        updates={},
    )

    _transition(
        owner="LanguageAccess",
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"Qualified {language} interpreter "
            f"{name} booked for {slot}."
        ),
        updates={
            "language": language,
            "interpreter_id": interpreter_id,
            "interpreter_name": name,
            "interpreter_booking_id": (
                booking_id
            ),
            "interpreter_slot": slot,
            "interpreter_service_location": (
                location
            ),
            "interpreter_status": "BOOKED",
        },
    )

    return _transition(
        owner="LanguageAccess",
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"Interpreter booking "
            f"{booking_id} is awaiting "
            f"attendance at {location}."
        ),
        updates={
            "interpreter_status": (
                "AWAITING_ATTENDANCE"
            )
        },
    )


def _dme(
    issue_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    equipment = _text(
        data.get("equipment_type"),
        default="home_oxygen",
        maximum=40,
    )

    destination = _text(
        data.get("delivery_destination"),
        default="Patient Home",
    )

    if equipment not in {
        "home_oxygen",
        "hospital_bed",
        "walker",
        "wheelchair",
    }:
        raise ValueError(
            "Unsupported DME type"
        )

    order_id = (
        f"DME-{uuid.uuid4().hex[:8].upper()}"
    )

    _transition(
        owner="DischargeDME",
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "DischargeDME accepted the "
            "routed equipment request."
        ),
        updates={},
    )

    _transition(
        owner="DischargeDME",
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"DME order {order_id} assigned "
            f"to Metro Home Medical."
        ),
        updates={
            "dme_equipment_type": equipment,
            "dme_provider_id": "DME-ALPHA",
            "dme_provider_name": (
                "Metro Home Medical"
            ),
            "dme_order_id": order_id,
            "dme_delivery_destination": (
                destination
            ),
            "dme_order_status": (
                "ORDER_CREATED"
            ),
        },
    )

    return _transition(
        owner="DischargeDME",
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"DME order {order_id} is "
            f"awaiting delivery to "
            f"{destination}."
        ),
        updates={
            "dme_order_status": (
                "AWAITING_DELIVERY"
            )
        },
    )


def _evs(
    issue_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    room = _text(
        data.get("room"),
        default="Room 402",
    )

    zone = _text(
        data.get("zone"),
        default="North Tower",
    )

    target = data.get(
        "target_minutes",
        60,
    )

    if (
        not isinstance(target, int)
        or target <= 0
        or target > 240
    ):
        raise ValueError(
            "Invalid turnaround target"
        )

    teams = {
        "North Tower": (
            "EVS-A",
            "Environmental Services Team A",
        ),
        "South Tower": (
            "EVS-B",
            "Environmental Services Team B",
        ),
    }

    if zone not in teams:
        raise ValueError(
            "No available EVS team"
        )

    team_id, team_name = teams[zone]

    cleaning_id = (
        f"EVS-{uuid.uuid4().hex[:8].upper()}"
    )

    _transition(
        owner="EVSThroughput",
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "EVSThroughput accepted the "
            "routed turnaround request."
        ),
        updates={},
    )

    _transition(
        owner="EVSThroughput",
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"Cleaning request {cleaning_id} "
            f"assigned to {team_name}."
        ),
        updates={
            "evs_cleaning_id": cleaning_id,
            "evs_team_id": team_id,
            "evs_team_name": team_name,
            "evs_room": room,
            "evs_zone": zone,
            "evs_target_minutes": target,
            "evs_status": "ASSIGNED",
        },
    )

    return _transition(
        owner="EVSThroughput",
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"EVS turnaround clock started "
            f"for {room}."
        ),
        updates={
            "evs_status": "CLEANING_PENDING",
            "evs_started_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        },
    )


def _transport(
    issue_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    transport_type = _text(
        data.get("transport_type"),
        default="wheelchair",
        maximum=40,
    )

    origin = _text(
        data.get("origin"),
        default="Room 402",
    )

    destination = _text(
        data.get("destination"),
        default="Discharge Lounge",
    )

    transporters = {
        "wheelchair": (
            "TRN-017",
            "Transport Team 17",
        ),
        "walking_assist": (
            "TRN-017",
            "Transport Team 17",
        ),
        "stretcher": (
            "TRN-024",
            "Transport Team 24",
        ),
    }

    if transport_type not in transporters:
        raise ValueError(
            "Unsupported transport type"
        )

    transporter_id, name = (
        transporters[transport_type]
    )

    request_id = (
        f"TRN-{uuid.uuid4().hex[:8].upper()}"
    )

    _transition(
        owner="PatientTransport",
        issue_id=issue_id,
        expected_state="RECEIVED",
        new_state="TRIAGED",
        reason=(
            "PatientTransport accepted the "
            "routed transport request."
        ),
        updates={},
    )

    _transition(
        owner="PatientTransport",
        issue_id=issue_id,
        expected_state="TRIAGED",
        new_state="ASSIGNED",
        reason=(
            f"Transport request {request_id} "
            f"assigned to {name}."
        ),
        updates={
            "transport_request_id": request_id,
            "transport_type": transport_type,
            "transport_origin": origin,
            "transport_destination": (
                destination
            ),
            "transporter_id": transporter_id,
            "transporter_name": name,
            "transport_status": "ASSIGNED",
        },
    )

    return _transition(
        owner="PatientTransport",
        issue_id=issue_id,
        expected_state="ASSIGNED",
        new_state="ACTION_PENDING",
        reason=(
            f"Transport request {request_id} "
            f"is awaiting pickup at {origin}."
        ),
        updates={
            "transport_status": (
                "AWAITING_PICKUP"
            )
        },
    )


HANDLERS: dict[
    str,
    Callable[
        [str, dict[str, Any]],
        dict[str, Any],
    ],
] = {
    "AssetLogistics": _asset,
    "LanguageAccess": _language,
    "DischargeDME": _dme,
    "EVSThroughput": _evs,
    "PatientTransport": _transport,
}


def process_issue(
    *,
    owner: str,
    issue_id: str,
    workflow_input: dict[str, Any],
) -> dict[str, Any]:
    handler = HANDLERS.get(owner)

    if handler is None:
        raise ValueError(
            f"Unsupported specialist owner: {owner}"
        )

    return handler(
        issue_id,
        workflow_input,
    )
