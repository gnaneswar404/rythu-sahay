import hashlib
import math
import re
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import (
    Case, Farmer, JobApplication, JobBooking, JobBookingMessage, MarketJob, MarketTeam, MarketTeamMember, Worker,
)
from app.schemas.cases import CaseRead
from app.schemas.marketplace import (
    ApplicationCreate, BookingMessageCreate, FarmerProfileUpdate, MarketJobCreate, TeamCreate, TeamMemberCreate,
    WageOffer, WorkerProfileUpdate,
)
from app.services.auth import require_farmer, require_worker

router = APIRouter(prefix="/market", tags=["worker marketplace"])
ACTIVE_BOOKING_STATUSES = ("PENDING", "CONFIRMED")
MAX_PROFILE_PHOTO_BYTES = 3 * 1024 * 1024
PROFILE_PHOTO_TYPES = {
    "image/jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    "image/png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda content: len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP",
}


def _profile_photo_url(account_type: str, account_id: int, photo_data: bytes | None) -> str | None:
    if photo_data is None:
        return None
    version = hashlib.sha256(photo_data).hexdigest()[:16]
    return (
        f"{get_settings().api_prefix.rstrip('/')}/market/public/profile-photos/"
        f"{account_type}/{account_id}?v={version}"
    )


async def _read_profile_photo(photo: UploadFile) -> tuple[bytes, str]:
    media_type = (photo.content_type or "").lower()
    signature_check = PROFILE_PHOTO_TYPES.get(media_type)
    if signature_check is None:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP profile photo.")
    content = await photo.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(content) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Profile photos must be 3 MB or smaller.")
    if not signature_check(content):
        raise HTTPException(status_code=415, detail="The uploaded file does not match its image type.")
    return content, media_type


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lon / 2) ** 2
    value = min(1.0, max(0.0, value))
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _normalized_location(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _has_skill_match(skills: str, text: str) -> bool:
    terms = [term for term in re.findall(r"\w+", skills.casefold()) if len(term) > 1]
    normalized_text = text.casefold()
    return any(term in normalized_text for term in terms)


def _job_data(
    job: MarketJob,
    distance: float | None = None,
    progress: dict[str, int] | None = None,
) -> dict:
    return {
        "id": job.id,
        "farmer_id": job.farmer_id,
        "title": job.title,
        "description": job.description,
        "village": job.village,
        "mandal": job.mandal,
        "latitude": job.latitude,
        "longitude": job.longitude,
        "work_date": job.work_date,
        "required_workers": job.required_workers,
        "daily_wage": job.daily_wage,
        "status": job.status,
        "created_at": job.created_at,
        "distance_km": round(distance, 1) if distance is not None else None,
        **(progress or {}),
    }


def _job_progress(db: Session, jobs: list[MarketJob]) -> dict[int, dict[str, int]]:
    job_ids = [job.id for job in jobs]
    progress = {
        job.id: {
            "interested_workers": 0,
            "pending_workers": 0,
            "confirmed_workers": 0,
            "remaining_workers": job.required_workers,
        }
        for job in jobs
    }
    if not job_ids:
        return progress

    applications = db.execute(
        select(
            JobApplication.job_id,
            JobApplication.worker_id,
            MarketTeamMember.worker_id,
        )
        .outerjoin(MarketTeamMember, MarketTeamMember.team_id == JobApplication.team_id)
        .where(
            JobApplication.job_id.in_(job_ids),
            JobApplication.status != "CANCELLED",
        )
    )
    interested_workers: dict[int, set[int]] = defaultdict(set)
    for job_id, applicant_id, team_member_id in applications:
        interested_workers[job_id].add(applicant_id)
        if team_member_id is not None:
            interested_workers[job_id].add(team_member_id)
    for job_id, worker_ids in interested_workers.items():
        progress[job_id]["interested_workers"] = len(worker_ids)

    booking_counts = db.execute(
        select(JobBooking.job_id, JobBooking.status, func.count(JobBooking.id))
        .where(
            JobBooking.job_id.in_(job_ids),
            JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
        )
        .group_by(JobBooking.job_id, JobBooking.status)
    )
    active_by_job: dict[int, int] = defaultdict(int)
    for job_id, booking_status, count in booking_counts:
        active_by_job[job_id] += count
        if booking_status == "CONFIRMED":
            progress[job_id]["confirmed_workers"] += count
        elif booking_status == "PENDING":
            progress[job_id]["pending_workers"] += count
    for job in jobs:
        progress[job.id]["remaining_workers"] = max(
            job.required_workers - active_by_job[job.id],
            0,
        )
    return progress


def _public_job_data(job: MarketJob, progress: dict[str, int] | None = None) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "recruiter_id": job.farmer.id,
        "recruiter_name": job.farmer.name or "Farmer",
        "recruiter_photo_url": _profile_photo_url("farmer", job.farmer.id, job.farmer.profile_photo_data),
        "village": job.village,
        "mandal": job.mandal,
        "work_date": job.work_date,
        "required_workers": job.required_workers,
        "daily_wage": job.daily_wage,
        **(progress or {}),
    }


