from __future__ import annotations

from dataclasses import dataclass


PROJECT_ID = "next-shift-506004"
SERVICE_ACCOUNT_DOMAIN = (
    f"{PROJECT_ID}.iam.gserviceaccount.com"
)

INTAKE_OWNERS = frozenset(
    {
        "Facilities",
        "AssetLogistics",
        "LanguageAccess",
        "DischargeDME",
        "EVSThroughput",
        "PatientTransport",
    }
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


def _standard_capability(
    *,
    owner: str,
    assignment_fields: frozenset[str],
    pending_fields: frozenset[str],
) -> CapabilityPolicy:
    all_fields = (
        assignment_fields
        | pending_fields
    )

    return CapabilityPolicy(
        owner=owner,
        allowed_update_fields=all_fields,
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
                required_update_fields=assignment_fields,
                allowed_update_fields=assignment_fields,
            ),
            (
                "ASSIGNED",
                "ACTION_PENDING",
            ): TransitionPolicy(
                required_update_fields=pending_fields,
                allowed_update_fields=pending_fields,
            ),
        },
    )


FACILITIES_ASSIGNMENT_FIELDS = frozenset(
    {
        "facility_type",
        "facilities_location",
        "facilities_work_order_id",
        "facilities_team_id",
        "facilities_team_name",
        "facilities_status",
    }
)

ASSET_PENDING_FIELDS = frozenset(
    {
        "assigned_asset_id",
        "assigned_asset_type",
        "assigned_asset_origin",
        "dispatch_destination",
        "dispatch_status",
    }
)

LANGUAGE_ASSIGNMENT_FIELDS = frozenset(
    {
        "language",
        "interpreter_id",
        "interpreter_name",
        "interpreter_booking_id",
        "interpreter_slot",
        "interpreter_service_location",
        "interpreter_status",
    }
)

DME_ASSIGNMENT_FIELDS = frozenset(
    {
        "dme_equipment_type",
        "dme_provider_id",
        "dme_provider_name",
        "dme_order_id",
        "dme_delivery_destination",
        "dme_order_status",
    }
)

EVS_ASSIGNMENT_FIELDS = frozenset(
    {
        "evs_cleaning_id",
        "evs_team_id",
        "evs_team_name",
        "evs_room",
        "evs_zone",
        "evs_target_minutes",
        "evs_status",
    }
)

TRANSPORT_ASSIGNMENT_FIELDS = frozenset(
    {
        "transport_request_id",
        "transport_type",
        "transport_origin",
        "transport_destination",
        "transporter_id",
        "transporter_name",
        "transport_status",
    }
)


PRINCIPAL_POLICIES: dict[str, PrincipalPolicy] = {
    (
        "ns-operations-ui@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="Intake",
        capabilities=frozenset(
            {"intake.create"}
        ),
    ),
    (
        "ns-worker-facilities@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="Facilities",
        capabilities=frozenset(
            {"facilities.coordinate"}
        ),
    ),
    (
        "ns-worker-asset-logistics@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="AssetLogistics",
        capabilities=frozenset(
            {"asset_logistics.coordinate"}
        ),
    ),
    (
        "ns-worker-language-access@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="LanguageAccess",
        capabilities=frozenset(
            {"language_access.coordinate"}
        ),
    ),
    (
        "ns-worker-discharge-dme@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="DischargeDME",
        capabilities=frozenset(
            {"discharge_dme.coordinate"}
        ),
    ),
    (
        "ns-worker-evs-throughput@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="EVSThroughput",
        capabilities=frozenset(
            {"evs_throughput.coordinate"}
        ),
    ),
    (
        "ns-worker-patient-transport@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="PatientTransport",
        capabilities=frozenset(
            {"patient_transport.coordinate"}
        ),
    ),
    (
        "ns-trusted-evidence@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="TrustedEvidence",
        capabilities=frozenset(
            {"evidence.record"}
        ),
    ),
    (
        "ns-verifier@"
        + SERVICE_ACCOUNT_DOMAIN
    ): PrincipalPolicy(
        owner="IndependentVerifier",
        capabilities=frozenset(
            {
                "verification.read",
                "verification.close",
            }
        ),
    ),
}


CAPABILITY_POLICIES: dict[str, CapabilityPolicy] = {
    "facilities.coordinate": (
        _standard_capability(
            owner="Facilities",
            assignment_fields=(
                FACILITIES_ASSIGNMENT_FIELDS
            ),
            pending_fields=frozenset(
                {"facilities_status"}
            ),
        )
    ),
    "asset_logistics.coordinate": (
        _standard_capability(
            owner="AssetLogistics",
            assignment_fields=frozenset(),
            pending_fields=(
                ASSET_PENDING_FIELDS
            ),
        )
    ),
    "language_access.coordinate": (
        _standard_capability(
            owner="LanguageAccess",
            assignment_fields=(
                LANGUAGE_ASSIGNMENT_FIELDS
            ),
            pending_fields=frozenset(
                {"interpreter_status"}
            ),
        )
    ),
    "discharge_dme.coordinate": (
        _standard_capability(
            owner="DischargeDME",
            assignment_fields=(
                DME_ASSIGNMENT_FIELDS
            ),
            pending_fields=frozenset(
                {"dme_order_status"}
            ),
        )
    ),
    "evs_throughput.coordinate": (
        _standard_capability(
            owner="EVSThroughput",
            assignment_fields=(
                EVS_ASSIGNMENT_FIELDS
            ),
            pending_fields=frozenset(
                {
                    "evs_status",
                    "evs_started_at",
                }
            ),
        )
    ),
    "patient_transport.coordinate": (
        _standard_capability(
            owner="PatientTransport",
            assignment_fields=(
                TRANSPORT_ASSIGNMENT_FIELDS
            ),
            pending_fields=frozenset(
                {"transport_status"}
            ),
        )
    ),
    "evidence.record": CapabilityPolicy(
        owner="TrustedEvidence",
        allowed_update_fields=frozenset(),
        transitions={},
    ),
    "verification.read": CapabilityPolicy(
        owner="IndependentVerifier",
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
