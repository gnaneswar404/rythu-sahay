import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///./test_rythu_sahaya.db"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.api.auth as auth_api  # noqa: E402
from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Expert  # noqa: E402
from app.services.seed import seed_demo_data  # noqa: E402


def test_seed_migrates_legacy_demo_email():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        db.add(Expert(
            name="Demo Expert",
            email="demo.expert@rythusahay.local",
            password_hash="unchanged",
            is_demo=True,
        ))
        db.commit()

        seed_demo_data(db)

        expert = db.scalar(select(Expert))
        assert expert.email == "demo.expert@example.com"
        assert expert.password_hash == "unchanged"
    engine.dispose()


def test_health_and_scope_protection():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        blocked = client.post("/api/v1/farmers", json={"name": "Test", "district": "Warangal"})
        assert blocked.status_code == 422


def test_telugu_conversation_creates_a_case_and_expert_can_review():
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

        login = client.post("/api/v1/auth/login", json={"email": "DEMO.EXPERT@EXAMPLE.COM", "password": "demo-expert"})
        assert login.status_code == 200
        legacy_login = client.post(
            "/api/v1/auth/login",
            json={"email": "demo.expert@rythusahay.local", "password": "demo-expert"},
        )
        assert legacy_login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        detail = client.get(f"/api/v1/cases/{case_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["crop"] == "cotton"
        status_update = client.patch(f"/api/v1/cases/{case_id}/status", headers=headers, json={"status": "UNDER_REVIEW"})
        assert status_update.status_code == 200


def test_google_login_verifies_identity_and_creates_expert(monkeypatch):
    claims = {
        "email": "new.expert@gmail.com",
        "email_verified": True,
        "sub": "google-user-123",
        "name": "New Expert",
    }
    monkeypatch.setattr(auth_api, "get_settings", lambda: SimpleNamespace(google_client_id="test-client"))
    monkeypatch.setattr(auth_api.id_token, "verify_oauth2_token", lambda token, request, audience: claims)

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/google", json={"credential": "verified-test-token"})

        assert response.status_code == 200
        assert response.json()["expert_name"] == "New Expert"
        second_response = client.post("/api/v1/auth/google", json={"credential": "verified-test-token"})
        assert second_response.status_code == 200
        assert second_response.json()["expert_id"] == response.json()["expert_id"]
        expert = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
        )
        assert expert.status_code == 200
        assert expert.json()["is_demo"] is False
        assert expert.json()["email"] == "new.expert@gmail.com"
        assert expert.json()["created_at"]


def test_google_config_returns_the_public_client_id(monkeypatch):
    monkeypatch.setattr(auth_api, "get_settings", lambda: SimpleNamespace(google_client_id="test-client"))

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/google/config")

    assert response.status_code == 200
    assert response.json() == {"client_id": "test-client"}


def test_signed_in_expert_can_complete_their_own_profile():
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "demo.expert@example.com", "password": "demo-expert"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        update = client.patch(
            "/api/v1/auth/me",
            headers=headers,
            json={"name": "Demo Profile Expert", "phone_number": "+91 98765 43210"},
        )

        assert update.status_code == 200
        assert update.json()["name"] == "Demo Profile Expert"
        assert update.json()["phone_number"] == "+91 98765 43210"
        profile = client.get("/api/v1/auth/me", headers=headers)
        assert profile.json()["email"] == "demo.expert@example.com"
        assert profile.json()["phone_number"] == "+91 98765 43210"


def test_google_login_rejects_unverified_email(monkeypatch):
    claims = {
        "email": "unverified@gmail.com",
        "email_verified": False,
        "sub": "google-user-456",
        "name": "Unverified",
    }
    monkeypatch.setattr(auth_api, "get_settings", lambda: SimpleNamespace(google_client_id="test-client"))
    monkeypatch.setattr(auth_api.id_token, "verify_oauth2_token", lambda token, request, audience: claims)

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/google", json={"credential": "unverified-test-token"})
        assert response.status_code == 401


def test_google_login_requires_client_id(monkeypatch):
    monkeypatch.setattr(auth_api, "get_settings", lambda: SimpleNamespace(google_client_id=None))

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/google", json={"credential": "test-token"})
        assert response.status_code == 503
