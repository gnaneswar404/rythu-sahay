from datetime import date, datetime

from pydantic import Field, field_validator

from app.models import CaseStatus, Severity
from app.schemas.common import ORMModel


class CaseCreate(ORMModel):
    farmer_id: int
    crop: str = "cotton"
    village: str | None = Field(default=None, max_length=120)
    mandal: str | None = Field(default=None, max_length=120)
    district: str = "Nalgonda"
    problem_category: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=5, max_length=4000)
    symptoms: str | None = Field(default=None, max_length=4000)
    affected_area: str | None = Field(default=None, max_length=120)
    severity: Severity = Severity.MEDIUM
    ai_summary: str | None = Field(default=None, max_length=4000)

    @field_validator("crop")
    @classmethod
    def validate_crop(cls, value: str) -> str:
        if value.strip().lower() not in {"cotton", "పత్తి"}:
            raise ValueError("RYTHU SAHAYA currently supports cotton only.")
        return "cotton"

    @field_validator("district")
    @classmethod
    def validate_district(cls, value: str) -> str:
        if value.strip().lower() != "nalgonda":
            raise ValueError("RYTHU SAHAYA currently supports only Nalgonda district.")
        return "Nalgonda"


class FeedbackCreate(ORMModel):
    outcome: str = Field(pattern="^(IMPROVED|UNCHANGED|WORSENED)$")
    farmer_response: str | None = Field(default=None, max_length=1000)


class FollowupRead(ORMModel):
    id: int
    scheduled_date: date
    farmer_response: str | None
    outcome: str | None
    completed_at: datetime | None
    created_at: datetime


class CaseRead(ORMModel):
    id: str
    farmer_id: int
    crop: str
    village: str | None
    mandal: str | None
    district: str
    problem_category: str | None
    description: str
    symptoms: str | None
    affected_area: str | None
    severity: Severity
    status: CaseStatus
    ai_summary: str | None
    recommended_next_action: str | None
    resolution_outcome: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
