from __future__ import annotations

from typing import Any


SUPPORTED_DME_TYPES: set[str] = {
    "home_oxygen",
    "hospital_bed",
    "walker",
    "wheelchair",
}


SYNTHETIC_DME_PROVIDERS: tuple[dict[str, Any], ...] = (
    {
        "provider_id": "DME-ALPHA",
        "name": "Metro Home Medical",
        "supported_types": {
            "home_oxygen",
            "hospital_bed",
            "walker",
            "wheelchair",
        },
        "available": True,
    },
    {
        "provider_id": "DME-BETA",
        "name": "Community Equipment Services",
        "supported_types": {
            "walker",
            "wheelchair",
        },
        "available": True,
    },
)


def find_dme_provider(
    equipment_type: str,
) -> dict[str, Any]:
    if equipment_type not in SUPPORTED_DME_TYPES:
        raise ValueError(
            f"Unsupported DME type: {equipment_type}"
        )

    for provider in SYNTHETIC_DME_PROVIDERS:
        if (
            provider["available"]
            and equipment_type in provider["supported_types"]
        ):
            result = dict(provider)
            result["supported_types"] = sorted(
                provider["supported_types"]
            )
            return result

    raise LookupError(
        f"No available DME provider for: {equipment_type}"
    )
