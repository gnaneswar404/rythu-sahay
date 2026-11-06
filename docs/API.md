# API reference

The interactive OpenAPI specification is served by the backend at `/docs`.

## Farmer-facing endpoints

| Method | Endpoint | Use |
| --- | --- | --- |
| `POST` | `/api/v1/farmers` | Register a farmer. Nalgonda is enforced. |
| `POST` | `/api/v1/calls/start` | Begin consented browser/phone conversation state. |
| `POST` | `/api/v1/calls/message` | Send Telugu text and receive one next question or acknowledgement. |
| `POST` | `/api/v1/calls/audio` | Mock fallback endpoint; does not claim transcription. |
| `POST` | `/api/v1/calls/end` | Stop a local conversation session. |
| `POST` | `/api/v1/cases` | Create a validated cotton/Nalgonda case for the signed-in farmer. |
| `POST` | `/api/v1/cases/{case_id}/photos` | Upload a JPG/PNG/WebP crop photo (max 5 MB) with the browser’s `X-Case-Access-Token`. |
| `GET` | `/api/v1/cases/{case_id}/photos/{filename}` | View a photo as an authenticated expert. Upload files are not publicly served. |
| `POST` | `/api/v1/cases/{case_id}/feedback` | Record `IMPROVED`, `UNCHANGED`, or `WORSENED` with the farmer session or the random case access token; worsened automatically escalates. |
| `GET` | `/api/v1/knowledge` | View clearly-labelled bundled demonstration guidance. |
| `POST` | `/api/v1/telephony/incoming` | Invoke the mock provider-neutral inbound-call flow. |

## Expert endpoints

Call `POST /api/v1/auth/login` first, then send `Authorization: Bearer <access_token>`.

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` | `/api/v1/dashboard/summary` | Dashboard counters and pending follow-ups. |
| `GET` | `/api/v1/cases` | Search/filter cases with `case_status`, `severity`, `village`, `mandal`, `search`. |
| `GET` | `/api/v1/cases/{case_id}` | Farmer details, conversation case history, actions, and follow-ups. |
| `PATCH` | `/api/v1/cases/{case_id}/status` | Set case status and optionally action/outcome text. |
| `POST` | `/api/v1/cases/{case_id}/assign` | Assign an active expert. |
| `POST` | `/api/v1/cases/{case_id}/notes` | Store expert note or verified recommendation. |
| `POST` | `/api/v1/cases/{case_id}/followups` | Schedule a follow-up. |

## Scope and safety behaviour

- `district` must equal `Nalgonda`; the backend rejects any other district.
- `crop` must equal `cotton` (or `పత్తి`); the backend rejects any other crop.
- The demonstrated conversation never calls a diagnosis confirmed and does not propose pesticides, active ingredients, or application rates.
- Bundled knowledge records are demonstration-only and have `expert_approved: false`.
- Expert case data requires a signed bearer token.

## Farmer and worker authentication

| Method | Endpoint | Use |
| --- | --- | --- |
| `POST` | `/api/v1/auth/market/register` | Create a farmer or worker account using `account_type`, `username`, and `password`. |
| `POST` | `/api/v1/auth/market/login` | Sign in with an existing username and password. |

Passwords must be at least 8 characters and are stored as bcrypt hashes. Usernames are case-insensitive and unique within each account type. An optional `phone` registration field is for marketplace contact features only, not authentication.

Use the token in `Authorization: Bearer <token>`. Farmer and worker tokens cannot be used interchangeably or to call expert endpoints.

## Farmer dashboard

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` | `/api/v1/market/farmer/profile` | Read the authenticated farmer's profile. |
| `PATCH` | `/api/v1/market/farmer/profile` | Update name, village, mandal, language, and optional coordinates. |
| `GET` | `/api/v1/market/farmer/cases` | List only the signed-in farmer's crop cases. Cases started in the assistant while signed in are associated with that farmer. |
| `POST` | `/api/v1/market/jobs` | Create a dated, wage-based job with a requested worker count. |
| `GET` | `/api/v1/market/jobs/mine` | Retrieve the farmer's jobs. |
| `GET` | `/api/v1/market/workers/nearby` | Find available, located workers within a 1–100 km radius. Phone numbers are not returned. |
| `POST` | `/api/v1/market/jobs/{job_id}/workers/{worker_id}/book` | Book an available worker for an open job at its posted wage. The worker must confirm before contact details are shared. |
| `GET` | `/api/v1/market/jobs/{job_id}/applications` | Review applications and negotiated wages for an owned job. |
| `PATCH` | `/api/v1/market/farmer/applications/{application_id}/offer` | Counter a worker's wage offer. |
| `POST` | `/api/v1/market/farmer/applications/{application_id}/accept` | Reserve positions and create pending bookings at the current agreed wage. |
| `GET` | `/api/v1/market/farmer/bookings` | View the farmer's bookings; worker phone numbers are included only after worker confirmation. |
| `POST` | `/api/v1/market/farmer/bookings/{booking_id}/cancel` | Cancel an active booking. |

## Worker marketplace

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` / `PATCH` | `/api/v1/market/worker/profile` | Read or update worker profile, location, skills, availability, and expected wage. |
| `GET` | `/api/v1/market/jobs/nearby` | Return open future jobs ranked by Haversine distance. Requires worker coordinates. |
| `POST` | `/api/v1/market/jobs/{job_id}/applications` | Apply individually or as a worker-led team with a wage proposal. |
| `GET` | `/api/v1/market/worker/applications` | List the signed-in worker's applications. |
| `PATCH` | `/api/v1/market/worker/applications/{application_id}/offer` | Counter the farmer's wage proposal. |
| `POST` / `GET` | `/api/v1/market/teams` | Create a team or list teams the worker belongs to. |
| `POST` | `/api/v1/market/teams/{team_id}/members` | Add a registered worker by phone number (team leader only). |
| `DELETE` | `/api/v1/market/teams/{team_id}/members/{worker_id}` | Remove an available team member (team leader only). |
| `GET` | `/api/v1/market/worker/bookings` | List bookings for the signed-in worker. |
| `POST` | `/api/v1/market/worker/bookings/{booking_id}/confirm` | Confirm a pending booking. |
| `POST` | `/api/v1/market/worker/bookings/{booking_id}/cancel` | Cancel an active booking. |

Active pending and confirmed bookings have a unique database constraint per worker and work date. Group applications reserve all team members together when accepted; each member confirms their own booking. Contact phone numbers are withheld until that worker confirms.

## Database configuration

SQLite is the default local database. To connect Supabase Postgres, set `SUPABASE_DATABASE_URL` to the project's PostgreSQL URI (with TLS enabled); it takes precedence over `DATABASE_URL`. The API creates missing tables and includes a small compatibility migration, but no live Supabase credentials are available in this workspace to verify connectivity.
