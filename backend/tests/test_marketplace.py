from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

import app.api.cases as cases_api
from app.database.session import SessionLocal
from app.models import JobApplication, JobBooking, MarketJob
from app.main import app


def phone():
    return f"+919{uuid4().int % 1000000000:09d}"


def sign_in(client, account_type, mobile):
    username = f"u{''.join(character for character in mobile if character.isdigit())[-10:]}"
    password = "test-password-123"
    payload = {"account_type": account_type, "username": username, "password": password, "phone": mobile}
    registered = client.post("/api/v1/auth/market/register", json=payload)
    assert registered.status_code == 201, registered.text
    response = client.post("/api/v1/auth/market/login", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data


def test_farmer_and_worker_accounts_register_and_log_in_with_username_password():
    with TestClient(app) as client:
        username = f"farm.user{uuid4().hex[:8]}"
        farmer_payload = {"account_type": "farmer", "username": username, "password": "farmer-pass-123"}
        worker_payload = {"account_type": "worker", "username": username, "password": "worker-pass-123"}
        for payload in (farmer_payload, worker_payload):
            registered = client.post("/api/v1/auth/market/register", json=payload)
            assert registered.status_code == 201, registered.text

        farmer_login = client.post(
            "/api/v1/auth/market/login",
            json={**farmer_payload, "username": username.upper()},
        )
        worker_login = client.post("/api/v1/auth/market/login", json=worker_payload)
        assert farmer_login.status_code == 200
        assert worker_login.status_code == 200
        assert farmer_login.json()["account_type"] == "farmer"
        assert worker_login.json()["account_type"] == "worker"

        farmer_headers = {"Authorization": f"Bearer {farmer_login.json()['access_token']}"}
        worker_headers = {"Authorization": f"Bearer {worker_login.json()['access_token']}"}
        assert client.get("/api/v1/market/farmer/profile", headers=farmer_headers).status_code == 200
        assert client.get("/api/v1/market/worker/profile", headers=farmer_headers).status_code == 401
        assert client.get("/api/v1/market/worker/profile", headers=worker_headers).status_code == 200
        assert client.get("/api/v1/market/farmer/profile", headers=worker_headers).status_code == 401
        invalid = client.post(
            "/api/v1/auth/market/login",
            json={**farmer_payload, "password": "wrong-password"},
        )
        assert invalid.status_code == 401
        duplicate = client.post("/api/v1/auth/market/register", json=farmer_payload)
        assert duplicate.status_code == 409


def test_farmer_can_book_nearby_worker_and_worker_confirms_booking():
    farmer_phone = phone()
    worker_phone = phone()
    with TestClient(app) as client:
        farmer_headers, farmer = sign_in(client, "farmer", farmer_phone)
        worker_headers, worker = sign_in(client, "worker", worker_phone)
        job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Cotton picking",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "work_date": (date.today() + timedelta(days=1)).isoformat(),
                "daily_wage": 650,
                "required_workers": 1,
            },
        )
        assert job.status_code == 201, job.text

        booked = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{worker['id']}/book",
            headers=farmer_headers,
        )
        assert booked.status_code == 201, booked.text
        assert booked.json()["status"] == "PENDING"
        assert booked.json()["agreed_wage"] == 650
        assert booked.json()["worker_phone"] is None

        farmer_bookings = client.get("/api/v1/market/farmer/bookings", headers=farmer_headers)
        assert farmer_bookings.json()[0]["status"] == "PENDING"
        assert farmer_bookings.json()[0]["worker_phone"] is None
        worker_bookings = client.get("/api/v1/market/worker/bookings", headers=worker_headers)
        pending = worker_bookings.json()[0]
        confirmed = client.post(
            f"/api/v1/market/worker/bookings/{pending['id']}/confirm",
            headers=worker_headers,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "CONFIRMED"
        assert confirmed.json()["farmer_phone"] == farmer_phone

        duplicate = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{worker['id']}/book",
            headers=farmer_headers,
        )
        assert duplicate.status_code == 409


