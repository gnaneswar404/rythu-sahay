from datetime import date

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ORMModel


class LocationFields(ORMModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both latitude and longitude, or neither.")
        return self


class WorkerProfileUpdate(LocationFields):
    name: str = Field(min_length=2, max_length=120)
    village: str | None = Field(default=None, max_length=120)
    mandal: str | None = Field(default=None, max_length=120)
    skills: str = Field(default="", max_length=1000)
    daily_wage: int | None = Field(default=None, ge=1, le=100000)
    is_available: bool = True
    allow_phone_contact: bool | None = None


class FarmerProfileUpdate(LocationFields):
    name: str = Field(min_length=2, max_length=120)
    village: str | None = Field(default=None, max_length=120)
    mandal: str | None = Field(default=None, max_length=120)
    preferred_language: str = Field(default="te", pattern="^(te|en)$")
    allow_phone_contact: bool | None = None


class MarketJobCreate(LocationFields):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)
    village: str = Field(min_length=2, max_length=120)
    mandal: str = Field(min_length=2, max_length=120)
    work_date: date
    required_workers: int = Field(default=1, ge=1, le=100)
    daily_wage: int = Field(ge=1, le=100000)


class TeamCreate(ORMModel):
    name: str = Field(min_length=2, max_length=120)


class TeamMemberCreate(ORMModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class ApplicationCreate(ORMModel):
    proposed_wage: int = Field(ge=1, le=100000)
    team_id: int | None = None


class WageOffer(ORMModel):
    proposed_wage: int = Field(ge=1, le=100000)


class BookingMessageCreate(ORMModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Message cannot be empty.")
        return message