def _public_worker_data(worker: Worker) -> dict:
    return {
        "id": worker.id,
        "name": worker.name,
        "profile_photo_url": _profile_photo_url("worker", worker.id, worker.profile_photo_data),
        "village": worker.village,
        "mandal": worker.mandal,
        "skills": worker.skills,
        "daily_wage": worker.daily_wage,
        "is_available": worker.is_available,
    }


def _team_data(team: MarketTeam) -> dict:
    members = [item.worker for item in team.members]
    return {
        "id": team.id,
        "name": team.name,
        "leader_id": team.leader_id,
        "member_count": len(members),
        "skills": sorted({
            skill.strip()
            for member in members
            for skill in member.skills.split(",")
            if skill.strip()
        }),
        "is_available": all(member.is_available for member in members),
        "members": [{"id": member.id, "name": member.name} for member in members],
        "created_at": team.created_at,
    }


def _application_data(application: JobApplication) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "worker_id": application.worker_id,
        "worker_name": application.worker.name,
        "team_id": application.team_id,
        "team_name": application.team.name if application.team else None,
        "team_size": len(application.team.members) if application.team else 1,
        "team_skills": _team_data(application.team)["skills"] if application.team else application.worker.skills,
        "team_available": all(member.worker.is_available for member in application.team.members) if application.team else application.worker.is_available,
        "job_daily_wage": application.job.daily_wage,
        "proposed_wage": application.proposed_wage,
        "agreed_wage": application.proposed_wage if application.status == "ACCEPTED" else None,
        "status": application.status,
        "created_at": application.created_at,
    }


def _booking_data(booking: JobBooking, include_contact: bool) -> dict:
    job = booking.job
    return {
        "id": booking.id,
        "job_id": job.id,
        "job_title": job.title,
        "village": job.village,
        "work_date": booking.work_date,
        "agreed_wage": booking.agreed_wage,
        "status": booking.status,
        "worker_id": booking.worker_id,
        "worker_name": booking.worker.name,
        "worker_phone": booking.worker.phone if include_contact and booking.worker.allow_phone_contact else None,
        "farmer_name": job.farmer.name if include_contact and job.farmer.allow_phone_contact else None,
        "farmer_phone": job.farmer.mobile if include_contact and job.farmer.allow_phone_contact else None,
    }


