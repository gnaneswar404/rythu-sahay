import json
import secrets
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models import Case, CaseAction, CaseStatus, Expert, Severity
from app.schemas.cases import (
    AssignmentCreate,
    CaseCreate,
    CaseDetail,
    CaseRead,
    FeedbackCreate,
    FollowupCreate,
    FollowupRead,
    NoteCreate,
    StatusUpdate,
)
from app.services.auth import optional_farmer, require_expert
from app.services.cases import add_note, assign_case, create_case, get_case_or_404, record_feedback, schedule_followup, update_status

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


@router.get("", response_model=list[CaseRead])
def list_cases(
    case_status: CaseStatus | None = None,
    severity: Severity | None = None,
    village: str | None = None,
    mandal: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: Expert = Depends(require_expert),
):
    query = select(Case).order_by(Case.created_at.desc())
    if case_status:
        query = query.where(Case.status == case_status)
    if severity:
        query = query.where(Case.severity == severity)
    if village:
        query = query.where(Case.village.ilike(f"%{village}%"))
    if mandal:
        query = query.where(Case.mandal.ilike(f"%{mandal}%"))
    if search:
        query = query.where((Case.id.ilike(f"%{search}%")) | (Case.description.ilike(f"%{search}%")))
    return list(db.scalars(query))


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    return get_case_or_404(db, case_id, detailed=True)


@router.patch("/{case_id}/status", response_model=CaseRead)
def patch_status(case_id: str, payload: StatusUpdate, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    return update_status(db, case_id, payload)


@router.post("/{case_id}/assign", response_model=CaseRead)
def assign(case_id: str, payload: AssignmentCreate, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    return assign_case(db, case_id, payload)


@router.post("/{case_id}/notes", status_code=status.HTTP_201_CREATED)
def add_expert_note(case_id: str, payload: NoteCreate, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    return add_note(db, case_id, payload)


@router.post("/{case_id}/followups", response_model=FollowupRead, status_code=status.HTTP_201_CREATED)
def create_followup(case_id: str, payload: FollowupCreate, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    return schedule_followup(db, case_id, payload)


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


@router.post("/{case_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_case_photo(
    case_id: str,
    photo: UploadFile = File(...),
    case_access_token: str | None = Header(default=None, alias="X-Case-Access-Token"),
    db: Session = Depends(get_db),
):
    """Farmer-upload flow. The per-case token is returned only to that browser after case creation."""
    case = get_case_or_404(db, case_id)
    if not case_access_token or not secrets.compare_digest(case.farmer_access_token, case_access_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A valid farmer case token is required to upload a photo.")
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    suffix = allowed.get(photo.content_type or "")
    if suffix is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only JPG, PNG, and WebP photographs are accepted.")
    content = await photo.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Photograph must be 5 MB or smaller.")
    filename = f"{case.id}-{uuid4().hex}{suffix}"
    upload_path = Path(get_settings().upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    (upload_path / filename).write_bytes(content)
    urls = json.loads(case.image_urls or "[]")
    url = f"/uploads/{filename}"
    urls.append(url)
    case.image_urls = json.dumps(urls)
    db.add(CaseAction(case=case, action_type="PHOTO_UPLOADED", description="Farmer crop photograph uploaded.", source="Farmer interface"))
    db.commit()
    return {"url": url, "message": "Photo uploaded successfully."}


@router.get("/{case_id}/photos/{filename}")
def get_case_photo(
    case_id: str,
    filename: str,
    db: Session = Depends(get_db),
    _: Expert = Depends(require_expert),
):
    case = get_case_or_404(db, case_id)
    if Path(filename).name != filename or not filename.startswith(f"{case_id}-"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if f"/uploads/{filename}" not in json.loads(case.image_urls or "[]"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    photo_path = Path(get_settings().upload_dir) / filename
    if not photo_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    media_type = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(photo_path.suffix.lower())
    return FileResponse(
        photo_path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
