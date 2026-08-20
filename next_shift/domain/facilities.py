from __future__ import annotations

from typing import Any


SUPPORTED_FACILITY_TYPES: set[str] = {
    "plumbing",
    "air_conditioning",
    "electrical",
    "room_maintenance",
}


SYNTHETIC_FACILITIES_TEAMS: tuple[dict[str, Any], ...] = (
    {
        "team_id": "FAC-PLUMB-01",
        "name": "Facilities Plumbing Team",
        "specialties": {"plumbing"},
        "available": True,
    },
    {
        "team_id": "FAC-HVAC-01",
        "name": "Facilities HVAC Team",
        "specialties": {"air_conditioning"},
        "available": True,
    },
    {
        "team_id": "FAC-GEN-01",
        "name": "Facilities General Maintenance",
        "specialties": {
            "electrical",
            "room_maintenance",
        },
        "available": True,
    },
)


def find_facilities_team(
    facility_type: str,
) -> dict[str, Any]:
    if facility_type not in SUPPORTED_FACILITY_TYPES:
        raise ValueError(
            f"Unsupported facility type: {facility_type}"
        )

    for team in SYNTHETIC_FACILITIES_TEAMS:
        if (
            team["available"]
            and facility_type in team["specialties"]
        ):
            result = dict(team)
            result["specialties"] = sorted(
                team["specialties"]
            )
            return result

    raise LookupError(
        f"No Facilities team available for: {facility_type}"
    )
