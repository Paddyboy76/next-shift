from __future__ import annotations

from typing import Literal


OperationalOwner = Literal[
    "Facilities",
    "AssetLogistics",
    "LanguageAccess",
    "DischargeDME",
    "EVSThroughput",
    "PatientTransport",
]


VALID_OPERATIONAL_OWNERS: set[str] = {
    "Facilities",
    "AssetLogistics",
    "LanguageAccess",
    "DischargeDME",
    "EVSThroughput",
    "PatientTransport",
}


OWNER_TO_WORKER: dict[str, str] = {
    "Facilities": "facilities_worker",
    "AssetLogistics": "asset_logistics_worker",
    "LanguageAccess": "language_access_worker",
    "DischargeDME": "discharge_dme_worker",
    "EVSThroughput": "evs_throughput_worker",
    "PatientTransport": "patient_transport_worker",
}


def validate_operational_owner(owner: str) -> None:
    if owner not in VALID_OPERATIONAL_OWNERS:
        raise ValueError(
            f"Unsupported operational owner: {owner}"
        )


def worker_for_owner(owner: str) -> str:
    validate_operational_owner(owner)
    return OWNER_TO_WORKER[owner]