def _booking_for_participant(booking_id: int, db: Session, principal_id: int, principal_type: str) -> JobBooking:
    booking = db.scalar(
        select(JobBooking)
        .where(JobBooking.id == booking_id)
        .options(joinedload(JobBooking.job), joinedload(JobBooking.worker))
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    is_participant = (
        booking.worker_id == principal_id
        if principal_type == "worker"
        else booking.job.farmer_id == principal_id
    )
    if not is_participant:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking


def _booking_messages(booking_id: int, db: Session, principal_id: int, principal_type: str) -> list[dict]:
    _booking_for_participant(booking_id, db, principal_id, principal_type)
    messages = db.scalars(
        select(JobBookingMessage)
        .where(JobBookingMessage.booking_id == booking_id)
        .order_by(JobBookingMessage.created_at, JobBookingMessage.id)
    )
    return [
        {
            "id": item.id,
            "booking_id": item.booking_id,
            "sender_type": item.sender_type,
            "sender_id": item.sender_id,
            "sender_name": item.sender_name,
            "message": item.message,
            "created_at": item.created_at,
        }
        for item in messages
    ]


def _send_booking_message(
    booking_id: int,
    payload: BookingMessageCreate,
    db: Session,
    principal_id: int,
    principal_type: str,
    principal: Farmer | Worker,
) -> dict:
    booking = _booking_for_participant(booking_id, db, principal_id, principal_type)
    if booking.status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Messages cannot be sent for a cancelled booking.")
    message = JobBookingMessage(
        booking_id=booking.id,
        sender_type=principal_type,
        sender_id=principal.id,
        sender_name=principal.name or ("Farmer" if principal_type == "farmer" else "Worker"),
        message=payload.message,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "booking_id": message.booking_id,
        "sender_type": message.sender_type,
        "sender_id": message.sender_id,
        "sender_name": message.sender_name,
        "message": message.message,
        "created_at": message.created_at,
    }


def _job_or_404(db: Session, job_id: int) -> MarketJob:
    job = db.get(MarketJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _application_or_404(db: Session, application_id: int) -> JobApplication:
    application = db.scalar(
        select(JobApplication)
        .options(joinedload(JobApplication.worker), joinedload(JobApplication.team).joinedload(MarketTeam.members))
        .where(JobApplication.id == application_id)
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return application


@router.get("/farmer/cases")
def farmer_cases(db: Session = Depends(get_db), farmer: Farmer = Depends(require_farmer)):
    cases = db.scalars(select(Case).where(Case.farmer_id == farmer.id).order_by(Case.created_at.desc()))
    return [CaseRead.model_validate(case) for case in cases]


@router.get("/farmer/profile")
def farmer_profile(farmer: Farmer = Depends(require_farmer)):
    return {
        "id": farmer.id,
        "name": farmer.name,
        "phone": farmer.mobile,
        "village": farmer.village,
        "mandal": farmer.mandal,
        "latitude": farmer.latitude,
        "longitude": farmer.longitude,
        "preferred_language": farmer.preferred_language,
        "allow_phone_contact": farmer.allow_phone_contact,
        "profile_photo_url": _profile_photo_url("farmer", farmer.id, farmer.profile_photo_data),
    }


@router.patch("/farmer/profile")
def update_farmer_profile(
    payload: FarmerProfileUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "allow_phone_contact" and value is None:
            continue
        setattr(farmer, key, value)
    db.commit()
    db.refresh(farmer)
    return farmer_profile(farmer)


@router.post("/farmer/profile/photo")
async def upload_farmer_profile_photo(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    farmer.profile_photo_data, farmer.profile_photo_media_type = await _read_profile_photo(photo)
    db.commit()
    return {"profile_photo_url": _profile_photo_url("farmer", farmer.id, farmer.profile_photo_data)}


@router.delete("/farmer/profile/photo")
def delete_farmer_profile_photo(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    farmer.profile_photo_data = None
    farmer.profile_photo_media_type = None
    db.commit()
    return {"profile_photo_url": None}


@router.get("/worker/profile")
def worker_profile(worker: Worker = Depends(require_worker)):
    return {
        "id": worker.id,
        "name": worker.name,
        "phone": worker.phone,
        "village": worker.village,
        "mandal": worker.mandal,
        "latitude": worker.latitude,
        "longitude": worker.longitude,
        "skills": worker.skills,
        "daily_wage": worker.daily_wage,
        "is_available": worker.is_available,
        "allow_phone_contact": worker.allow_phone_contact,
        "profile_photo_url": _profile_photo_url("worker", worker.id, worker.profile_photo_data),
    }


@router.patch("/worker/profile")
def update_worker_profile(
    payload: WorkerProfileUpdate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "allow_phone_contact" and value is None:
            continue
        setattr(worker, key, value)
    db.commit()
    db.refresh(worker)
    return worker_profile(worker)


@router.post("/worker/profile/photo")
async def upload_worker_profile_photo(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    worker.profile_photo_data, worker.profile_photo_media_type = await _read_profile_photo(photo)
    db.commit()
    return {"profile_photo_url": _profile_photo_url("worker", worker.id, worker.profile_photo_data)}


@router.delete("/worker/profile/photo")
def delete_worker_profile_photo(
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    worker.profile_photo_data = None
    worker.profile_photo_media_type = None
    db.commit()
    return {"profile_photo_url": None}


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: MarketJobCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    if payload.work_date < date.today():
        raise HTTPException(status_code=422, detail="Work date cannot be in the past.")
    job = MarketJob(farmer_id=farmer.id, **payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_data(job, progress=_job_progress(db, [job])[job.id])


@router.get("/jobs/mine")
def my_jobs(db: Session = Depends(get_db), farmer: Farmer = Depends(require_farmer)):
    jobs = list(db.scalars(
        select(MarketJob).where(MarketJob.farmer_id == farmer.id).order_by(MarketJob.work_date.desc())
    ))
    progress = _job_progress(db, jobs)
    return [_job_data(job, progress=progress[job.id]) for job in jobs]


@router.get("/public/jobs")
def public_jobs(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        select(MarketJob)
        .join(MarketJob.farmer)
        .where(MarketJob.status == "OPEN", MarketJob.work_date >= date.today())
        .options(joinedload(MarketJob.farmer))
        .order_by(MarketJob.work_date, MarketJob.created_at.desc())
        .limit(limit)
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            MarketJob.title.ilike(term)
            | MarketJob.description.ilike(term)
            | MarketJob.village.ilike(term)
            | MarketJob.mandal.ilike(term)
            | Farmer.name.ilike(term)
        )
    jobs = list(db.scalars(query))
    progress = _job_progress(db, jobs)
    return [_public_job_data(job, progress[job.id]) for job in jobs]


@router.get("/public/profile-photos/{account_type}/{account_id}")
def public_profile_photo(
    account_type: str,
    account_id: int,
    db: Session = Depends(get_db),
):
    if account_type == "farmer":
        account = db.get(Farmer, account_id)
    elif account_type == "worker":
        account = db.get(Worker, account_id)
    else:
        raise HTTPException(status_code=404, detail="Profile photo not found.")
    if account is None or account.profile_photo_data is None or account.profile_photo_media_type is None:
        raise HTTPException(status_code=404, detail="Profile photo not found.")
    return Response(
        content=account.profile_photo_data,
        media_type=account.profile_photo_media_type,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/public/profiles/{account_type}/{account_id}")
def public_profile(
    account_type: str,
    account_id: int,
    db: Session = Depends(get_db),
):
    if account_type == "farmer":
        account = db.get(Farmer, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Profile not found.")
        jobs = db.scalars(
            select(MarketJob)
            .where(
                MarketJob.farmer_id == account.id,
                MarketJob.status == "OPEN",
                MarketJob.work_date >= date.today(),
            )
            .order_by(MarketJob.work_date, MarketJob.created_at.desc())
            .limit(50)
        )
        return {
            "id": account.id,
            "account_type": "farmer",
            "name": account.name or "Farmer",
            "profile_photo_url": _profile_photo_url("farmer", account.id, account.profile_photo_data),
            "phone": account.mobile if account.allow_phone_contact else None,
            "village": account.village,
            "mandal": account.mandal,
            "jobs": [_public_job_data(job) for job in jobs],
        }
    if account_type == "worker":
        account = db.get(Worker, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Profile not found.")
        return {
            "id": account.id,
            "account_type": "worker",
            "name": account.name,
            "profile_photo_url": _profile_photo_url("worker", account.id, account.profile_photo_data),
            "phone": account.phone if account.allow_phone_contact else None,
            "village": account.village,
            "mandal": account.mandal,
            "skills": account.skills,
            "daily_wage": account.daily_wage,
            "is_available": account.is_available,
        }
    raise HTTPException(status_code=404, detail="Profile not found.")


@router.get("/public/workers")
def public_workers(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        select(Worker)
        .where(Worker.is_available.is_(True))
        .order_by(Worker.name)
        .limit(limit)
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Worker.name.ilike(term)
            | Worker.skills.ilike(term)
            | Worker.village.ilike(term)
            | Worker.mandal.ilike(term)
        )
    return [_public_worker_data(worker) for worker in db.scalars(query)]


@router.get("/jobs/nearby")
def nearby_jobs(
    radius_km: float = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    worker_village = _normalized_location(worker.village)
    jobs = list(db.scalars(
        select(MarketJob).where(MarketJob.status == "OPEN", MarketJob.work_date >= date.today())
        .order_by(MarketJob.work_date).limit(500)
    ))
    progress = _job_progress(db, jobs)
    matches = []
    for job in jobs:
        same_village = bool(worker_village and worker_village == _normalized_location(job.village))
        if worker.latitude is not None and worker.longitude is not None and job.latitude is not None and job.longitude is not None:
            distance = _distance_km(worker.latitude, worker.longitude, job.latitude, job.longitude)
            if distance > radius_km:
                continue
        elif same_village:
            distance = None
        else:
            continue
        result = _job_data(job, distance, progress[job.id])
        result["same_village"] = same_village
        result["skill_match"] = _has_skill_match(worker.skills, f"{job.title} {job.description}")
        result["wage_match"] = worker.daily_wage is None or job.daily_wage >= worker.daily_wage
        matches.append(result)
    return sorted(
        matches,
        key=lambda match: (
            not match["same_village"],
            not match["skill_match"],
            not match["wage_match"],
            match["distance_km"] if match["distance_km"] is not None else float("inf"),
            match["work_date"],
        ),
    )


@router.get("/workers/nearby")
def nearby_workers(
    radius_km: float = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    farmer_village = _normalized_location(farmer.village)
    jobs = list(db.scalars(
        select(MarketJob).where(
            MarketJob.farmer_id == farmer.id,
            MarketJob.status == "OPEN",
            MarketJob.work_date >= date.today(),
        )
    ))
    workers = db.scalars(select(Worker).where(Worker.is_available.is_(True)).limit(1000))
    matches = []
    for worker in workers:
        candidate_distances: list[float] = []
        same_village = False
        if jobs:
            for job in jobs:
                job_same_village = _normalized_location(job.village) == _normalized_location(worker.village)
                if job.latitude is not None and job.longitude is not None and worker.latitude is not None and worker.longitude is not None:
                    job_distance = _distance_km(job.latitude, job.longitude, worker.latitude, worker.longitude)
                    if job_distance <= radius_km:
                        candidate_distances.append(job_distance)
                        same_village = same_village or job_same_village
                elif job_same_village:
                    same_village = True
        elif farmer.latitude is not None and farmer.longitude is not None and worker.latitude is not None and worker.longitude is not None:
            farmer_distance = _distance_km(farmer.latitude, farmer.longitude, worker.latitude, worker.longitude)
            if farmer_distance <= radius_km:
                candidate_distances.append(farmer_distance)
                same_village = bool(farmer_village and farmer_village == _normalized_location(worker.village))
        elif farmer_village and farmer_village == _normalized_location(worker.village):
            same_village = True

        if not candidate_distances and not same_village:
            continue
        distance = min(candidate_distances) if candidate_distances else None
        skill_match = any(_has_skill_match(worker.skills, f"{job.title} {job.description}") for job in jobs)
        wage_match = (
            not jobs
            or worker.daily_wage is None
            or any(job.daily_wage >= worker.daily_wage for job in jobs)
        )
        matches.append({
            "id": worker.id,
            "name": worker.name,
            "profile_photo_url": _profile_photo_url("worker", worker.id, worker.profile_photo_data),
            "village": worker.village,
            "skills": worker.skills,
            "daily_wage": worker.daily_wage,
            "distance_km": round(distance, 1) if distance is not None else None,
            "same_village": same_village,
            "skill_match": skill_match,
            "wage_match": wage_match,
        })
    return sorted(
        matches,
        key=lambda match: (
            not match["same_village"],
            not match["skill_match"],
            not match["wage_match"],
            match["distance_km"] if match["distance_km"] is not None else float("inf"),
        ),
    )


@router.get("/farmer/bookings/{booking_id}/replacements")
def replacement_workers(
    booking_id: int,
    radius_km: float = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    booking = _booking_for_participant(booking_id, db, farmer.id, "farmer")
    if booking.job.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "ABSENT":
        raise HTTPException(status_code=409, detail="Report an absent confirmed worker before finding a replacement.")
    if booking.work_date < date.today():
        return []

    occupied_on_date = select(JobBooking.id).where(
        JobBooking.worker_id == Worker.id,
        JobBooking.work_date == booking.work_date,
        JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    ).exists()
    already_applied = select(JobApplication.id).where(
        JobApplication.job_id == booking.job_id,
        JobApplication.worker_id == Worker.id,
        JobApplication.status != "CANCELLED",
    ).exists()
    candidates = db.scalars(
        select(Worker)
        .where(Worker.is_available.is_(True), ~occupied_on_date, ~already_applied)
        .limit(1000)
    )
    job = booking.job
    job_village = _normalized_location(job.village)
    matches = []
    for candidate in candidates:
        same_village = bool(job_village and job_village == _normalized_location(candidate.village))
        if job.latitude is not None and job.longitude is not None and candidate.latitude is not None and candidate.longitude is not None:
            distance = _distance_km(job.latitude, job.longitude, candidate.latitude, candidate.longitude)
            if distance > radius_km:
                continue
        elif same_village:
            distance = None
        else:
            continue
        matches.append({
            "id": candidate.id,
            "name": candidate.name,
            "phone": candidate.phone if candidate.allow_phone_contact else None,
            "village": candidate.village,
            "skills": candidate.skills,
            "daily_wage": candidate.daily_wage,
            "distance_km": round(distance, 1) if distance is not None else None,
            "same_village": same_village,
            "skill_match": _has_skill_match(candidate.skills, f"{job.title} {job.description}"),
            "wage_match": candidate.daily_wage is None or job.daily_wage >= candidate.daily_wage,
        })
    return sorted(
        matches,
        key=lambda match: (
            not match["same_village"],
            not match["skill_match"],
            not match["wage_match"],
            match["distance_km"] if match["distance_km"] is not None else float("inf"),
        ),
    )


@router.post("/teams", status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    team = MarketTeam(leader_id=worker.id, name=payload.name.strip())
    team.members.append(MarketTeamMember(worker=worker))
    db.add(team)
    db.commit()
    db.refresh(team)
    return _team_data(team)


@router.get("/teams")
def my_teams(db: Session = Depends(get_db), worker: Worker = Depends(require_worker)):
    teams = db.scalars(
        select(MarketTeam).join(MarketTeamMember).where(MarketTeamMember.worker_id == worker.id)
        .options(joinedload(MarketTeam.members).joinedload(MarketTeamMember.worker)).distinct()
    ).unique()
    return [_team_data(team) for team in teams]


@router.post("/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: int,
    payload: TeamMemberCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    team = db.scalar(
        select(MarketTeam).where(MarketTeam.id == team_id, MarketTeam.leader_id == worker.id)
        .options(joinedload(MarketTeam.members))
    )
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    if len(team.members) >= 25:
        raise HTTPException(status_code=409, detail="A team can have at most 25 workers.")
    member = db.scalar(select(Worker).where(func.lower(Worker.username) == payload.username))
    if member is None:
        raise HTTPException(status_code=404, detail="No worker account is registered with that username.")
    if not member.is_available:
        raise HTTPException(status_code=409, detail="That worker is currently unavailable.")
    if member.id == team.leader_id or any(item.worker_id == member.id for item in team.members):
        raise HTTPException(status_code=409, detail="That worker is already part of this team.")
    active_booking = db.scalar(
        select(JobBooking.id).where(
            JobBooking.worker_id == member.id,
            JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
            JobBooking.work_date >= date.today(),
        ).limit(1)
    )
    if active_booking is not None:
        raise HTTPException(status_code=409, detail="That worker has an active booking.")
    team.members.append(MarketTeamMember(worker=member))
    db.commit()
    db.refresh(team)
    return _team_data(team)


@router.delete("/teams/{team_id}/members/{worker_id}")
def remove_team_member(
    team_id: int,
    worker_id: int,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    team = db.scalar(select(MarketTeam).where(MarketTeam.id == team_id, MarketTeam.leader_id == worker.id))
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    membership = db.scalar(select(MarketTeamMember).where(
        MarketTeamMember.team_id == team_id, MarketTeamMember.worker_id == worker_id,
    ))
    if membership is None or worker_id == team.leader_id:
        raise HTTPException(status_code=404, detail="Team member not found.")
    reserved = db.scalar(
        select(JobBooking.id).join(JobApplication).where(
            JobApplication.team_id == team_id,
            JobBooking.worker_id == worker_id,
            JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
        ).limit(1)
    )
    if reserved is not None:
        raise HTTPException(status_code=409, detail="A worker with an active team booking cannot be removed.")
    db.delete(membership)
    db.commit()
    return {"removed": True}


@router.post("/jobs/{job_id}/applications", status_code=status.HTTP_201_CREATED)
def apply_to_job(
    job_id: int,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    job = _job_or_404(db, job_id)
    if job.status != "OPEN" or job.work_date < date.today():
        raise HTTPException(status_code=409, detail="This job is no longer accepting applications.")
    team = None
    applicants = [worker]
    if payload.team_id is not None:
        team = db.scalar(
            select(MarketTeam).where(MarketTeam.id == payload.team_id, MarketTeam.leader_id == worker.id)
            .options(joinedload(MarketTeam.members).joinedload(MarketTeamMember.worker))
        )
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found.")
        applicants = [member.worker for member in team.members]
    if not applicants or len(applicants) > job.required_workers:
        raise HTTPException(status_code=409, detail="The team is larger than the number of open positions.")
    if any(not applicant.is_available for applicant in applicants):
        raise HTTPException(status_code=409, detail="Every worker applying as a team must be available.")
    for applicant in applicants:
        booked = db.scalar(select(JobBooking.id).where(
            JobBooking.worker_id == applicant.id,
            JobBooking.work_date == job.work_date,
            JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
        ).limit(1))
        if booked is not None:
            raise HTTPException(status_code=409, detail="A worker in this application is already booked for that date.")
    existing = db.scalar(select(JobApplication.id).where(
        JobApplication.job_id == job.id, JobApplication.worker_id == worker.id,
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already applied to this job.")
    application = JobApplication(
        job_id=job.id, worker_id=worker.id, team_id=team.id if team else None,
        proposed_wage=payload.proposed_wage,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return _application_data(_application_or_404(db, application.id))


@router.post("/jobs/{job_id}/workers/{worker_id}/book", status_code=status.HTTP_201_CREATED)
def book_worker(
    job_id: int,
    worker_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    job = _job_or_404(db, job_id)
    if job.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "OPEN" or job.work_date < date.today():
        raise HTTPException(status_code=409, detail="This job is no longer accepting bookings.")

    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found.")
    if not worker.is_available:
        raise HTTPException(status_code=409, detail="That worker is currently unavailable.")

    active_count = db.scalar(select(func.count(JobBooking.id)).where(
        JobBooking.job_id == job.id,
        JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    )) or 0
    if active_count >= job.required_workers:
        raise HTTPException(status_code=409, detail="There are no remaining positions for this job.")

    existing_application = db.scalar(select(JobApplication.id).where(
        JobApplication.job_id == job.id,
        JobApplication.worker_id == worker.id,
    ))
    if existing_application is not None:
        raise HTTPException(status_code=409, detail="This worker already has an application for the job.")

    active_booking = db.scalar(select(JobBooking.id).where(
        JobBooking.worker_id == worker.id,
        JobBooking.work_date == job.work_date,
        JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    ).limit(1))
    if active_booking is not None:
        raise HTTPException(status_code=409, detail="That worker already has a booking for this date.")

    application = JobApplication(
        job=job,
        worker=worker,
        proposed_wage=job.daily_wage,
        status="ACCEPTED",
    )
    booking = JobBooking(
        application=application,
        job=job,
        worker=worker,
        work_date=job.work_date,
        agreed_wage=job.daily_wage,
        status="PENDING",
    )
    db.add_all([application, booking])
    if active_count + 1 >= job.required_workers:
        job.status = "FILLED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That worker could not be booked for this job. Refresh and retry.") from None
    db.refresh(booking)
    return _booking_data(booking, False)


@router.get("/jobs/{job_id}/applications")
def job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    job = _job_or_404(db, job_id)
    if job.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Job not found.")
    applications = db.scalars(
        select(JobApplication).where(JobApplication.job_id == job_id)
        .options(joinedload(JobApplication.worker), joinedload(JobApplication.team).joinedload(MarketTeam.members))
        .order_by(JobApplication.created_at)
    ).unique()
    return [_application_data(application) for application in applications]


@router.get("/worker/applications")
def worker_applications(db: Session = Depends(get_db), worker: Worker = Depends(require_worker)):
    applications = db.scalars(
        select(JobApplication).where(JobApplication.worker_id == worker.id)
        .options(joinedload(JobApplication.worker), joinedload(JobApplication.team).joinedload(MarketTeam.members))
        .order_by(JobApplication.created_at.desc())
    ).unique()
    return [_application_data(application) for application in applications]


def _offer(application_id: int, wage: int, db: Session, owner_id: int, owner_type: str):
    application = _application_or_404(db, application_id)
    if application.status != "NEGOTIATING":
        raise HTTPException(status_code=409, detail="This application is no longer open for wage negotiation.")
    if owner_type == "worker":
        if application.worker_id != owner_id:
            raise HTTPException(status_code=404, detail="Application not found.")
    elif application.job.farmer_id != owner_id:
        raise HTTPException(status_code=404, detail="Application not found.")
    application.proposed_wage = wage
    db.commit()
    db.refresh(application)
    return _application_data(application)


@router.patch("/worker/applications/{application_id}/offer")
def worker_offer(
    application_id: int,
    payload: WageOffer,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    return _offer(application_id, payload.proposed_wage, db, worker.id, "worker")


@router.patch("/farmer/applications/{application_id}/offer")
def farmer_offer(
    application_id: int,
    payload: WageOffer,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    return _offer(application_id, payload.proposed_wage, db, farmer.id, "farmer")


@router.post("/farmer/applications/{application_id}/accept")
def accept_application(
    application_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    application = db.scalar(
        select(JobApplication).where(JobApplication.id == application_id).with_for_update()
        .options(joinedload(JobApplication.worker), joinedload(JobApplication.team).joinedload(MarketTeam.members))
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    job = db.scalar(select(MarketJob).where(MarketJob.id == application.job_id).with_for_update())
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Application not found.")
    if application.status != "NEGOTIATING":
        raise HTTPException(status_code=409, detail="This application cannot be accepted.")
    members = application.team.members if application.team else []
    workers = [member.worker for member in members] if members else [application.worker]
    if len(workers) > job.required_workers:
        raise HTTPException(status_code=409, detail="The team is larger than the number of open positions.")
    reserved_count = db.scalar(select(func.count(JobBooking.id)).where(
        JobBooking.job_id == job.id, JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    )) or 0
    if reserved_count + len(workers) > job.required_workers:
        raise HTTPException(status_code=409, detail="There are not enough remaining positions for this group.")
    for member in workers:
        if not member.is_available:
            raise HTTPException(status_code=409, detail="A worker in this application is unavailable.")
        conflict = db.scalar(select(JobBooking.id).where(
            JobBooking.worker_id == member.id,
            JobBooking.work_date == job.work_date,
            JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
        ).limit(1))
        if conflict is not None:
            raise HTTPException(status_code=409, detail="A worker in this application is already booked for that date.")
    application.status = "ACCEPTED"
    for member in workers:
        db.add(JobBooking(
            application=application, job=job, worker=member,
            work_date=job.work_date, agreed_wage=application.proposed_wage, status="PENDING",
        ))
    if reserved_count + len(workers) >= job.required_workers:
        job.status = "FILLED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A worker was booked for another job at the same time. Refresh and retry.") from None
    bookings = db.scalars(select(JobBooking).where(JobBooking.application_id == application.id)).all()
    return [_booking_data(booking, False) for booking in bookings]


@router.get("/worker/bookings")
def worker_bookings(db: Session = Depends(get_db), worker: Worker = Depends(require_worker)):
    bookings = db.scalars(
        select(JobBooking).where(JobBooking.worker_id == worker.id)
        .options(joinedload(JobBooking.job).joinedload(MarketJob.farmer), joinedload(JobBooking.worker))
        .order_by(JobBooking.work_date)
    ).unique()
    return [_booking_data(item, item.status == "CONFIRMED") for item in bookings]


@router.get("/farmer/bookings")
def farmer_bookings(db: Session = Depends(get_db), farmer: Farmer = Depends(require_farmer)):
    bookings = db.scalars(
        select(JobBooking).join(MarketJob).where(MarketJob.farmer_id == farmer.id)
        .options(joinedload(JobBooking.job).joinedload(MarketJob.farmer), joinedload(JobBooking.worker))
        .order_by(JobBooking.work_date)
    ).unique()
    return [_booking_data(item, item.status == "CONFIRMED") for item in bookings]


@router.post("/farmer/bookings/{booking_id}/report-absence")
def report_worker_absence(
    booking_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    booking = db.scalar(
        select(JobBooking)
        .where(JobBooking.id == booking_id)
        .options(joinedload(JobBooking.job), joinedload(JobBooking.worker))
    )
    if booking is None or booking.job.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=409, detail="Only confirmed workers can be reported absent.")
    booking.status = "ABSENT"
    booking.application.status = "CANCELLED"
    active_count = db.scalar(select(func.count(JobBooking.id)).where(
        JobBooking.job_id == booking.job_id,
        JobBooking.id != booking.id,
        JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    )) or 0
    if active_count < booking.job.required_workers and booking.job.work_date >= date.today():
        booking.job.status = "OPEN"
    db.commit()
    return _booking_data(booking, False)


@router.get("/worker/bookings/{booking_id}/messages")
def worker_booking_messages(
    booking_id: int,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    return _booking_messages(booking_id, db, worker.id, "worker")


@router.post("/worker/bookings/{booking_id}/messages", status_code=status.HTTP_201_CREATED)
def worker_send_booking_message(
    booking_id: int,
    payload: BookingMessageCreate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    return _send_booking_message(booking_id, payload, db, worker.id, "worker", worker)


@router.get("/farmer/bookings/{booking_id}/messages")
def farmer_booking_messages(
    booking_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    return _booking_messages(booking_id, db, farmer.id, "farmer")


@router.post("/farmer/bookings/{booking_id}/messages", status_code=status.HTTP_201_CREATED)
def farmer_send_booking_message(
    booking_id: int,
    payload: BookingMessageCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    return _send_booking_message(booking_id, payload, db, farmer.id, "farmer", farmer)


@router.post("/worker/bookings/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    booking = db.scalar(
        select(JobBooking).where(JobBooking.id == booking_id, JobBooking.worker_id == worker.id)
        .options(joinedload(JobBooking.job).joinedload(MarketJob.farmer), joinedload(JobBooking.worker))
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending bookings can be confirmed.")
    booking.status = "CONFIRMED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already have another booking for this date.") from None
    db.refresh(booking)
    return _booking_data(booking, True)


def _cancel_booking(booking_id: int, db: Session, principal_id: int, principal_type: str):
    booking = db.scalar(
        select(JobBooking).where(JobBooking.id == booking_id)
        .options(joinedload(JobBooking.job), joinedload(JobBooking.worker))
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    authorized = booking.worker_id == principal_id if principal_type == "worker" else booking.job.farmer_id == principal_id
    if not authorized:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise HTTPException(status_code=409, detail="This booking is already closed.")
    booking.status = "CANCELLED"
    active_count = db.scalar(select(func.count(JobBooking.id)).where(
        JobBooking.job_id == booking.job_id, JobBooking.status.in_(ACTIVE_BOOKING_STATUSES),
    )) or 0
    if active_count < booking.job.required_workers:
        booking.job.status = "OPEN"
    db.commit()
    return {"cancelled": True}


@router.post("/worker/bookings/{booking_id}/cancel")
def worker_cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    return _cancel_booking(booking_id, db, worker.id, "worker")


@router.post("/farmer/bookings/{booking_id}/cancel")
def farmer_cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    return _cancel_booking(booking_id, db, farmer.id, "farmer")
