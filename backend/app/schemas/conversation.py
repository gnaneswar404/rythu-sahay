from pydantic import Field

from app.schemas.common import ORMModel


class CallStart(ORMModel):
    session_id: str | None = Field(default=None, max_length=80)
    consent_recording: bool = False


class ConversationMessage(ORMModel):
    session_id: str = Field(min_length=4, max_length=80)
    message: str = Field(min_length=1, max_length=2000)


class ConversationReply(ORMModel):
    session_id: str
    response: str
    recognized_text: str | None = None
    next_question_key: str | None = None
    case_id: str | None = None
    case_access_token: str | None = None
    needs_expert_review: bool = False
    mock_voice: bool = True
