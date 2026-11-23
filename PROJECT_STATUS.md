# MyKshema – Project Status

_Last updated: 2026-11-23_

## Phase 1 – Inspection (done)

- Local folder `MyApps/MyKshema` held only the master prompt; there was no starter ZIP or source code.
- GitHub `chandrra111/MyKshema` exists, is public and is **empty** (no branches). Nothing to preserve or merge.
- Toolchain: Node 24.20, npm 12, Python 3.12.5, git 2.55. `gh` CLI not installed.
- Built greenfield. Milestone commits on `main`, **pushed to GitHub on 2026-11-23** (https://github.com/chandrra111/MyKshema).

## Completed

### Backend (FastAPI)
- [x] Settings from env; all optional (`backend/.env.example`)
- [x] Repository interface (`app/storage/base.py`) with JSON-file adapter (atomic writes, corrupt-file quarantine) and in-memory adapter
- [x] Typed Pydantic models for users, patient/doctor profiles, access requests/grants, documents, extractions, conditions, allergies, medications + events, observations, consultations, prescriptions, AI summaries, audit logs
- [x] Synthetic seed (2 patients, 5 doctors, about 2 years, 10 consultations, 7 prescriptions, 146 observations, 29 generated PDF documents) + seed/reset scripts
- [x] Demo auth: PBKDF2 hashes, HMAC-signed expiring tokens
- [x] Server-side ownership and consent-scope checks on every patient-data route; denied attempts audited
- [x] Upload validation: extension allow-list, magic-byte check, size limit (10 MB default); private storage; authenticated file endpoint
- [x] Extraction: rule-based PDF text parsing (pypdf), demo manual-review template for images, optional live AI; review → confirm → records with source links and confidence
- [x] Timeline with filters; medication review rules (duplicates, curated interactions, allergy conflicts, missing details, unverified); analytics trends with documented ranges and OLS 95% CI; reminders
- [x] Deterministic AI assistant (16 intents) labelled `DEMO MODE - NOT LIVE AI`; optional OpenAI path with fallback; per-user AI rate limit
- [x] Simulated consent: doctor request, patient approve (narrow scope/duration) / deny, direct share, revoke, expiry; audit history
- [x] Consultations with doctor-authored proposed prescriptions (`proposed_demo`)
- [x] Consistent JSON error format; OpenAPI docs at `/docs`; `/health`; demo reset endpoint

### Frontend (Next.js)
- [x] Design system (navy/teal, cards, badges, modals), responsive shell with 9-item patient nav
- [x] Patient: Overview, Health Vault, Medical History, Medications, Health Analytics, AI Assistant, Doctor Connect, Consultations, Profile & Settings
- [x] Doctor: Dashboard, My Patients, scoped patient record (summary, timeline, medications, labs, documents, consultations, Ask AI), AI assistant, access requests, activity log, profile
- [x] localStorage for session token and per-patient assistant chat history (wrapped in try/catch)

### Docs and submission
- [x] README, architecture, API, security, PostgreSQL migration plan, deployment, demo script, submission pack

## Tested (actual results)

| Check | Result |
|---|---|
| `pytest -q` (backend) | **23 passed** |
| `tsc --noEmit` | **passed** |
| `next build` | **passed** (20 routes) |
| Browser end-to-end (local dev servers) | **passed**: patient login → overview → upload PDF → reviewed extraction (date, doctor, hospital, diagnosis, medication with confidence) → confirm; approved Dr. Shah's request with Labs removed → doctor sees only shared scopes, Labs tab locked, allergies "Not shared" → DEMO MODE clinical summary with citations → doctor consultation saved and labelled → patient revokes → doctor immediately blocked and the attempt audited. Mobile (375 px) has no horizontal scroll. |

## Pending / known limitations

- [ ] **Not deployed.** Deployment files are prepared; no hosted URL exists yet.
- [ ] Live OpenAI path implemented but **untested** (no key available).
- [ ] No OCR engine. Scanned images use the manual-review flow unless live AI vision is configured.
- [ ] Medicines added from a confirmed document are saved as `active` with no drug class, so class-based flags (duplicate class, interactions) don't apply to them until classified. Re-uploading an old prescription re-activates that medicine.
- [ ] Interaction table is a small curated demo subset, not a clinical knowledge base.
- [ ] Demo video and screenshots: to be recorded from the running app (script in `docs/DEMO_SCRIPT.md`).
- [x] 13-slide submission deck built on the official Build 2036 template: `docs/submission/MyKshema_BUILD2036_Deck.pptx`
- [ ] Deck PDF export (PowerPoint could not be automated here; export manually: File → Export → Create PDF)
- [ ] Confirm team name ("MyKshema") and team leader name on the deck's title slide
- [ ] Submission form values are prepared in `docs/SUBMISSION.md` and **not submitted**.

## Blocked

- Hosted deployment: needs a Vercel account and a container host.

## Not production-ready

Production needs a managed database, private object storage with encryption, a hardened identity provider with verified doctor registration, legally reviewed consent (DPDP Act 2023), monitoring, backups and clinical validation. See `docs/SECURITY.md`.
