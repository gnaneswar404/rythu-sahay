from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Expert, Farmer, Worker
from app.services.seed import pwd_context

security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(principal: Expert | Farmer | Worker, principal_type: str | None = None) -> str:
    settings = get_settings()
    if principal_type is None:
        principal_type = "expert" if isinstance(principal, Expert) else "farmer" if isinstance(principal, Farmer) else "worker"
    payload = {
        "sub": str(principal.id),
        "principal_type": principal_type,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def require_expert(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Expert:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expert authentication is required.")
    try:
        data = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=[ALGORITHM])
        if data.get("principal_type") != "expert":
            raise ValueError("Token is not for an expert.")
        expert = db.get(Expert, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        expert = None
    if expert is None or not expert.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired expert session.")
    return expert


def _authenticated_principal(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
    expected_type: str,
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Marketplace account authentication is required.")
    try:
        data = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=[ALGORITHM])
        if data.get("principal_type") != expected_type:
            raise ValueError("Token has the wrong account type.")
        principal_id = int(data["sub"])
        model = Farmer if expected_type == "farmer" else Worker
        principal = db.get(model, principal_id)
    except (jwt.PyJWTError, KeyError, ValueError):
        principal = None
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired marketplace session.")
    return principal


def require_farmer(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Farmer:
    return _authenticated_principal(credentials, db, "farmer")


def require_worker(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Worker:
    return _authenticated_principal(credentials, db, "worker")


def optional_farmer(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Farmer | None:
    if credentials is None:
        return None
    return _authenticated_principal(credentials, db, "farmer")
