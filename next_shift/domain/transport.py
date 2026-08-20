from __future__ import annotations

from typing import Any


SUPPORTED_TRANSPORT_TYPES: set[str] = {
    "wheelchair",
    "stretcher",
    "walking_assist",
}


SYNTHETIC_TRANSPORTERS: tuple[dict[str, Any], ...] = (
    {
        "transporter_id": "TRN-017",
        "name": "Transport Team 17",
        "transport_types": {
            "wheelchair",
            "walking_assist",
        },
        "available": True,
    },
    {
        "transporter_id": "TRN-024",
        "name": "Transport Team 24",
        "transport_types": {
            "stretcher",
            "wheelchair",
        },
        "available": True,
    },
)


def find_available_transporter(
    transport_type: str,
) -> dict[str, Any]:
    if transport_type not in SUPPORTED_TRANSPORT_TYPES:
        raise ValueError(
            f"Unsupported transport type: {transport_type}"
        )

    for transporter in SYNTHETIC_TRANSPORTERS:
        if (
            transporter["available"]
            and transport_type
            in transporter["transport_types"]
        ):
            result = dict(transporter)
            result["transport_types"] = sorted(
                transporter["transport_types"]
            )
            return result

    raise LookupError(
        f"No transporter available for: {transport_type}"
    )
