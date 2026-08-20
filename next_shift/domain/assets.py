from __future__ import annotations

from typing import Any


SUPPORTED_ASSET_TYPES: set[str] = {
    "standard_wheelchair",
    "bariatric_wheelchair",
}


SYNTHETIC_ASSETS: tuple[dict[str, Any], ...] = (
    {
        "asset_id": "WC-041",
        "asset_type": "standard_wheelchair",
        "location": "Floor 3 - Lift Lobby",
        "available": True,
    },
    {
        "asset_id": "WC-042",
        "asset_type": "standard_wheelchair",
        "location": "Floor 5 - Discharge Lounge",
        "available": False,
    },
    {
        "asset_id": "BWC-011",
        "asset_type": "bariatric_wheelchair",
        "location": "Floor 2 - Equipment Store",
        "available": True,
    },
)


def find_available_asset(
    asset_type: str,
) -> dict[str, Any]:
    if asset_type not in SUPPORTED_ASSET_TYPES:
        raise ValueError(f"Unsupported asset type: {asset_type}")

    for asset in SYNTHETIC_ASSETS:
        if (
            asset["asset_type"] == asset_type
            and asset["available"] is True
        ):
            return dict(asset)

    raise LookupError(
        f"No available asset found for type: {asset_type}"
    )
