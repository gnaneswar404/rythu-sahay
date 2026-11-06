import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Case, Farmer, JobApplication, JobBooking, MarketJob, MarketTeam, MarketTeamMember, Worker,
)
from app.schemas.cases import CaseRead
from app.schemas.marketplace import (
    ApplicationCreate, FarmerProfileUpdate, MarketJobCreate, TeamCreate, TeamMemberCreate,
    WageOffer, WorkerProfileUpdate,
)
from app.services.auth import require_farmer, require_worker

router = APIRouter(prefix="/market", tags=["worker marketplace"])
ACTIVE_BOOKING_STATUSES = ("PENDING", "CONFIRMED")


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lon / 2) ** 2
    value = min(1.0, max(0.0, value))
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _job_data(job: MarketJob, distance: float | None = None) -> dict:
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
    }


def _team_data(team: MarketTeam) -> dict:
    return {
        "id": team.id,
        "name": team.name,
        "leader_id": team.leader_id,
        "members": [{"id": item.worker.id, "name": item.worker.name} for item in team.members],
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
        "proposed_wage": application.proposed_wage,
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
        "worker_phone": booking.worker.phone if include_contact else None,
        "farmer_name": job.farmer.name if include_contact else None,
        "farmer_phone": job.farmer.mobile if include_contact else None,
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
    }


@router.patch("/farmer/profile")
def update_farmer_profile(
    payload: FarmerProfileUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    for key, value in payload.model_dump().items():
        setattr(farmer, key, value)
    db.commit()
    db.refresh(farmer)
    return {"id": farmer.id, "name": farmer.name, "village": farmer.village, "mandal": farmer.mandal}


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
    }


@router.patch("/worker/profile")
def update_worker_profile(
    payload: WorkerProfileUpdate,
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    for key, value in payload.model_dump().items():
        setattr(worker, key, value)
    db.commit()
    db.refresh(worker)
    return worker_profile(worker)


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
    return _job_data(job)


@router.get("/jobs/mine")
def my_jobs(db: Session = Depends(get_db), farmer: Farmer = Depends(require_farmer)):
    jobs = db.scalars(select(MarketJob).where(MarketJob.farmer_id == farmer.id).order_by(MarketJob.work_date.desc()))
    return [_job_data(job) for job in jobs]


@router.get("/jobs/nearby")
def nearby_jobs(
    radius_km: float = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    worker: Worker = Depends(require_worker),
):
    if worker.latitude is None or worker.longitude is None:
        raise HTTPException(status_code=400, detail="Add your location to your worker profile to find nearby jobs.")
    jobs = db.scalars(
        select(MarketJob).where(MarketJob.status == "OPEN", MarketJob.work_date >= date.today())
        .order_by(MarketJob.work_date).limit(500)
    )
    matches = []
    for job in jobs:
        if job.latitude is None or job.longitude is None:
            continue
        distance = _distance_km(worker.latitude, worker.longitude, job.latitude, job.longitude)
        if distance <= radius_km:
            matches.append(_job_data(job, distance))
    return sorted(matches, key=lambda match: (match["distance_km"], match["work_date"]))


@router.get("/workers/nearby")
def nearby_workers(
    radius_km: float = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(require_farmer),
):
    if farmer.latitude is None or farmer.longitude is None:
        raise HTTPException(status_code=400, detail="Add your location to your farmer profile to find nearby workers.")
    workers = db.scalars(select(Worker).where(Worker.is_available.is_(True)).limit(1000))
    matches = []
    for worker in workers:
        if worker.latitude is None or worker.longitude is None:
            continue
        distance = _distance_km(farmer.latitude, farmer.longitude, worker.latitude, worker.longitude)
        if distance <= radius_km:
            matches.append({
                "id": worker.id,
                "name": worker.name,
                "village": worker.village,
                "skills": worker.skills,
                "daily_wage": worker.daily_wage,
                "distance_km": round(distance, 1),
            })
    return sorted(matches, key=lambda match: match["distance_km"])


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
    member = db.scalar(select(Worker).where(Worker.phone == payload.phone))
    if member is None:
        raise HTTPException(status_code=404, detail="No worker account is registered with that phone number.")
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
