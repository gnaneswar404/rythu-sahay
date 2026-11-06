import os

os.environ["DATABASE_URL"] = "sqlite:///./test_rythu_sahaya.db"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Case  # noqa: E402
from app.services.seed import seed_demo_data  # noqa: E402


def test_demo_seed_creates_farmer_case_without_expert_model():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_demo_data(db)
        case = db.scalar(select(Case).where(Case.is_demo.is_(True)))
        assert case is not None
        assert case.farmer.is_demo is True
        assert "experts" not in Base.metadata.tables
        assert "expert_id" not in Case.__table__.columns
    engine.dispose()


def test_health_and_scope_protection():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        blocked = client.post("/api/v1/farmers", json={"name": "Test", "district": "Warangal"})
        assert blocked.status_code == 422


def test_expert_authentication_and_dashboard_routes_are_removed():
    removed_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/google",
        "/api/v1/auth/google/config",
        "/api/v1/auth/me",
        "/api/v1/dashboard/summary",
        "/api/v1/cases/{case_id}",
        "/api/v1/cases/{case_id}/status",
        "/api/v1/cases/{case_id}/assign",
        "/api/v1/cases/{case_id}/notes",
        "/api/v1/cases/{case_id}/followups",
        "/api/v1/cases/{case_id}/photos",
        "/api/v1/farmers/{farmer_id}",
    }
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert removed_paths.isdisjoint(paths)
        assert "get" not in paths["/api/v1/cases"]


def test_telugu_conversation_creates_case_and_farmer_can_send_feedback():
    with TestClient(app) as client:
        start = client.post("/api/v1/calls/start", json={"consent_recording": True})
        assert start.status_code == 200
        session_id = start.json()["session_id"]
        messages = [
            "నా పత్తి పంట ఆకులు పసుపు రంగులోకి మారుతున్నాయి.",
            "మూడు రోజుల నుంచి.",
            "కొన్ని మచ్చలు ఉన్నాయి.",
            "నకిరేకల్",
            "నకిరేకల్ మండలం",
        ]
        reply = None
        for message in messages:
            reply = client.post("/api/v1/calls/message", json={"session_id": session_id, "message": message})
            assert reply.status_code == 200
        case_id = reply.json()["case_id"]
        assert case_id.startswith("RS-")
        assert client.get(f"/api/v1/cases/{case_id}").status_code == 404

        feedback = client.post(
            f"/api/v1/cases/{case_id}/feedback",
            headers={"X-Case-Access-Token": reply.json()["case_access_token"]},
            json={"outcome": "WORSENED"},
        )
        assert feedback.status_code == 200
