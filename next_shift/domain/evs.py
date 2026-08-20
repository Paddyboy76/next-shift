from __future__ import annotations

from typing import Any


DEFAULT_TURNAROUND_TARGET_MINUTES = 60


SYNTHETIC_EVS_TEAMS: tuple[dict[str, Any], ...] = (
    {
        "team_id": "EVS-A",
        "name": "Environmental Services Team A",
        "zone": "North Tower",
        "available": True,
    },
    {
        "team_id": "EVS-B",
        "name": "Environmental Services Team B",
        "zone": "South Tower",
        "available": True,
    },
)


def find_available_evs_team(
    zone: str,
) -> dict[str, Any]:
    for team in SYNTHETIC_EVS_TEAMS:
        if team["available"] and team["zone"] == zone:
            return dict(team)

    raise LookupError(
        f"No available EVS team for zone: {zone}"
    )
