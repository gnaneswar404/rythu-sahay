from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expert, Farmer
from app.schemas.farmers import FarmerCreate, FarmerRead
from app.services.auth import require_expert

router = APIRouter(prefix="/farmers", tags=["farmers"])


@router.post("", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
def create_farmer(payload: FarmerCreate, db: Session = Depends(get_db)):
    farmer = Farmer(**payload.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/{farmer_id}", response_model=FarmerRead)
def get_farmer(farmer_id: int, db: Session = Depends(get_db), _: Expert = Depends(require_expert)):
    farmer = db.get(Farmer, farmer_id)
    if farmer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found.")
    return farmer
