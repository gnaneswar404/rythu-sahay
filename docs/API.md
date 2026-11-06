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
| `POST` | `/api/v1/cases/{case_id}/feedback` | Record `IMPROVED`, `UNCHANGED`, or `WORSENED` with the farmer session or the random case access token; worsened marks the case as escalated. |
| `GET` | `/api/v1/knowledge` | View clearly-labelled bundled demonstration guidance. |
| `POST` | `/api/v1/telephony/incoming` | Invoke the mock provider-neutral inbound-call flow. |

## Scope and safety behaviour

- `district` must equal `Nalgonda`; the backend rejects any other district.
- `crop` must equal `cotton` (or `పత్తి`); the backend rejects any other crop.
- The demonstrated conversation never calls a diagnosis confirmed and does not propose pesticides, active ingredients, or application rates.
- Bundled knowledge records are demonstration-only and are not verified treatment instructions.
- The API does not provide expert sign-in or case-management endpoints. Farmers should consult a local agricultural officer for advice.

## Farmer and worker authentication

| Method | Endpoint | Use |
| --- | --- | --- |
| `POST` | `/api/v1/auth/market/register` | Create a farmer or worker account using `account_type`, `username`, and `password`. |
| `POST` | `/api/v1/auth/market/login` | Sign in with an existing username and password. |

Passwords must be at least 8 characters and are stored as bcrypt hashes. Usernames are case-insensitive and unique within each account type. An optional `phone` registration field is for marketplace contact features only, not authentication.

Use the token in `Authorization: Bearer <access_token>`. Farmer and worker tokens cannot be used interchangeably.

## Public marketplace

These read-only listings and public profiles are available before sign-in. Public profiles expose village/mandal only; phone numbers are included only when the account owner has enabled phone-contact consent. Exact coordinates are not returned publicly.

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` | `/api/v1/market/public/jobs?search={term}` | Search open upcoming work by title, details, location, or recruiter name. |
| `GET` | `/api/v1/market/public/workers?search={term}` | Search available workers by name, skills, or location. |
| `GET` | `/api/v1/market/public/profiles/{account_type}/{id}` | View a farmer/recruiter or worker profile; phone is returned only with that account's explicit contact consent. |
| `GET` | `/api/v1/market/public/profile-photos/{account_type}/{id}` | View a profile photo shown with public listings (`account_type` is `farmer` or `worker`). |

Recruiting a worker requires a farmer account. Applying for a job requires a worker account. Listing responses do not include phone numbers or exact coordinates. A public profile includes a phone number only when its owner has opted into contact sharing; exact coordinates are never public.

## Farmer dashboard

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` | `/api/v1/market/farmer/profile` | Read the authenticated farmer's profile. |
| `PATCH` | `/api/v1/market/farmer/profile` | Update profile, optional coordinates, language, and `allow_phone_contact` consent. Omitted fields are left unchanged. |
| `POST` / `DELETE` | `/api/v1/market/farmer/profile/photo` | Upload or remove the signed-in farmer's JPEG, PNG, or WebP profile photo (maximum 3 MB). |
| `GET` | `/api/v1/market/farmer/cases` | List only the signed-in farmer's crop cases. Conversation API cases created while signed in are associated with that farmer. |
| `POST` | `/api/v1/market/jobs` | Create a dated, wage-based job with a requested worker count. |
| `GET` | `/api/v1/market/jobs/mine` | Retrieve the farmer's jobs. |
| `GET` | `/api/v1/market/workers/nearby?radius_km={5|10|20}` | Find available workers near open work sites; uses Haversine distance where both coordinates exist and same-village fallback otherwise. Results prioritize same village, matching skills, and wage compatibility. Phone numbers are not returned. |
| `POST` | `/api/v1/market/jobs/{job_id}/workers/{worker_id}/book` | Book an available worker for an open job at its posted wage. The worker must confirm before contact details are shared. |
| `GET` | `/api/v1/market/jobs/{job_id}/applications` | Review applications and negotiated wages for an owned job. |
| `PATCH` | `/api/v1/market/farmer/applications/{application_id}/offer` | Counter a worker's wage offer. |
| `POST` | `/api/v1/market/farmer/applications/{application_id}/accept` | Reserve positions and create pending bookings at the current agreed wage. |
| `GET` | `/api/v1/market/farmer/bookings` | View the farmer's bookings; worker phone numbers are included only after worker confirmation. |
| `POST` | `/api/v1/market/farmer/bookings/{booking_id}/cancel` | Cancel an active booking. |
| `POST` | `/api/v1/market/farmer/bookings/{booking_id}/report-absence` | Mark a confirmed absent worker and reopen the job position when capacity allows. |
| `GET` | `/api/v1/market/farmer/bookings/{booking_id}/replacements?radius_km={n}` | Find available, unbooked replacement workers for the work date; returns a phone number only if the worker opted in. |
| `GET` / `POST` | `/api/v1/market/farmer/bookings/{booking_id}/messages` | Read or send messages with a worker who is part of the farmer's booking. |

