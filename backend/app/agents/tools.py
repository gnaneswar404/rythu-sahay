"""The only mutation/retrieval surface intended for an LLM-backed agent.

An agent receives this facade, never an SQLAlchemy session or model. Every call
therefore uses the same validation and transaction path as the REST API.
"""
from sqlalchemy.orm import Session

from app.knowledge.repository import get_verified_guidance
from app.models import Farmer
from app.schemas.cases import CaseCreate, FeedbackCreate
from app.schemas.farmers import FarmerCreate
from app.services.cases import create_case, record_feedback


class AgriculturalAgentTools:
    def __init__(self, db: Session):
        self._db = db

    def create_farmer(self, payload: FarmerCreate) -> Farmer:
        farmer = Farmer(**payload.model_dump())
        self._db.add(farmer)
        self._db.commit()
        self._db.refresh(farmer)
        return farmer

    def create_case(self, payload: CaseCreate):
        return create_case(self._db, payload)

    def get_verified_guidance(self, query: str) -> dict | None:
        return get_verified_guidance(query)

    def record_farmer_feedback(self, case_id: str, payload: FeedbackCreate):
        return record_feedback(self._db, case_id, payload)
