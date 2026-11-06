import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cases import (
    CaseCreate,
    CaseRead,
    FeedbackCreate,
    FollowupRead,
)
from app.services.auth import optional_farmer
from app.services.cases import create_case, get_case_or_404, record_feedback

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_farmer_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    farmer=Depends(optional_farmer),
):
    if farmer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Farmer account authentication is required to create a case.")
    return create_case(db, payload.model_copy(update={"farmer_id": farmer.id}))


@router.post("/{case_id}/feedback", response_model=FollowupRead)
def receive_feedback(
    case_id: str,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    case_access_token: str | None = Header(default=None, alias="X-Case-Access-Token"),
    farmer=Depends(optional_farmer),
):
    """Farmer-facing outcome endpoint; a worsened report is automatically escalated."""
    case = get_case_or_404(db, case_id)
    is_owner = farmer is not None and farmer.id == case.farmer_id
    has_case_token = case_access_token and secrets.compare_digest(case.farmer_access_token, case_access_token)
    if not is_owner and not has_case_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A valid farmer session or case token is required.")
    return record_feedback(db, case_id, payload)