## Worker marketplace

| Method | Endpoint | Use |
| --- | --- | --- |
| `GET` / `PATCH` | `/api/v1/market/worker/profile` | Read or update worker profile, location, skills, availability, expected wage, and `allow_phone_contact` consent. Omitted fields are left unchanged. |
| `POST` / `DELETE` | `/api/v1/market/worker/profile/photo` | Upload or remove the signed-in worker's JPEG, PNG, or WebP profile photo (maximum 3 MB). |
| `GET` | `/api/v1/market/jobs/nearby?radius_km={5|10|20}` | Return open future jobs ranked by same village, skill/wage compatibility, then Haversine distance. Uses same-village fallback if GPS coordinates are unavailable. |
| `POST` | `/api/v1/market/jobs/{job_id}/applications` | Apply individually or as a worker-led team with a wage proposal. |
| `GET` | `/api/v1/market/worker/applications` | List the signed-in worker's applications. |
| `PATCH` | `/api/v1/market/worker/applications/{application_id}/offer` | Counter the farmer's wage proposal. |
| `POST` / `GET` | `/api/v1/market/teams` | Create a team or list teams the worker belongs to. |
| `POST` | `/api/v1/market/teams/{team_id}/members` | Add a registered worker by case-insensitive login `username` (team leader only). |
| `DELETE` | `/api/v1/market/teams/{team_id}/members/{worker_id}` | Remove an available team member (team leader only). |
| `GET` | `/api/v1/market/worker/bookings` | List bookings for the signed-in worker. |
| `POST` | `/api/v1/market/worker/bookings/{booking_id}/confirm` | Confirm a pending booking. |
| `POST` | `/api/v1/market/worker/bookings/{booking_id}/cancel` | Cancel an active booking. |
| `GET` / `POST` | `/api/v1/market/worker/bookings/{booking_id}/messages` | Read or send messages with the farmer who booked the signed-in worker. |

Active pending and confirmed bookings have a unique database constraint per worker and work date. Group applications reserve all team members together when accepted; each member confirms their own booking. Phone numbers are shared only after booking confirmation and each account's explicit phone-contact consent. Public profiles do not disclose exact coordinates.

## Database configuration

SQLite is the default local database. To connect Supabase Postgres, set `SUPABASE_DATABASE_URL` to the project's PostgreSQL URI (with TLS enabled); it takes precedence over `DATABASE_URL`. The API creates missing tables and includes a small compatibility migration, but no live Supabase credentials are available in this workspace to verify connectivity.

Existing databases receive additive `allow_phone_contact` columns with a private-by-default value; no existing rows or tables are deleted. Legacy expert account rows and case-assignment columns are left untouched but are no longer mapped, read, or exposed by the API.
