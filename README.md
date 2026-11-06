# RYTHU SAHAYA

RYTHU SAHAYA is a Telugu-first case-recording and labor-marketplace MVP for **cotton farmers in Nalgonda district, Telangana**.

The app provides farmer and worker marketplace accounts, a searchable public view of job listings and available workers, a farmer case list, and a Telugu-first API for recording cotton crop cases. Recruiting requires a farmer account; applying for work requires a worker account. There is no expert sign-in or case-management dashboard.

> **Demo safety notice:** Seeded farmers, cases, and knowledge records are explicitly synthetic demonstration data. Bundled knowledge does not include pesticide names, chemical application rates, or treatment dosages, and it is not a diagnosis or verified treatment guidance.

## What is implemented

- React/Vite/Tailwind sign-in page and farmer/worker marketplace with an English/Telugu language switch remembered in the browser.
- FastAPI application with SQLite fallback, SQLAlchemy models, input validation, CORS, health check, farmer/worker password hashing, signed account tokens, indexes, and demo seeding.
- Structured farmer, case, action, follow-up, and conversation records.
- Case IDs in `RS-YYYY-NNNN` format; statuses from `NEW` through `ESCALATED` and `RESOLVED`.
- Server-side Nalgonda/cotton scope enforcement, including out-of-scope Telugu conversation response.
- Farmer and worker accounts use role-specific username/password registration and signed sessions. Passwords are stored as bcrypt hashes; phone numbers are optional marketplace contact details, not login credentials.
- Public job and worker listings support searching by work, name, skills, and location. Phone contact is shown only when the account owner opts in; exact coordinates are never exposed in public profiles.
- Farmers and workers can upload JPEG, PNG, or WebP profile photos (up to 3 MB); the photo is shown with public marketplace listings.
- Separate farmer and worker dashboards for posting work, finding workers/jobs, recruitment progress, applications, teams, profiles, and bookings. Matching supports 5/10/20 km searches, real-coordinate distance, same-village priority, village fallback, skills/wage indicators, and available-worker filtering.
- Team applications recruit all members together with per-member confirmation and booking protection. Farmers can report a confirmed worker absent and reopen the position to search for available replacements.
- Phone links are consent-gated both on public profiles and confirmed bookings. Existing records default to private; an additive startup migration adds the consent field without replacing tables.
- Wage offers/counteroffers and the mutually accepted wage are shown in application/booking views. Historical wage trends are not displayed because no historical wage analytics are stored.
- Farmers can dictate job descriptions using supported browser speech recognition (including Telugu where the browser provides it) and review all fields before publishing; manual entry remains available.
- Configurable Supabase PostgreSQL connection via `SUPABASE_DATABASE_URL`; SQLite remains the local default.
- Farmer feedback endpoint that escalates a case when the reported outcome is `WORSENED`.
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

Existing databases are not destructively migrated: legacy expert account rows and case-assignment columns are left untouched, but the application no longer maps, reads, or exposes them.

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

### Farmer and worker accounts

Farmers and workers can create accounts with a username and password, then use the same credentials for later sign-ins. Usernames are case-insensitive and unique per account type. Passwords must be at least 8 characters; only bcrypt password hashes are stored. An optional phone number is for marketplace contact features only and is never used to register or authenticate.

Cases created through the conversation API are associated with the signed-in farmer when a farmer token is supplied. The farmer dashboard shows only that account's cases. GPS-enabled matches use worksite coordinates and Haversine distance. When GPS is unavailable, the service falls back to same-village matches; those results do not claim a distance. A profile consent checkbox controls public phone visibility and whether booking call details are shared.

### Local test commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
```

Marketplace API tests cover farmer and worker registration, repeat sign-in, role-specific sessions, booking-participant chat, and marketplace workflows. Supabase connectivity still requires credentials and is not covered by the local tests.

### Alternative: Docker Compose

```powershell
docker compose up --build
```

The Compose setup uses SQLite for a no-credential local demo. It may take longer on its first run while it downloads Python and Node images.

## Demo flow

1. Select English or Telugu on the landing page.
2. Open the profile menu and sign in or register as a farmer or worker.
3. Use the farmer marketplace to manage a profile, view the account's crop cases, and use the labor marketplace. Workers can complete a profile and find nearby jobs.
4. The crop-case conversation endpoints remain available through the API. Case responses are not diagnoses; consult a local agricultural officer for advice.

## Safety and scope rules

- Pilot scope is **Telugu-speaking cotton farmers in Nalgonda district only**. Both UI wording and Pydantic validation enforce this; out-of-scope case creation returns a useful validation error.
- No bundled knowledge item is presented as a verified diagnosis. Uncertainty or potentially severe symptoms should be taken to a local agricultural officer.
- The UI deliberately does not advise pesticide products, active ingredients, concentrations, or dosages.
- Sarvam and Exotel are not integrated in this workspace. The Sarvam key is not configured, the backend speech provider remains a mock, and browser speech dictation depends on browser support and permission. No SMS or real telephony provider is claimed active.
- The worker marketplace is scoped to one work date per booking and a maximum 100 km API radius (dashboard presets are 5, 10, and 20 km). A team's leader submits the application; every reserved worker confirms their own booking.
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

The deterministic Telugu conversation service is the credential-free hackathon fallback. When a tool-calling LLM is enabled, give it only `AgriculturalAgentTools` from `backend/app/agents/tools.py`—never an ORM session or database connection. Its available actions map to validated operations such as `create_farmer`, `create_case`, `get_verified_guidance`, and `record_farmer_feedback`. The agent must wait for a tool result before confirming that any case or feedback exists.

## Tests

```powershell
cd backend
pytest
```

The API tests cover health, district rejection, demo seeding, removed expert endpoints, Telugu conversation-to-case creation, and farmer feedback. See [docs/API.md](docs/API.md) for endpoint details.
