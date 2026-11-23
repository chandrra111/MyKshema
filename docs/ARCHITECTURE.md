# Architecture

```
┌──────────────────────────── Browser ─────────────────────────────┐
│ Next.js 15 (React 19, TS, Tailwind, Recharts)                    │
│  /patient/*  /doctor/*   localStorage: token, chat history       │
└───────────────┬──────────────────────────────────────────────────┘
                │ REST + Bearer token (CORS allow-list)
┌───────────────▼─────────────────── FastAPI ──────────────────────┐
│ routers/   auth · patients · documents · medications · analytics │
│            ai · access (doctor connect, audit) · consultations   │
│ security.py   PBKDF2 hashes, HMAC tokens, role dependencies      │
│ services/                                                        │
│   access.py           ownership + consent-scope enforcement      │
│   records.py          scoped patient bundle, timeline builder    │
│   extraction.py       pypdf text → rules │ live AI │ demo review │
│   medication_review   duplicates, curated interactions, allergy  │
│   analytics.py        trends, documented ranges, OLS CI, prompts │
│   ai.py + llm.py      deterministic skills │ optional OpenAI     │
│   audit.py            append-only audit events                   │
│ storage/  Repository[T]  ← DocumentStore protocol                │
│           JsonFileStore (default) │ MemoryStore │ (future) SQL   │
└───────────────┬──────────────────────────────┬───────────────────┘
                │                              │
        backend/data/*.json           backend/uploads/ (private files)
```

## Key design decisions

**Storage boundary.** Routes and services only use `Repos` (typed `Repository[T]` objects). Repositories sit on a tiny `DocumentStore` protocol (`load`, `save`, `collections`, `clear`). The JSON adapter writes atomically (temp file, then `os.replace`) and quarantines corrupt files as `*.corrupt-<ts>.json`. A PostgreSQL adapter can replace it without touching the UI, routes or business logic ([POSTGRES_MIGRATION.md](POSTGRES_MIGRATION.md)).

**Authorisation on the server.** `ensure_patient_access(user, patient_id, scope)` runs on every patient-data route. Patients can read only their own record. Doctors need an active (unrevoked, unexpired) grant that includes the scope. The frontend hides locked tabs for clarity, but enforcement lives in the API. Denied attempts are written to the audit log, which the patient can see.

**Consent model.** `AccessRequest` (doctor- or patient-initiated, pending → approved/denied/cancelled) and `AccessGrant` (scopes ⊆ {history, medications, allergies, labs, documents, consultations}, `expires_at`, `revoked_at`). Approving supersedes any earlier active grant for the same pair.

**Document intelligence pipeline.** Upload → validate (extension, magic bytes, size) → store privately → `Extraction` in `pending_review` with per-field confidence and method label → user edits and confirms → observations, medications, prescriptions, allergies and conditions are created with `source_document_id`. Unconfirmed extractions never reach the record.

**AI grounding.** `PatientBundle` holds only what the caller may see. Deterministic skills (summary, medications, compare reports, trends, doctors, consultations, medication review, insights) produce answers with citations. With `OPENAI_API_KEY`, the same bundle is sent as JSON context under strict grounding rules. Citations are validated against known record IDs, and any failure falls back to the deterministic answer. Every response carries `mode` and `label`.

**Medication safety.** Flags come only from the patient's records plus a curated table that is labelled as such. Severity ranks them; every flag has `requires_clinician_review: true`. The system never creates, changes or stops a prescription. Doctors author proposed prescriptions explicitly (`authored_by: "doctor"`, `status: "proposed_demo"`).

**Analytics honesty.** Reference indicators appear only when the source report documented a range. Trend slopes need at least 5 points, come with a 95% CI and are never extrapolated.

## Data collections

`users, patients, doctors, access_requests, access_grants, documents, extractions, conditions, allergies, medications, medication_events, observations, consultations, prescriptions, ai_summaries, audit_logs` (+ `_meta`).
