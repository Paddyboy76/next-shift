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
class CapabilityPolicy:
    owner: str
    allowed_update_fields: frozenset[str]


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
        allowed_update_fields=frozenset(
            {
                "facility_type",
                "facilities_location",
                "facilities_work_order_id",
                "facilities_team_id",
                "facilities_team_name",
                "facilities_status",
            }
        ),
    ),

    # These capabilities are recognized but intentionally have no
    # writable fields until each specialist is migrated through the
    # State Authority and receives its own explicit field contract.
    "asset_logistics.coordinate": CapabilityPolicy(
        owner="AssetLogistics",
        allowed_update_fields=frozenset(),
    ),
    "language_access.coordinate": CapabilityPolicy(
        owner="LanguageAccess",
        allowed_update_fields=frozenset(),
    ),
    "discharge_dme.coordinate": CapabilityPolicy(
        owner="DischargeDME",
        allowed_update_fields=frozenset(),
    ),
    "evs_throughput.coordinate": CapabilityPolicy(
        owner="EVSThroughput",
        allowed_update_fields=frozenset(),
    ),
    "patient_transport.coordinate": CapabilityPolicy(
        owner="PatientTransport",
        allowed_update_fields=frozenset(),
    ),
    "verification.close": CapabilityPolicy(
        owner="IndependentVerifier",
        allowed_update_fields=frozenset(),
    ),
}


VALID_CAPABILITIES = frozenset(
    CAPABILITY_POLICIES
)
