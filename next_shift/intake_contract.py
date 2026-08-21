from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class _IssueBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=200,
        description="Concise operational issue title.",
    )
    description: str = Field(
        min_length=1,
        max_length=4000,
        description=(
            "What remains unresolved, using only facts from the handover."
        ),
    )
    human_approval_required: bool = Field(
        default=False,
        description=(
            "True only when the operational issue explicitly requires an "
            "authorized human decision before execution."
        ),
    )


class FacilitiesWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_type: Literal[
        "plumbing",
        "air_conditioning",
        "electrical",
        "room_maintenance",
    ]
    location: str = Field(min_length=1, max_length=200)


class FacilitiesIssue(_IssueBase):
    workflow_input: FacilitiesWorkflowInput


class AssetLogisticsWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1, max_length=200)


class AssetLogisticsIssue(_IssueBase):
    workflow_input: AssetLogisticsWorkflowInput


class LanguageAccessWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(min_length=1, max_length=80)
    service_location: str = Field(min_length=1, max_length=200)


class LanguageAccessIssue(_IssueBase):
    workflow_input: LanguageAccessWorkflowInput


class DischargeDMEWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_type: Literal[
        "home_oxygen",
        "hospital_bed",
        "walker",
        "wheelchair",
    ]
    delivery_destination: str = Field(min_length=1, max_length=200)


class DischargeDMEIssue(_IssueBase):
    workflow_input: DischargeDMEWorkflowInput


class EVSWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room: str = Field(min_length=1, max_length=200)
    zone: Literal[
        "North Tower",
        "South Tower",
    ] | None = None


class EVSThroughputIssue(_IssueBase):
    workflow_input: EVSWorkflowInput


class PatientTransportWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    transport_type: Literal[
        "wheelchair",
        "walking_assist",
        "stretcher",
    ]


class PatientTransportIssue(_IssueBase):
    workflow_input: PatientTransportWorkflowInput


class IntakeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facilities: list[FacilitiesIssue] = Field(
        description="Every unresolved Facilities issue; use [] when none."
    )
    asset_logistics: list[AssetLogisticsIssue] = Field(
        description="Every unresolved AssetLogistics issue; use [] when none."
    )
    language_access: list[LanguageAccessIssue] = Field(
        description="Every unresolved LanguageAccess issue; use [] when none."
    )
    discharge_dme: list[DischargeDMEIssue] = Field(
        description="Every unresolved DischargeDME issue; use [] when none."
    )
    evs_throughput: list[EVSThroughputIssue] = Field(
        description="Every unresolved EVSThroughput issue; use [] when none."
    )
    patient_transport: list[PatientTransportIssue] = Field(
        description="Every unresolved PatientTransport issue; use [] when none."
    )
    rejected_clinical_requests: list[str] = Field(
        description=(
            "Clinical or otherwise prohibited requests deliberately not "
            "converted into operational work; use [] when none."
        ),
    )
    summary: str = Field(
        min_length=1,
        max_length=1200,
        description=(
            "Short operator-facing summary of the intake analysis. Do not "
            "claim persistence, dispatch, execution, evidence, or closure."
        ),
    )
