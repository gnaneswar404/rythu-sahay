from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, CaseAction, CaseStatus, Farmer, Severity


def seed_demo_data(db: Session) -> None:
    """Create one synthetic farmer and case when no demo case exists."""
    if db.scalar(select(Case.id).where(Case.is_demo.is_(True)).limit(1)):
        return
    farmer = Farmer(
        name="కె. మల్లేష్ (డెమో)",
        mobile="9XXXXXXXXX",
        village="నకిరేకల్ (డెమో)",
        mandal="నకిరేకల్",
        district="Nalgonda",
        consent_recording=True,
        is_demo=True,
    )
    db.add(farmer)
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
        status=CaseStatus.NEW,
        ai_summary="డెమో రికార్డు మాత్రమే. పసుపుదనానికి కారణం నిర్ధారించబడలేదు.",
        is_demo=True,
    )
    db.add(case)
    db.flush()
    db.add(CaseAction(case_id=case.id, action_type="CASE_CREATED", description="Synthetic demo case created.", source="Demo seed"))
    db.commit()
