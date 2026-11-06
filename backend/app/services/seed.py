from datetime import date, timedelta

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, CaseAction, CaseStatus, Expert, Farmer, Followup, Severity

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEMO_EMAIL = "demo.expert@example.com"
LEGACY_DEMO_EMAIL = "demo.expert@rythusahay.local"


def seed_demo_data(db: Session) -> None:
    """Creates synthetic records on an empty database and updates the legacy demo email."""
    legacy_demo_expert = db.scalar(
        select(Expert).where(
            Expert.email == LEGACY_DEMO_EMAIL,
            Expert.is_demo.is_(True),
        )
    )
    if legacy_demo_expert is not None:
        legacy_demo_expert.email = DEMO_EMAIL
        db.commit()

    if db.scalar(select(Expert.id).limit(1)):
        return
    expert = Expert(
        name="డా. అనిత కుమారి (డెమో)",
        role="Cotton Agricultural Expert",
        contact="Demo account only",
        email=DEMO_EMAIL,
        password_hash=pwd_context.hash("demo-expert"),
        is_demo=True,
    )
    farmer = Farmer(
        name="కె. మల్లేష్ (డెమో)",
        mobile="9XXXXXXXXX",
        village="నకిరేకల్ (డెమో)",
        mandal="నకిరేకల్",
        district="Nalgonda",
        consent_recording=True,
        is_demo=True,
    )
    db.add_all([expert, farmer])
    db.flush()
    case = Case(
        id=f"RS-{date.today().year}-0001",
        farmer_id=farmer.id,
        crop="cotton",
        village=farmer.village,
        mandal=farmer.mandal,
        district="Nalgonda",
        problem_category="ఆకులు పసుపు రంగులోకి మారడం",
        description="పత్తి ఆకులు మూడు రోజులుగా పసుపు రంగులోకి మారుతున్నాయని రైతు తెలిపారు. (డెమో డేటా)",
        symptoms="ఆకుల పసుపుదనం; కారణం నిర్ధారించలేదు.",
        severity=Severity.MEDIUM,
        status=CaseStatus.ESCALATED,
        ai_summary="డెమో రికార్డు మాత్రమే. పసుపుదనానికి కారణం నిర్ధారించడానికి నిపుణుడి సమీక్ష అవసరం.",
        is_demo=True,
        expert_id=expert.id,
    )
    db.add(case)
    db.flush()
    db.add_all([
        CaseAction(case_id=case.id, action_type="CASE_CREATED", description="Synthetic demo case created.", source="Demo seed"),
        CaseAction(case_id=case.id, action_type="EXPERT_ASSIGNED", description="Assigned to demo expert.", source="Demo seed", expert_approved=True),
        Followup(case_id=case.id, scheduled_date=date.today() + timedelta(days=3)),
    ])
    db.commit()
