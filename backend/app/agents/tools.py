"""The only mutation/retrieval surface intended for an LLM-backed agent.

An agent receives this facade, never an SQLAlchemy session or model. Every call
therefore uses the same validation and transaction path as the REST API.
"""
from sqlalchemy.orm import Session

from app.knowledge.repository import get_verified_guidance
from app.models import Farmer
from app.schemas.cases import AssignmentCreate, CaseCreate, FeedbackCreate, FollowupCreate, StatusUpdate
from app.schemas.farmers import FarmerCreate
from app.services.cases import assign_case, create_case, record_feedback, schedule_followup, update_status


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

    def assign_expert(self, case_id: str, expert_id: int):
        return assign_case(self._db, case_id, AssignmentCreate(expert_id=expert_id))

    def update_case_status(self, case_id: str, payload: StatusUpdate):
        return update_status(self._db, case_id, payload)

    def schedule_followup(self, case_id: str, payload: FollowupCreate):
        return schedule_followup(self._db, case_id, payload)

    def record_farmer_feedback(self, case_id: str, payload: FeedbackCreate):
        return record_feedback(self._db, case_id, payload)
