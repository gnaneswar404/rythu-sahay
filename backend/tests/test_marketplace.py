from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

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
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": "Calling farmer", "allow_phone_contact": True},
        ).status_code == 200
        assert client.patch(
            "/api/v1/market/worker/profile",
            headers=worker_headers,
            json={"name": "Calling worker", "allow_phone_contact": True},
        ).status_code == 200
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
        assert confirmed.json()["worker_phone"] == worker_phone

        duplicate = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{worker['id']}/book",
            headers=farmer_headers,
        )
        assert duplicate.status_code == 409


def test_logged_out_marketplace_lists_public_jobs_and_available_workers():
    with TestClient(app) as client:
        farmer_headers, _ = sign_in(client, "farmer", phone())
        worker_headers, worker = sign_in(client, "worker", phone())
        recruiter_name = f"Recruiter Searchable {uuid4().hex[:8]}"
        worker_name = f"Worker Searchable {uuid4().hex[:8]}"
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": recruiter_name, "village": "Nalgonda", "mandal": "Nalgonda"},
        ).status_code == 200
        assert client.patch(
            "/api/v1/market/worker/profile",
            headers=worker_headers,
            json={
                "name": worker_name,
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "skills": "cotton picking",
                "daily_wage": 650,
                "is_available": True,
            },
        ).status_code == 200
        created_job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Public cotton picking job",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "work_date": (date.today() + timedelta(days=1)).isoformat(),
                "daily_wage": 650,
                "required_workers": 2,
            },
        )
        assert created_job.status_code == 201

        jobs = client.get("/api/v1/market/public/jobs", params={"search": recruiter_name})
        workers = client.get("/api/v1/market/public/workers", params={"search": worker_name})
        assert jobs.status_code == 200
        matching_job = next(item for item in jobs.json() if item["id"] == created_job.json()["id"])
        assert matching_job["recruiter_name"] == recruiter_name
        assert "farmer_id" not in matching_job
        assert "latitude" not in matching_job
        assert workers.status_code == 200
        matching_worker = next(item for item in workers.json() if item["id"] == worker["id"])
        assert matching_worker["name"] == worker_name
        assert "phone" not in matching_worker
        assert "latitude" not in matching_worker


def test_farmer_and_worker_can_upload_and_remove_public_profile_photos():
    with TestClient(app) as client:
        farmer_headers, _ = sign_in(client, "farmer", phone())
        worker_headers, worker = sign_in(client, "worker", phone())
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": "Photo recruiter", "village": "Nalgonda", "mandal": "Nalgonda", "latitude": 17.1, "longitude": 79.2},
        ).status_code == 200
        assert client.patch(
            "/api/v1/market/worker/profile",
            headers=worker_headers,
            json={
                "name": "Photo worker", "village": "Nalgonda", "mandal": "Nalgonda",
                "latitude": 17.2, "longitude": 79.3, "skills": "cotton picking",
                "daily_wage": 650, "is_available": True,
            },
        ).status_code == 200
        farmer_image = b"\x89PNG\r\n\x1a\nfarmer-photo"
        worker_image = b"\xff\xd8\xffworker-photo"

        assert client.post(
            "/api/v1/market/farmer/profile/photo",
            headers=worker_headers,
            files={"photo": ("farmer.png", farmer_image, "image/png")},
        ).status_code == 401
        bad_type = client.post(
            "/api/v1/market/worker/profile/photo",
            headers=worker_headers,
            files={"photo": ("photo.svg", b"<svg></svg>", "image/svg+xml")},
        )
        assert bad_type.status_code == 415
        too_large = client.post(
            "/api/v1/market/worker/profile/photo",
            headers=worker_headers,
            files={"photo": ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (3 * 1024 * 1024), "image/png")},
        )
        assert too_large.status_code == 413

        farmer_upload = client.post(
            "/api/v1/market/farmer/profile/photo",
            headers=farmer_headers,
            files={"photo": ("farmer.png", farmer_image, "image/png")},
        )
        worker_upload = client.post(
            "/api/v1/market/worker/profile/photo",
            headers=worker_headers,
            files={"photo": ("worker.jpg", worker_image, "image/jpeg")},
        )
        assert farmer_upload.status_code == worker_upload.status_code == 200
        job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Photo listing job",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "work_date": (date.today() + timedelta(days=1)).isoformat(),
                "daily_wage": 650,
                "required_workers": 1,
            },
        )
        assert job.status_code == 201
        assert client.get("/api/v1/market/farmer/profile", headers=farmer_headers).json()["profile_photo_url"] == farmer_upload.json()["profile_photo_url"]
        assert client.get("/api/v1/market/worker/profile", headers=worker_headers).json()["profile_photo_url"] == worker_upload.json()["profile_photo_url"]
        private_farmer_profile = client.get("/api/v1/market/farmer/profile", headers=farmer_headers).json()
        private_worker_profile = client.get("/api/v1/market/worker/profile", headers=worker_headers).json()
        public_farmer = client.get(f"/api/v1/market/public/profiles/farmer/{private_farmer_profile['id']}")
        public_worker = client.get(f"/api/v1/market/public/profiles/worker/{private_worker_profile['id']}")
        assert public_farmer.status_code == public_worker.status_code == 200
        assert public_farmer.json()["phone"] is None
        assert public_worker.json()["phone"] is None
        assert "latitude" not in public_farmer.json()
        assert "longitude" not in public_farmer.json()
        assert "latitude" not in public_worker.json()
        assert "longitude" not in public_worker.json()
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": "Photo recruiter", "allow_phone_contact": True},
        ).status_code == 200
        assert client.patch(
            "/api/v1/market/worker/profile",
            headers=worker_headers,
            json={"name": "Photo worker", "allow_phone_contact": True},
        ).status_code == 200
        public_farmer = client.get(f"/api/v1/market/public/profiles/farmer/{private_farmer_profile['id']}")
        public_worker = client.get(f"/api/v1/market/public/profiles/worker/{private_worker_profile['id']}")
        assert public_farmer.json()["phone"] == private_farmer_profile["phone"]
        assert public_worker.json()["phone"] == private_worker_profile["phone"]
        assert public_worker.json()["skills"] == "cotton picking"

        farmer_photo = client.get(farmer_upload.json()["profile_photo_url"])
        worker_photo = client.get(worker_upload.json()["profile_photo_url"])
        assert farmer_photo.content == farmer_image
        assert farmer_photo.headers["content-type"] == "image/png"
        assert worker_photo.content == worker_image
        assert worker_photo.headers["content-type"] == "image/jpeg"
        job_listing = client.get("/api/v1/market/public/jobs").json()
        photo_job_listing = next(item for item in job_listing if item["id"] == job.json()["id"])
        assert photo_job_listing["recruiter_photo_url"] == farmer_upload.json()["profile_photo_url"]
        assert photo_job_listing["recruiter_id"] == private_farmer_profile["id"]
        worker_listing = client.get("/api/v1/market/public/workers").json()
        assert next(item for item in worker_listing if item["id"] == worker["id"])["profile_photo_url"] == worker_upload.json()["profile_photo_url"]

        replacement_photo = b"\xff\xd8\xffreplacement-photo"
        replacement_upload = client.post(
            "/api/v1/market/worker/profile/photo",
            headers=worker_headers,
            files={"photo": ("new-worker.jpg", replacement_photo, "image/jpeg")},
        )
        assert replacement_upload.status_code == 200
        assert replacement_upload.json()["profile_photo_url"] != worker_upload.json()["profile_photo_url"]
        assert client.get(replacement_upload.json()["profile_photo_url"]).content == replacement_photo
        worker_listing = client.get("/api/v1/market/public/workers").json()
        assert next(item for item in worker_listing if item["id"] == worker["id"])["profile_photo_url"] == replacement_upload.json()["profile_photo_url"]

        removed = client.delete("/api/v1/market/worker/profile/photo", headers=worker_headers)
        assert removed.status_code == 200
        assert removed.json()["profile_photo_url"] is None
        assert client.get(replacement_upload.json()["profile_photo_url"]).status_code == 404


def test_booking_chat_is_shared_only_with_booking_farmer_and_worker():
    with TestClient(app) as client:
        farmer_headers, _ = sign_in(client, "farmer", phone())
        worker_headers, worker = sign_in(client, "worker", phone())
        other_farmer_headers, _ = sign_in(client, "farmer", phone())
        job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Field work",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "work_date": (date.today() + timedelta(days=2)).isoformat(),
                "daily_wage": 700,
                "required_workers": 1,
            },
        )
        booking = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{worker['id']}/book",
            headers=farmer_headers,
        )
        booking_id = booking.json()["id"]

        sent = client.post(
            f"/api/v1/market/farmer/bookings/{booking_id}/messages",
            headers=farmer_headers,
            json={"message": "Please arrive at 8 AM."},
        )
        assert sent.status_code == 201
        received = client.get(
            f"/api/v1/market/worker/bookings/{booking_id}/messages",
            headers=worker_headers,
        )
        assert received.status_code == 200
        assert received.json()[0]["message"] == "Please arrive at 8 AM."
        assert received.json()[0]["sender_type"] == "farmer"

        reply = client.post(
            f"/api/v1/market/worker/bookings/{booking_id}/messages",
            headers=worker_headers,
            json={"message": "I will be there."},
        )
        assert reply.status_code == 201
        farmer_messages = client.get(
            f"/api/v1/market/farmer/bookings/{booking_id}/messages",
            headers=farmer_headers,
        )
        assert [item["message"] for item in farmer_messages.json()] == [
            "Please arrive at 8 AM.",
            "I will be there.",
        ]
        assert client.get(
            f"/api/v1/market/farmer/bookings/{booking_id}/messages",
            headers=other_farmer_headers,
        ).status_code == 404
        assert client.post(
            f"/api/v1/market/farmer/bookings/{booking_id}/messages",
            headers=farmer_headers,
            json={"message": "   "},
        ).status_code == 422


def test_farmer_cases_and_complete_group_recruitment_workflow():
    farmer_phone = phone()
    worker_phone = phone()
    member_phone = phone()
    with TestClient(app) as client:
        farmer_headers, farmer = sign_in(client, "farmer", farmer_phone)
        worker_headers, worker = sign_in(client, "worker", worker_phone)
        member_headers, member = sign_in(client, "worker", member_phone)

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
        assert job.json()["interested_workers"] == 0
        assert job.json()["confirmed_workers"] == 0
        assert job.json()["remaining_workers"] == 2
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
        assert matched_job["same_village"] is True
        assert matched_job["skill_match"] is True
        assert matched_job["wage_match"] is True
        assert client.get("/api/v1/market/jobs/nearby?radius_km=101", headers=worker_headers).status_code == 422
        worker_matches = client.get("/api/v1/market/workers/nearby", headers=farmer_headers)
        assert worker_matches.status_code == 200
        matched_worker = next(item for item in worker_matches.json() if item["id"] == worker["id"])
        assert matched_worker["distance_km"] < 1
        assert matched_worker["same_village"] is True
        assert matched_worker["skill_match"] is True
        assert matched_worker["wage_match"] is True
        assert "phone" not in matched_worker

        team = client.post("/api/v1/market/teams", headers=worker_headers, json={"name": "Cotton Crew"})
        assert team.status_code == 201, team.text
        team_id = team.json()["id"]
        add_member = client.post(
            f"/api/v1/market/teams/{team_id}/members",
            headers=worker_headers,
            json={"username": member["username"].upper()},
        )
        assert add_member.status_code == 201, add_member.text
        assert len(add_member.json()["members"]) == 2
        missing_member = client.post(
            f"/api/v1/market/teams/{team_id}/members",
            headers=worker_headers,
            json={"username": f"missing-{uuid4().hex[:8]}"},
        )
        assert missing_member.status_code == 404
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
        job_progress = next(
            item for item in client.get("/api/v1/market/jobs/mine", headers=farmer_headers).json()
            if item["id"] == job_id
        )
        assert job_progress["interested_workers"] == 2
        assert job_progress["pending_workers"] == 2
        assert job_progress["remaining_workers"] == 0
        pending_farmer_view = client.get("/api/v1/market/farmer/bookings", headers=farmer_headers)
        assert all(item["worker_phone"] is None for item in pending_farmer_view.json())

        for headers in (worker_headers, member_headers):
            own = client.get("/api/v1/market/worker/bookings", headers=headers)
            assert own.status_code == 200
            booking = next(item for item in own.json() if item["job_id"] == job_id)
            confirmed = client.post(f"/api/v1/market/worker/bookings/{booking['id']}/confirm", headers=headers)
            assert confirmed.status_code == 200, confirmed.text
            assert confirmed.json()["status"] == "CONFIRMED"
            assert confirmed.json()["farmer_phone"] is None

        farmer_bookings = client.get("/api/v1/market/farmer/bookings", headers=farmer_headers)
        assert farmer_bookings.status_code == 200
        assert all(item["worker_phone"] is None for item in farmer_bookings.json())

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