def test_farmer_cases_and_complete_group_recruitment_workflow(monkeypatch, tmp_path):
    farmer_phone = phone()
    worker_phone = phone()
    member_phone = phone()
    with TestClient(app) as client:
        monkeypatch.setattr(cases_api, "get_settings", lambda: SimpleNamespace(upload_dir=str(tmp_path)))
        farmer_headers, farmer = sign_in(client, "farmer", farmer_phone)
        worker_headers, worker = sign_in(client, "worker", worker_phone)
        member_headers, _ = sign_in(client, "worker", member_phone)

        profile = client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": "Farmer One", "village": "Nalgonda", "mandal": "Nalgonda", "latitude": 17.0575, "longitude": 79.2684},
        )
        assert profile.status_code == 200, profile.text
        for headers, name, latitude, longitude in (
            (worker_headers, "Worker One", 17.06, 79.27),
            (member_headers, "Worker Two", 17.061, 79.271),
        ):
            updated = client.patch(
                "/api/v1/market/worker/profile",
                headers=headers,
                json={
                    "name": name, "village": "Nalgonda", "mandal": "Nalgonda",
                    "latitude": latitude, "longitude": longitude, "skills": "cotton picking",
                    "daily_wage": 600, "is_available": True,
                },
            )
            assert updated.status_code == 200, updated.text

        start = client.post("/api/v1/calls/start", headers=farmer_headers, json={"consent_recording": True})
        assert start.status_code == 200
        session_id = start.json()["session_id"]
        for message in (
            "నా పత్తి పంట ఆకులు పసుపు రంగులోకి మారుతున్నాయి.",
            "మూడు రోజుల నుంచి.",
            "కొన్ని మచ్చలు ఉన్నాయి.",
            "నకిరేకల్",
            "నకిరేకల్ మండలం",
        ):
            result = client.post(
                "/api/v1/calls/message", headers=farmer_headers,
                json={"session_id": session_id, "message": message},
            )
            assert result.status_code == 200, result.text
        case_access_token = result.json()["case_access_token"]
        assert client.post(
            f"/api/v1/cases/{result.json()['case_id']}/feedback",
            json={"outcome": "IMPROVED"},
        ).status_code == 403
        feedback = client.post(
            f"/api/v1/cases/{result.json()['case_id']}/feedback",
            headers={"X-Case-Access-Token": case_access_token},
            json={"outcome": "IMPROVED"},
        )
        assert feedback.status_code == 200, feedback.text
        case_id = result.json()["case_id"]
        upload_without_token = client.post(
            f"/api/v1/cases/{case_id}/photos",
            files={"photo": ("leaf.jpg", b"private-image", "image/jpeg")},
        )
        assert upload_without_token.status_code == 403
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/photos",
            headers={"X-Case-Access-Token": case_access_token},
            files={"photo": ("leaf.jpg", b"private-image", "image/jpeg")},
        )
        assert uploaded.status_code == 201, uploaded.text
        filename = uploaded.json()["url"].split("/")[-1]
        assert client.get(uploaded.json()["url"]).status_code == 404
        assert client.get(f"/api/v1/cases/{case_id}/photos/{filename}").status_code == 401
        expert_login = client.post(
            "/api/v1/auth/login",
            json={"email": "demo.expert@example.com", "password": "demo-expert"},
        )
        assert expert_login.status_code == 200
        expert_headers = {"Authorization": f"Bearer {expert_login.json()['access_token']}"}
        photo = client.get(f"/api/v1/cases/{case_id}/photos/{filename}", headers=expert_headers)
        assert photo.status_code == 200
        assert photo.content == b"private-image"
        assert photo.headers["cache-control"] == "private, no-store"
        assert client.post(
            "/api/v1/cases",
            json={"farmer_id": farmer["id"], "description": "Untrusted direct case"},
        ).status_code == 401
        cases = client.get("/api/v1/market/farmer/cases", headers=farmer_headers)
        assert cases.status_code == 200
        assert len(cases.json()) == 1
        assert cases.json()[0]["farmer_id"] == farmer["id"]

        work_date = (date.today() + timedelta(days=1)).isoformat()
        job = client.post(
            "/api/v1/market/jobs", headers=farmer_headers,
            json={
                "title": "Cotton picking", "description": "Pick cotton in the north field",
                "village": "Nalgonda", "mandal": "Nalgonda", "work_date": work_date,
                "required_workers": 2, "daily_wage": 650, "latitude": 17.0575, "longitude": 79.2684,
            },
        )
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]
        invalid_location = client.post(
            "/api/v1/market/jobs", headers=farmer_headers,
            json={
                "title": "Invalid location", "village": "Nalgonda", "mandal": "Nalgonda",
                "work_date": work_date, "required_workers": 1, "daily_wage": 500, "latitude": 17.0,
            },
        )
        assert invalid_location.status_code == 422
        matches = client.get("/api/v1/market/jobs/nearby", headers=worker_headers)
        assert matches.status_code == 200
        matched_job = next(item for item in matches.json() if item["id"] == job_id)
        assert matched_job["distance_km"] < 1
        assert client.get("/api/v1/market/jobs/nearby?radius_km=101", headers=worker_headers).status_code == 422
        worker_matches = client.get("/api/v1/market/workers/nearby", headers=farmer_headers)
        assert worker_matches.status_code == 200
        matched_worker = next(item for item in worker_matches.json() if item["id"] == worker["id"])
        assert matched_worker["distance_km"] < 1
        assert "phone" not in matched_worker

        team = client.post("/api/v1/market/teams", headers=worker_headers, json={"name": "Cotton Crew"})
        assert team.status_code == 201, team.text
        team_id = team.json()["id"]
        add_member = client.post(
            f"/api/v1/market/teams/{team_id}/members",
            headers=worker_headers,
            json={"phone": member_phone},
        )
        assert add_member.status_code == 201, add_member.text
        assert len(add_member.json()["members"]) == 2
        unavailable = client.patch(
            "/api/v1/market/worker/profile",
            headers=member_headers,
            json={
                "name": "Worker Two", "village": "Nalgonda", "mandal": "Nalgonda",
                "latitude": 17.061, "longitude": 79.271, "skills": "cotton picking",
                "daily_wage": 600, "is_available": False,
            },
        )
        assert unavailable.status_code == 200
        unavailable_apply = client.post(
            f"/api/v1/market/jobs/{job_id}/applications",
            headers=worker_headers,
            json={"proposed_wage": 600, "team_id": team_id},
        )
        assert unavailable_apply.status_code == 409
        available = client.patch(
            "/api/v1/market/worker/profile",
            headers=member_headers,
            json={
                "name": "Worker Two", "village": "Nalgonda", "mandal": "Nalgonda",
                "latitude": 17.061, "longitude": 79.271, "skills": "cotton picking",
                "daily_wage": 600, "is_available": True,
            },
        )
        assert available.status_code == 200
        application = client.post(
            f"/api/v1/market/jobs/{job_id}/applications",
            headers=worker_headers,
            json={"proposed_wage": 600, "team_id": team_id},
        )
        assert application.status_code == 201, application.text
        application_id = application.json()["id"]
        counter = client.patch(
            f"/api/v1/market/farmer/applications/{application_id}/offer",
            headers=farmer_headers, json={"proposed_wage": 700},
        )
        assert counter.status_code == 200
        assert counter.json()["proposed_wage"] == 700
        accepted = client.post(
            f"/api/v1/market/farmer/applications/{application_id}/accept",
            headers=farmer_headers,
        )
        assert accepted.status_code == 200, accepted.text
        pending_bookings = accepted.json()
        assert len(pending_bookings) == 2
        assert {item["status"] for item in pending_bookings} == {"PENDING"}
        assert all(item["worker_phone"] is None for item in pending_bookings)
        pending_farmer_view = client.get("/api/v1/market/farmer/bookings", headers=farmer_headers)
        assert all(item["worker_phone"] is None for item in pending_farmer_view.json())

        for headers in (worker_headers, member_headers):
            own = client.get("/api/v1/market/worker/bookings", headers=headers)
            assert own.status_code == 200
            booking = next(item for item in own.json() if item["job_id"] == job_id)
            confirmed = client.post(f"/api/v1/market/worker/bookings/{booking['id']}/confirm", headers=headers)
            assert confirmed.status_code == 200, confirmed.text
            assert confirmed.json()["status"] == "CONFIRMED"
            assert confirmed.json()["farmer_phone"] == farmer_phone

        farmer_bookings = client.get("/api/v1/market/farmer/bookings", headers=farmer_headers)
        assert farmer_bookings.status_code == 200
        assert all(item["worker_phone"] for item in farmer_bookings.json())

        duplicate_job = client.post(
            "/api/v1/market/jobs", headers=farmer_headers,
            json={
                "title": "Second field", "village": "Nalgonda", "mandal": "Nalgonda",
                "work_date": work_date, "required_workers": 1, "daily_wage": 700,
            },
        )
        assert duplicate_job.status_code == 201
        double_booking = client.post(
            f"/api/v1/market/jobs/{duplicate_job.json()['id']}/applications",
            headers=worker_headers, json={"proposed_wage": 700},
        )
        assert double_booking.status_code == 409
        with SessionLocal() as db:
            conflicting_job = MarketJob(
                farmer_id=farmer["id"], title="Direct conflict", description="",
                village="Nalgonda", mandal="Nalgonda", work_date=date.fromisoformat(work_date),
                required_workers=1, daily_wage=700,
            )
            db.add(conflicting_job)
            db.flush()
            conflicting_application = JobApplication(
                job_id=conflicting_job.id, worker_id=worker["id"], proposed_wage=700,
            )
            db.add(conflicting_application)
            db.flush()
            db.add(JobBooking(
                application_id=conflicting_application.id, job_id=conflicting_job.id,
                worker_id=worker["id"], work_date=date.fromisoformat(work_date),
                agreed_wage=700, status="PENDING",
            ))
            try:
                db.commit()
                raise AssertionError("The database must reject two active bookings for one worker and date.")
            except IntegrityError:
                db.rollback()
