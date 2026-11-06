from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Farmer
from app.schemas.conversation import CallStart, ConversationMessage, ConversationReply
from app.services.auth import optional_farmer
from app.services.conversation import end_session, respond_to_message, start_session

router = APIRouter(prefix="/calls", tags=["farmer conversation"])


@router.post("/start", response_model=ConversationReply)
def start_call(
    payload: CallStart,
    db: Session = Depends(get_db),
    farmer: Farmer | None = Depends(optional_farmer),
):
    state = start_session(payload.session_id, farmer.id if farmer else None, payload.consent_recording)
    response = "నమస్కారం. రీతు సహాయకు స్వాగతం. నల్గొండ జిల్లా పత్తి పంటలో మీ సమస్యను సులభంగా చెప్పండి."
    return ConversationReply(session_id=state.session_id, response=response, mock_voice=get_settings().mock_voice_enabled)


@router.post("/message", response_model=ConversationReply)
def send_message(
    payload: ConversationMessage,
    db: Session = Depends(get_db),
    farmer: Farmer | None = Depends(optional_farmer),
):
    result = respond_to_message(db, payload.session_id, payload.message, farmer.id if farmer else None)
    return ConversationReply(session_id=payload.session_id, recognized_text=payload.message, mock_voice=get_settings().mock_voice_enabled, **result)


@router.post("/audio", response_model=ConversationReply)
async def submit_audio(session_id: str, audio: UploadFile = File(...), db: Session = Depends(get_db)):
    """Safe local fallback: browsers use Web Speech recognition; Sarvam adapter is intentionally credential-gated."""
    if not get_settings().mock_voice_enabled:
        raise HTTPException(status_code=503, detail="Speech provider is not configured yet.")
    await audio.read()
    response = "డెమో మోడ్‌లో ఆడియోను స్వయంచాలకంగా గుర్తించలేకపోయాము. దయచేసి టెక్స్ట్ లేదా కీప్యాడ్ ఉపయోగించండి."
    return ConversationReply(session_id=session_id, response=response, mock_voice=True)


@router.post("/end")
def end_call(session_id: str):
    ended = end_session(session_id)
    return {"session_id": session_id, "ended": ended, "message": "Session ended. Recording has stopped."}
