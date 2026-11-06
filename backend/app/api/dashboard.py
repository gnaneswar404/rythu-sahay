from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, CaseStatus, Expert, Followup
from app.services.auth import require_expert

router = APIRouter(prefix="/dashboard", tags=["expert dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    def count_by_status(status: CaseStatus) -> int:
        return db.scalar(select(func.count()).select_from(Case).where(Case.status == status)) or 0

    pending_followups = db.scalar(
        select(func.count()).select_from(Followup).where(Followup.completed_at.is_(None), Followup.scheduled_date <= date.today())
    ) or 0
    return {
        "total_cases": db.scalar(select(func.count()).select_from(Case)) or 0,
        "new_cases": count_by_status(CaseStatus.NEW),
        "pending_cases": count_by_status(CaseStatus.UNDER_REVIEW) + count_by_status(CaseStatus.FOLLOW_UP_PENDING),
        "escalated_cases": count_by_status(CaseStatus.ESCALATED),
        "resolved_cases": count_by_status(CaseStatus.RESOLVED),
        "pending_followups": pending_followups,
        "demo_data_notice": "Dashboard includes clearly labelled synthetic demonstration data.",
    }
