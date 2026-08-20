from __future__ import annotations

from dataclasses import dataclass


PROJECT_ID = "next-shift-506004"
SERVICE_ACCOUNT_DOMAIN = (
    f"{PROJECT_ID}.iam.gserviceaccount.com"
)


@dataclass(frozen=True)
class PrincipalPolicy:
    owner: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class TransitionPolicy:
    required_update_fields: frozenset[str]
    allowed_update_fields: frozenset[str]


@dataclass(frozen=True)
class CapabilityPolicy:
    owner: str
    allowed_update_fields: frozenset[str]
    transitions: dict[
        tuple[str, str],
        TransitionPolicy,
    ]


FACILITIES_FIELDS = frozenset(
    {
        "facility_type",
        "facilities_location",
        "facilities_work_order_id",
        "facilities_team_id",
        "facilities_team_name",
        "facilities_status",
    }
)


PRINCIPAL_POLICIES: dict[str, PrincipalPolicy] = {
    (
        "ns-worker-facilities@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="Facilities",
        capabilities=frozenset(
            {
                "facilities.coordinate",
            }
        ),
    ),
    (
        "ns-worker-asset-logistics@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="AssetLogistics",
        capabilities=frozenset(
            {
                "asset_logistics.coordinate",
            }
        ),
    ),
    (
        "ns-worker-language-access@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="LanguageAccess",
        capabilities=frozenset(
            {
                "language_access.coordinate",
            }
        ),
    ),
    (
        "ns-worker-discharge-dme@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="DischargeDME",
        capabilities=frozenset(
            {
                "discharge_dme.coordinate",
            }
        ),
    ),
    (
        "ns-worker-evs-throughput@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="EVSThroughput",
        capabilities=frozenset(
            {
                "evs_throughput.coordinate",
            }
        ),
    ),
    (
        "ns-worker-patient-transport@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="PatientTransport",
        capabilities=frozenset(
            {
                "patient_transport.coordinate",
            }
        ),
    ),
    (
        "ns-verifier@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="IndependentVerifier",
        capabilities=frozenset(
            {
                "verification.close",
            }
        ),
    ),
}


CAPABILITY_POLICIES: dict[str, CapabilityPolicy] = {
    "facilities.coordinate": CapabilityPolicy(
        owner="Facilities",
        allowed_update_fields=FACILITIES_FIELDS,
        transitions={
            (
                "RECEIVED",
                "TRIAGED",
            ): TransitionPolicy(
                required_update_fields=frozenset(),
                allowed_update_fields=frozenset(),
            ),
            (
                "TRIAGED",
                "ASSIGNED",
            ): TransitionPolicy(
                required_update_fields=FACILITIES_FIELDS,
                allowed_update_fields=FACILITIES_FIELDS,
            ),
            (
                "ASSIGNED",
                "ACTION_PENDING",
            ): TransitionPolicy(
                required_update_fields=frozenset(
                    {
                        "facilities_status",
                    }
                ),
                allowed_update_fields=frozenset(
                    {
                        "facilities_status",
                    }
                ),
            ),
        },
    ),
    "asset_logistics.coordinate": CapabilityPolicy(
        owner="AssetLogistics",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "language_access.coordinate": CapabilityPolicy(
        owner="LanguageAccess",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "discharge_dme.coordinate": CapabilityPolicy(
        owner="DischargeDME",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "evs_throughput.coordinate": CapabilityPolicy(
        owner="EVSThroughput",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "patient_transport.coordinate": CapabilityPolicy(
        owner="PatientTransport",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "verification.close": CapabilityPolicy(
        owner="IndependentVerifier",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
}


FACILITY_TEAM_BY_TYPE = {
    "plumbing": (
        "FAC-PLUMB-01",
        "Facilities Plumbing Team",
    ),
    "air_conditioning": (
        "FAC-HVAC-01",
        "Facilities HVAC Team",
    ),
    "electrical": (
        "FAC-GEN-01",
        "Facilities General Maintenance",
    ),
    "room_maintenance": (
        "FAC-GEN-01",
        "Facilities General Maintenance",
    ),
}
