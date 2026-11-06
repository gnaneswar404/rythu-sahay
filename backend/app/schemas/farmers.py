from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class FarmerCreate(ORMModel):
    name: str | None = Field(default=None, max_length=120)
    mobile: str | None = Field(default=None, max_length=20)
    village: str | None = Field(default=None, max_length=120)
    mandal: str | None = Field(default=None, max_length=120)
    district: str = Field(default="Nalgonda", max_length=120)
    preferred_language: str = Field(default="te", max_length=20)
    consent_recording: bool = False

    @field_validator("district")
    @classmethod
    def validate_district(cls, value: str) -> str:
        if value.strip().lower() != "nalgonda":
            raise ValueError("RYTHU SAHAYA currently supports only Nalgonda district.")
        return "Nalgonda"


class FarmerRead(FarmerCreate):
    id: int
    is_demo: bool
    created_at: datetime
