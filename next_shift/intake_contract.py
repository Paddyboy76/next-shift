from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


OperationalOwner = Literal[
    "Facilities",
    "AssetLogistics",
    "LanguageAccess",
    "DischargeDME",
    "EVSThroughput",
    "PatientTransport",
]


class IntakeIssueProposal(BaseModel):
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
    owner: OperationalOwner = Field(
        description="The single canonical specialist owner for this issue."
    )
    workflow_input: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Small owner-specific string fields needed for specialist "
            "execution, such as room, language, destination, equipment_type, "
            "origin, transport_type, facility_type, or location."
        ),
    )
    human_approval_required: bool = Field(
        default=False,
        description=(
            "True only when the operational issue explicitly requires an "
            "authorized human decision before execution."
        ),
    )


class IntakeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[IntakeIssueProposal] = Field(
        default_factory=list,
        description=(
            "Every distinct unresolved permitted non-clinical operational "
            "issue found in the handover."
        ),
    )
    rejected_clinical_requests: list[str] = Field(
        default_factory=list,
        description=(
            "Clinical or otherwise prohibited requests that were deliberately "
            "not converted into operational work."
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
