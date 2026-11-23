# Future PostgreSQL migration plan

PostgreSQL is **not** used or required today. This plan keeps the change contained to the storage layer.

## Current boundary

- `app/storage/base.py`: `DocumentStore` protocol + generic `Repository[T]` (`all, find, first, get, require, add, add_many, update, delete, replace_all`).
- `app/storage/__init__.py`: `Repos` container and `build_store(settings)`, the single switch point.
- Routes and services never touch files directly; they call `get_repos().<collection>`.

## Steps

1. **Schema.** One table per collection with typed columns matching the Pydantic models. Use `text` IDs (keep the existing `prefix_hex` IDs), `timestamptz`, `date`, `jsonb` for nested lists (`scopes`, `items`, extraction `fields`). Index `patient_id`, `doctor_id`, `(doctor_id, patient_id, expires_at)` on grants, and `timestamp` on audit logs.
2. **Adapter.** Add `app/storage/postgres.py` implementing `SqlRepository[T]` with the same method signatures. Push `find(**equals)` filters into `WHERE` clauses (the JSON adapter filters in memory). Use SQLAlchemy 2.0 Core or psycopg 3 with a connection pool.
3. **Switch.** `MYKSHEMA_STORAGE=postgres` + `DATABASE_URL` → `build_store` returns the SQL repos. The JSON adapter stays for demos and tests.
4. **Migrations.** Alembic, introduced only at this step.
5. **Data move.** One-off script: read each `data/*.json` via `JsonFileStore`, validate with the Pydantic models, bulk-insert. (Demo data only. Never migrate real patient data from local JSON.)
6. **Hardening that comes with it.** Row-level security keyed on patient and grant; append-only audit table (no UPDATE/DELETE grants); encryption at rest; PITR backups; documents moved to private object storage (S3/GCS/Azure Blob with server-side encryption) using short-lived signed URLs issued **after** the consent check.
7. **Tests.** Run the existing pytest suite against both adapters (parametrised fixture).

## What does not change

Pydantic models, API contracts, frontend, access-control logic, AI grounding, extraction and medication-review services.
