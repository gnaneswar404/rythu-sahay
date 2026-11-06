import secrets
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field, TypeAdapter, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Expert, Farmer, Worker
from app.services.auth import create_access_token, require_expert, verify_password
from app.services.seed import DEMO_EMAIL, LEGACY_DEMO_EMAIL, pwd_context

router = APIRouter(prefix="/auth", tags=["authentication"])
email_adapter = TypeAdapter(EmailStr)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email", mode="before")
    @classmethod
    def accept_legacy_demo_email(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().casefold() == LEGACY_DEMO_EMAIL:
            return DEMO_EMAIL
        return value


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)


class GoogleConfigResponse(BaseModel):
    client_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expert_id: int
    expert_name: str


class ExpertProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: str | None
    role: str
    is_demo: bool
    created_at: datetime


class ExpertProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=7, max_length=30)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Name must contain at least two characters.")
        return normalized

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.strip()
        digit_count = sum(character.isdigit() for character in normalized)
        if not 7 <= digit_count <= 15:
            raise ValueError("Enter a valid phone number.")
        return normalized


class MarketAccountRequest(BaseModel):
    account_type: Literal["farmer", "worker"]
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = Field(default=None, min_length=10, max_length=16)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 bytes.")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) == 10 and digits[0] in "6789":
            digits = f"91{digits}"
        if len(digits) != 12 or not digits.startswith("91") or digits[2] not in "6789":
            raise ValueError("Enter a valid Indian mobile number.")
        return f"+{digits}"


def profile_response(expert: Expert) -> ExpertProfileResponse:
    return ExpertProfileResponse(
        id=expert.id,
        name=expert.name,
        email=expert.email,
        phone_number=expert.contact,
        role=expert.role,
        is_demo=expert.is_demo,
        created_at=expert.created_at,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    expert = db.scalar(select(Expert).where(func.lower(Expert.email) == str(payload.email).lower()))
    if expert is None or not expert.is_active or not verify_password(payload.password, expert.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return LoginResponse(access_token=create_access_token(expert), expert_id=expert.id, expert_name=expert.name)


@router.get("/google/config", response_model=GoogleConfigResponse)
def google_config():
    """Expose the public OAuth client ID needed by Google Identity Services."""
    client_id = (get_settings().google_client_id or "").strip()
    return GoogleConfigResponse(client_id=client_id or None)


@router.post("/google", response_model=LoginResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    client_id = (get_settings().google_client_id or "").strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID on the backend.",
        )

    try:
        claims = id_token.verify_oauth2_token(payload.credential, GoogleRequest(), audience=client_id)
    except (ValueError, GoogleAuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in failed. Please try again.",
        ) from None

    email = claims.get("email")
    subject = claims.get("sub")
    if (
        not isinstance(email, str)
        or claims.get("email_verified") is not True
        or not isinstance(subject, str)
        or not subject
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google must verify your email address before you can sign in.",
        )
    try:
        normalized_email = email_adapter.validate_python(email).lower()
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google returned an invalid email.") from None
    if len(normalized_email) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This Google email address is too long.")

    expert = db.scalar(select(Expert).where(func.lower(Expert.email) == normalized_email))
    if expert is None:
        name = claims.get("name")
        expert = Expert(
            name=name.strip()[:120] if isinstance(name, str) and name.strip() else normalized_email.split("@", 1)[0],
            email=normalized_email,
            password_hash=pwd_context.hash(secrets.token_urlsafe(32)),
            is_active=True,
            is_demo=False,
        )
        db.add(expert)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            expert = db.scalar(select(Expert).where(func.lower(Expert.email) == normalized_email))
            if expert is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Could not create your expert account. Please try again.",
                ) from None

    if not expert.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This expert account is disabled.")

    return LoginResponse(
        access_token=create_access_token(expert),
        expert_id=expert.id,
        expert_name=expert.name,
    )


@router.get("/me", response_model=ExpertProfileResponse)
def current_expert(expert: Expert = Depends(require_expert)):
    return profile_response(expert)


@router.patch("/me", response_model=ExpertProfileResponse)
def update_current_expert(
    payload: ExpertProfileUpdate,
    db: Session = Depends(get_db),
    expert: Expert = Depends(require_expert),
):
    """Update only the authenticated expert's own profile."""
    expert.name = payload.name
    expert.contact = payload.phone_number
    db.commit()
    db.refresh(expert)
    return profile_response(expert)


def market_account_response(principal: Farmer | Worker, account_type: str) -> dict:
    return {
        "access_token": create_access_token(principal, account_type),
        "token_type": "bearer",
        "account_type": account_type,
        "id": principal.id,
        "name": principal.name,
        "username": principal.username,
    }


@router.post("/market/register", status_code=status.HTTP_201_CREATED)
def register_market_account(payload: MarketAccountRequest, db: Session = Depends(get_db)):
    model = Farmer if payload.account_type == "farmer" else Worker
    principal = model(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        name=payload.username,
        **(
            {"district": "Nalgonda", "mobile": payload.phone}
            if payload.account_type == "farmer"
            else {"phone": payload.phone}
        ),
    )
    db.add(principal)
    try:
        db.commit()
        db.refresh(principal)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username or contact number is already in use for this account type.",
        ) from None
    return market_account_response(principal, payload.account_type)


@router.post("/market/login")
def login_market_account(payload: MarketAccountRequest, db: Session = Depends(get_db)):
    model = Farmer if payload.account_type == "farmer" else Worker
    principal = db.scalar(select(model).where(func.lower(model.username) == payload.username))
    if principal is None or not principal.password_hash or not verify_password(payload.password, principal.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    return market_account_response(principal, payload.account_type)
