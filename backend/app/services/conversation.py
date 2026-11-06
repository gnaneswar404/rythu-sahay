from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.tools import AgriculturalAgentTools
from app.models import CaseAction, CaseStatus, Conversation, Farmer, Severity
from app.schemas.cases import CaseCreate


@dataclass
class SessionState:
    session_id: str
    farmer_id: int | None = None
    consent_recording: bool = False
    stage: int = 0
    answers: list[str] = field(default_factory=list)
    case_id: str | None = None


_sessions: dict[str, SessionState] = {}
_outside_scope_terms = ("వరి", "rice", "మిర్చి", "chilli", "మొక్కజొన్న", "maize")
_urgent_terms = ("వాడిపో", "చనిపో", "తీవ్ర", "మొత్తం", "wilt")


def start_session(session_id: str | None, farmer_id: int | None, consent_recording: bool) -> SessionState:
    state = SessionState(session_id=session_id or str(uuid4()), farmer_id=farmer_id, consent_recording=consent_recording)
    _sessions[state.session_id] = state
    return state


def _save_message(db: Session, state: SessionState, message: str, speaker: str, case_id: str | None = None) -> None:
    db.add(Conversation(farmer_id=state.farmer_id, case_id=case_id or state.case_id, session_id=state.session_id, message=message, speaker=speaker))
    db.commit()


def _ensure_farmer(db: Session, state: SessionState) -> int:
    if state.farmer_id is not None:
        return state.farmer_id
    farmer = Farmer(
        name=None,
        district="Nalgonda",
        preferred_language="te",
        consent_recording=state.consent_recording,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    state.farmer_id = farmer.id
    return farmer.id


def respond_to_message(db: Session, session_id: str, message: str, farmer_id: int | None = None) -> dict:
    state = _sessions.get(session_id)
    if state is None:
        state = start_session(session_id, farmer_id, False)
    if farmer_id is not None:
        state.farmer_id = farmer_id
    text = message.strip()
    _save_message(db, state, text, "FARMER")
    lowered = text.lower()
    if any(term in lowered for term in _outside_scope_terms):
        response = "క్షమించండి, ఈ పైలట్ ప్రస్తుతం నల్గొండ జిల్లా పత్తి రైతులకే అందుబాటులో ఉంది."
        _save_message(db, state, response, "ASSISTANT")
        return {"response": response, "next_question_key": "scope"}
    if state.case_id:
        response = "మీ కేసు ఇప్పటికే నమోదైంది. అదనపు సలహా కోసం స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి."
        _save_message(db, state, response, "ASSISTANT")
        return {"response": response, "case_id": state.case_id, "next_question_key": None}

    state.answers.append(text)
    prompts = [
        "ఈ సమస్య ఎన్ని రోజులుగా కనిపిస్తోంది?",
        "ఆకులపై మచ్చలు, ముడతలు లేదా పురుగులు కనిపిస్తున్నాయా?",
        "మీ గ్రామం పేరు చెప్పండి.",
        "మీ మండలం పేరు చెప్పండి.",
    ]
    if state.stage < len(prompts):
        response = prompts[state.stage]
        state.stage += 1
        _save_message(db, state, response, "ASSISTANT")
        return {"response": response, "next_question_key": f"question_{state.stage}"}

    farmer_db_id = _ensure_farmer(db, state)
    description = state.answers[0]
    symptoms = state.answers[2] if len(state.answers) > 2 else None
    village = state.answers[3] if len(state.answers) > 3 else None
    mandal = state.answers[4] if len(state.answers) > 4 else None
    severe = any(term in " ".join(state.answers).lower() for term in _urgent_terms)
    case = AgriculturalAgentTools(db).create_case(
        CaseCreate(
            farmer_id=farmer_db_id,
            crop="cotton",
            village=village,
            mandal=mandal,
            district="Nalgonda",
            problem_category="పంట సమస్య",
            description=description,
            symptoms=symptoms,
            severity=Severity.HIGH if severe else Severity.MEDIUM,
            ai_summary="తెలుగు వాయిస్/టెక్స్ట్ డెమోలో సేకరించిన సమాచారం. కారణం నిర్ధారించబడలేదు.",
        ),
    )
    if severe:
        case.status = CaseStatus.ESCALATED
        db.add(CaseAction(case=case, action_type="AUTO_ESCALATED", description="Potentially severe symptoms reported; farmer advised to seek local agricultural guidance.", source="Safety triage"))
        db.commit()
    state.case_id = case.id
    response = f"ధన్యవాదాలు. మీ అభ్యర్థన {case.id}గా నమోదు చేశాము. తదుపరి సలహా కోసం స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి. ధృవీకరించిన మార్గదర్శకం లేకుండా మందులు వాడవద్దు."
    _save_message(db, state, response, "ASSISTANT", case.id)
    return {
        "response": response,
        "case_id": case.id,
        "case_access_token": case.farmer_access_token,
        "next_question_key": None,
    }


def end_session(session_id: str) -> bool:
    return _sessions.pop(session_id, None) is not None
