from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.telephony.factory import get_telephony_provider

router = APIRouter(prefix="/telephony", tags=["telephony"])


class IncomingCall(BaseModel):
    caller_number: str | None = Field(default=None, max_length=20)
    call_id: str = Field(min_length=4, max_length=100)
    digits: str | None = Field(default=None, max_length=30)


@router.post("/incoming")
def incoming_call(payload: IncomingCall):
    """Provider-neutral mock webhook. Real Exotel handling stays disabled without credentials."""
    if not get_settings().mock_telephony_enabled:
        raise HTTPException(status_code=503, detail="Telephony provider adapter is not configured.")
    return get_telephony_provider().incoming_call_response(payload.call_id, payload.caller_number, payload.digits)
