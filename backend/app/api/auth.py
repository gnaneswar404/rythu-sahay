from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farmer, Worker
from app.services.auth import create_access_token, pwd_context, verify_password

router = APIRouter(prefix="/auth", tags=["marketplace authentication"])


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
