from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farmer
from app.schemas.farmers import FarmerCreate, FarmerRead

router = APIRouter(prefix="/farmers", tags=["farmers"])


@router.post("", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
def create_farmer(payload: FarmerCreate, db: Session = Depends(get_db)):
    farmer = Farmer(**payload.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer
