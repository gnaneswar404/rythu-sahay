# RYTHU SAHAYA

RYTHU SAHAYA is a Telugu-first, case-resolution MVP for **cotton farmers in Nalgonda district, Telangana**. It is designed around one workflow: **Advice → Action → Verification → Resolution**.

This is intentionally not a generic chatbot. The API rejects non-Nalgonda districts and non-cotton crops. The farmer interface is Telugu-first, works with typing and a large keypad, and uses browser speech recognition and browser speech synthesis when available. The expert dashboard handles triage, assignment, expert notes, follow-ups, and farmer outcomes.

> **Demo safety notice:** Seeded farmers, cases, experts, and knowledge records are explicitly synthetic demonstration data. Bundled knowledge does not include pesticide names, chemical application rates, or treatment dosages, and it is not described as expert-approved guidance.

## What is implemented

- React/Vite/Tailwind farmer experience with large Telugu microphone control, text fallback, keypad fallback, consent control, optional crop-photo upload, session end, and outcome feedback.
- English/Telugu language switch for the farmer and expert screens; the selection is remembered in the browser.
- FastAPI application with SQLite fallback, SQLAlchemy models, input validation, CORS, health check, Google OAuth expert sign-in, password hashing for local demo accounts, signed expert bearer tokens, indexes, and demo seeding.
- Structured farmer, case, expert, action, follow-up, and conversation records.
- Case IDs in `RS-YYYY-NNNN` format; statuses from `NEW` through `ESCALATED` and `RESOLVED`.
- Server-side Nalgonda/cotton scope enforcement, including out-of-scope Telugu conversation response.
- Expert dashboard with protected case search, filter, review, assignment, expert notes, status changes, and follow-up scheduling.
- Farmer and worker accounts use role-specific username/password registration and signed sessions. Passwords are stored as bcrypt hashes; phone numbers are optional marketplace contact details, not login credentials.
- Farmer dashboard for the signed-in farmer's own crop cases, plus a worker marketplace for job posting, radius-based matching, group applications, worker teams, wage negotiation, booking confirmation, same-day double-booking prevention, and post-confirmation call links.
- Configurable Supabase PostgreSQL connection via `SUPABASE_DATABASE_URL`; SQLite remains the local default.
- Farmer feedback endpoint that escalates a case when the reported outcome is `WORSENED`.
- Farmer photo uploads require the case access token, and photo reads are authenticated for experts rather than exposed through a public static upload directory.
- Replaceable voice and telephony adapter boundaries, with honest local mock implementations. A mock webhook never claims a real number is active.
- A tool-only AI action boundary (`AgriculturalAgentTools`) so an LLM integration can request validated actions without receiving database access.
- OpenAPI documentation and API tests.

## Project layout

```text
backend/                 FastAPI API, data model, services, tests
  app/knowledge/         Cotton demonstration knowledge records
  app/voice/             Speech-provider contract and safe mock
  app/telephony/         Provider contract and safe mock
frontend/                React/Vite/Tailwind user interface
docs/API.md              Endpoint reference
TODO.md                  MVP state and production integration work
docker-compose.yml       One-command local containers
```

## Run locally

Use Python 3.11 or 3.12 and Node.js 20+.

### 1. Configure environment

PowerShell:

```powershell
Copy-Item .env.example backend\.env
```

For Supabase, paste the PostgreSQL connection URI from the project's **Connect** dialog into `SUPABASE_DATABASE_URL` in `backend/.env`, including `sslmode=require`. This setting takes precedence over `DATABASE_URL`. The app creates missing tables at startup and migrates existing farmer/worker tables for location, username/password credentials, and optional worker contact numbers. Existing phone-only accounts are preserved but need a new username/password account to sign in. A live Supabase connection cannot be verified without a project URI and credentials.

The default `DATABASE_URL` uses local SQLite. It creates `backend/rythu_sahaya.db` when the backend starts. PostgreSQL support is included through `psycopg[binary]` in `backend/requirements.txt`; set `SUPABASE_DATABASE_URL` (recommended) or `DATABASE_URL` to a PostgreSQL connection URI with SSL enabled when using Supabase.

### 2. Start the backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify [http://localhost:8000/health](http://localhost:8000/health), then inspect the interactive API at [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Configure expert Google sign-in

The expert login accepts Google accounts through Google Identity Services. The app never receives or checks a Google password. A verified Google account automatically receives an expert account on its first sign-in.

1. In Google Cloud Console, configure the OAuth consent screen and create an OAuth client ID for a **Web application**.
2. Add the app origin (for local development, `http://localhost:5173`) to the OAuth client's authorized JavaScript origins.
3. Set the client ID in `backend/.env` as `GOOGLE_CLIENT_ID`, then restart the backend. The frontend obtains this public OAuth client ID from the API, so a second frontend environment variable is not required. (`VITE_GOOGLE_CLIENT_ID` remains available as an optional build-time override.)
4. For Docker Compose, set `GOOGLE_CLIENT_ID` in the environment used to run Compose and restart the stack.

Without these settings, Google sign-in is unavailable; the local demo account remains usable.

### Farmer and worker accounts

Farmers and workers can create accounts with a username and password, then use the same credentials for later sign-ins. Usernames are case-insensitive and unique per account type. Passwords must be at least 8 characters; only bcrypt password hashes are stored. An optional phone number is for marketplace contact features only and is never used to register or authenticate.

The farmer assistant associates new cases with the signed-in farmer. The farmer dashboard shows only that account's cases. Workers must set their location to get distance-ranked open jobs; farmers must set a location on each job to make it eligible for nearby matching. Contact phone numbers are hidden from search and negotiation responses and exposed to the other party only after a worker confirms the booking.

### Local test commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
```

Marketplace API tests cover farmer and worker registration, repeat sign-in, role-specific sessions, and marketplace workflows. Supabase connectivity still requires credentials and is not covered by the local tests.

### Alternative: Docker Compose

```powershell
docker compose up --build
```

The Compose setup uses SQLite for a no-credential local demo. It may take longer on its first run while it downloads Python and Node images.

## Hackathon demo script

1. Open the farmer site, check consent, and choose **సహాయం ప్రారంభించండి**.
2. Tap the microphone (in a compatible browser) or enter: `నా పత్తి పంట ఆకులు పసుపు రంగులోకి మారుతున్నాయి.`
3. Answer the next four small questions: duration, symptoms, village, and mandal. The browser shows each Telugu response and speaks it where supported.
4. Observe the structured case acknowledgement, e.g. `RS-2026-0002`. It states that expert review is needed rather than claiming a diagnosis.
5. Use **నిపుణుల లాగిన్**. The prefilled synthetic demo account is:

   - Email: `demo.expert@example.com`
   - Password: `demo-expert`

6. Filter/search the case, select it, then choose **నాకు కేటాయించు**.
7. Add an expert note, save it, and schedule a follow-up date.
8. Return to the farmer experience and record `మెరుగుపడింది`, `మార్పు లేదు`, or `దిగజారింది`. A worsening report automatically changes the case to `ESCALATED`.

## Safety and scope rules

- Pilot scope is **Telugu-speaking cotton farmers in Nalgonda district only**. Both UI wording and Pydantic validation enforce this; out-of-scope case creation returns a useful validation error.
- No bundled knowledge item is presented as a verified diagnosis or as expert approval. Uncertainty, potential severity, or missing verified information leads to expert review.
- The UI deliberately does not advise pesticide products, active ingredients, concentrations, or dosages.
- There is no claim that a phone number, SMS reminder, Sarvam service, or Exotel connection is active. Until credentials and provider contracts are configured, mock mode remains enabled.
- Expert pages are bearer-token protected. Demo credentials are for the local MVP only; replace the default secret and bootstrap real accounts before deployment.
- The worker marketplace is currently scoped to one work date per booking and a maximum 100 km search radius. A team's leader submits the application; every reserved worker confirms their own booking.
- Supabase schema setup currently uses SQLAlchemy `create_all` plus a small compatibility migration, not a versioned Alembic migration workflow. Back up production data and use a formal migration process before future schema changes.
- Farmer and worker authentication uses stored bcrypt password hashes. Supabase connectivity has not been verified in this credential-free workspace.

## Voice and telephone production hand-off

`backend/app/voice/` and `backend/app/telephony/` are provider boundaries. Production work must verify the **current** Sarvam and Exotel API contracts before inserting SDK calls. Then:

1. Put real keys only in `backend/.env` or a production secret manager.
2. Implement the provider methods behind `SpeechProvider` and `TelephonyProvider`.
3. Set `MOCK_VOICE_ENABLED=false` and `MOCK_TELEPHONY_ENABLED=false` only after integration tests pass.
4. Configure an HTTPS Exotel webhook at `/api/v1/telephony/incoming`; complete KYC and activate a real number separately.
5. Add data-retention, consent wording review, rate-limiting storage, PostgreSQL migrations, and production monitoring before handling real farmer data.

### LLM agent integration

The deterministic Telugu conversation service is the credential-free hackathon fallback. When a tool-calling LLM is enabled, give it only `AgriculturalAgentTools` from `backend/app/agents/tools.py`—never an ORM session or database connection. Its available actions map to validated operations such as `create_farmer`, `create_case`, `get_verified_guidance`, `assign_expert`, `update_case_status`, `schedule_followup`, and `record_farmer_feedback`. The agent must wait for a tool result before confirming that any case, assignment, or follow-up exists.

## Tests

```powershell
cd backend
pytest
```

The API test confirms health, district rejection, Telugu conversation-to-case creation, expert sign-in, expert access, and a status update. See [docs/API.md](docs/API.md) for endpoint details.