def test_nearby_matching_uses_same_village_when_coordinates_are_missing():
    with TestClient(app) as client:
        farmer_headers, _ = sign_in(client, "farmer", phone())
        worker_headers, _ = sign_in(client, "worker", phone())
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={"name": "Village Farmer", "village": "Nalgonda", "mandal": "Nalgonda"},
        ).status_code == 200
        assert client.patch(
            "/api/v1/market/worker/profile",
            headers=worker_headers,
            json={
                "name": "Village Worker", "village": " nalgonda ", "mandal": "Nalgonda",
                "skills": "cotton picking", "daily_wage": 500, "is_available": True,
            },
        ).status_code == 200
        job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Cotton picking",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "work_date": (date.today() + timedelta(days=1)).isoformat(),
                "daily_wage": 600,
                "required_workers": 1,
            },
        )
        assert job.status_code == 201, job.text
        jobs = client.get("/api/v1/market/jobs/nearby?radius_km=5", headers=worker_headers)
        match = next(item for item in jobs.json() if item["id"] == job.json()["id"])
        assert match["distance_km"] is None
        assert match["same_village"] is True
        assert match["skill_match"] is True
        assert match["wage_match"] is True
        workers = client.get("/api/v1/market/workers/nearby?radius_km=5", headers=farmer_headers)
        match = next(item for item in workers.json() if item["name"] == "Village Worker")
        assert match["distance_km"] is None
        assert match["same_village"] is True


def test_absent_worker_can_be_replaced_with_consent_gated_contact():
    with TestClient(app) as client:
        farmer_headers, _ = sign_in(client, "farmer", phone())
        booked_headers, booked_worker = sign_in(client, "worker", phone())
        replacement_phone = phone()
        replacement_headers, replacement_worker = sign_in(client, "worker", replacement_phone)
        assert client.patch(
            "/api/v1/market/farmer/profile",
            headers=farmer_headers,
            json={
                "name": "Replacement Farmer", "village": "Nalgonda", "mandal": "Nalgonda",
                "latitude": 17.0575, "longitude": 79.2684,
            },
        ).status_code == 200
        for headers, name, can_call in (
            (booked_headers, "Absent Worker", False),
            (replacement_headers, "Replacement Worker", True),
        ):
            updated = client.patch(
                "/api/v1/market/worker/profile",
                headers=headers,
                json={
                    "name": name, "village": "Nalgonda", "mandal": "Nalgonda",
                    "latitude": 17.06, "longitude": 79.27, "skills": "cotton picking",
                    "daily_wage": 500, "is_available": True, "allow_phone_contact": can_call,
                },
            )
            assert updated.status_code == 200, updated.text
        job = client.post(
            "/api/v1/market/jobs",
            headers=farmer_headers,
            json={
                "title": "Cotton picking replacement",
                "description": "Cotton picking",
                "village": "Nalgonda",
                "mandal": "Nalgonda",
                "latitude": 17.0575,
                "longitude": 79.2684,
                "work_date": (date.today() + timedelta(days=1)).isoformat(),
                "daily_wage": 600,
                "required_workers": 1,
            },
        )
        assert job.status_code == 201, job.text
        booked = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{booked_worker['id']}/book",
            headers=farmer_headers,
        )
        assert booked.status_code == 201
        confirmation = client.post(
            f"/api/v1/market/worker/bookings/{booked.json()['id']}/confirm",
            headers=booked_headers,
        )
        assert confirmation.status_code == 200
        assert confirmation.json()["worker_phone"] is None
        absence = client.post(
            f"/api/v1/market/farmer/bookings/{booked.json()['id']}/report-absence",
            headers=farmer_headers,
        )
        assert absence.status_code == 200
        assert absence.json()["status"] == "ABSENT"
        progress = next(
            item for item in client.get("/api/v1/market/jobs/mine", headers=farmer_headers).json()
            if item["id"] == job.json()["id"]
        )
        assert progress["status"] == "OPEN"
        assert progress["remaining_workers"] == 1
        replacements = client.get(
            f"/api/v1/market/farmer/bookings/{booked.json()['id']}/replacements?radius_km=5",
            headers=farmer_headers,
        )
        assert replacements.status_code == 200, replacements.text
        candidate = next(item for item in replacements.json() if item["id"] == replacement_worker["id"])
        assert candidate.get("phone") == replacement_phone, candidate
        assert candidate["skill_match"] is True
        invited = client.post(
            f"/api/v1/market/jobs/{job.json()['id']}/workers/{replacement_worker['id']}/book",
            headers=farmer_headers,
        )
        assert invited.status_code == 201, invited.text
        assert invited.json()["worker_phone"] is None
