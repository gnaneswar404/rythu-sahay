from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Case, CaseAction, CaseStatus, Expert, Farmer, Followup, Severity
from app.schemas.cases import AssignmentCreate, CaseCreate, FeedbackCreate, FollowupCreate, NoteCreate, StatusUpdate


def get_case_or_404(db: Session, case_id: str, detailed: bool = False) -> Case:
    query = select(Case).where(Case.id == case_id)
    if detailed:
        query = query.options(joinedload(Case.farmer), joinedload(Case.actions), joinedload(Case.followups))
    result = db.execute(query).unique().scalar_one_or_none()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return result


def create_case_id(db: Session) -> str:
    year = datetime.now().year
    prefix = f"RS-{year}-"
    count = db.scalar(select(func.count()).select_from(Case).where(Case.id.like(f"{prefix}%"))) or 0
    return f"{prefix}{count + 1:04d}"


def create_case(db: Session, payload: CaseCreate, is_demo: bool = False) -> Case:
    farmer = db.get(Farmer, payload.farmer_id)
    if farmer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found.")
    case_data = payload.model_dump()
    case_data["village"] = payload.village or farmer.village
    case_data["mandal"] = payload.mandal or farmer.mandal
    case = Case(id=create_case_id(db), **case_data, is_demo=is_demo)
    db.add(case)
    db.add(CaseAction(case=case, action_type="CASE_CREATED", description="Farmer case created.", source="System"))
    db.commit()
    db.refresh(case)
    return case


def update_status(db: Session, case_id: str, payload: StatusUpdate) -> Case:
    case = get_case_or_404(db, case_id)
    case.status = payload.status
    if payload.recommended_next_action is not None:
        case.recommended_next_action = payload.recommended_next_action
    if payload.resolution_outcome is not None:
        case.resolution_outcome = payload.resolution_outcome
    db.add(CaseAction(case=case, action_type="STATUS_UPDATED", description=f"Status changed to {payload.status.value}.", source="Expert dashboard"))
    db.commit()
    db.refresh(case)
    return case


def assign_case(db: Session, case_id: str, payload: AssignmentCreate) -> Case:
    case = get_case_or_404(db, case_id)
    expert = db.get(Expert, payload.expert_id)
    if expert is None or not expert.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active expert not found.")
    case.expert_id = expert.id
    case.status = CaseStatus.ASSIGNED
    db.add(CaseAction(case=case, action_type="EXPERT_ASSIGNED", description=f"Assigned to {expert.name}.", source="System", expert_approved=True))
    db.commit()
    db.refresh(case)
    return case


def add_note(db: Session, case_id: str, payload: NoteCreate) -> CaseAction:
    case = get_case_or_404(db, case_id)
    action = CaseAction(case=case, action_type="EXPERT_NOTE", **payload.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def schedule_followup(db: Session, case_id: str, payload: FollowupCreate) -> Followup:
    case = get_case_or_404(db, case_id)
    followup = Followup(case=case, **payload.model_dump())
    case.status = CaseStatus.FOLLOW_UP_PENDING
    db.add(followup)
    db.add(CaseAction(case=case, action_type="FOLLOWUP_SCHEDULED", description=f"Follow-up scheduled for {payload.scheduled_date.isoformat()}.", source="Expert dashboard"))
    db.commit()
    db.refresh(followup)
    return followup


def record_feedback(db: Session, case_id: str, payload: FeedbackCreate) -> Followup:
    case = get_case_or_404(db, case_id)
    followup = db.scalar(select(Followup).where(Followup.case_id == case_id, Followup.completed_at.is_(None)).order_by(Followup.scheduled_date))
    if followup is None:
        followup = Followup(case=case, scheduled_date=date.today())
        db.add(followup)
    followup.outcome = payload.outcome
    followup.farmer_response = payload.farmer_response
    followup.completed_at = datetime.now()
    if payload.outcome == "WORSENED":
        case.status = CaseStatus.ESCALATED
    elif payload.outcome == "IMPROVED":
        case.status = CaseStatus.RESOLVED
    else:
        case.status = CaseStatus.UNDER_REVIEW
    db.add(CaseAction(case=case, action_type="FARMER_FEEDBACK", description=f"Farmer reported {payload.outcome}.", source="Farmer follow-up"))
    db.commit()
    db.refresh(followup)
    return followup
