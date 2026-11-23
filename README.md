# MyKshema

**Your Health. Your History. Your Well-being.**
AI-powered personal health intelligence. Built for BUILD 2036 (Health, Longevity & Biotechnology).

MyKshema turns scattered prescriptions, lab reports, scans and consultation notes into one structured, lifelong health record. Patients review their timeline, track trends and choose which doctors can see which parts of their record, for how long. Authorised doctors get a consolidated history, an AI-assisted summary and medication-review flags to check.

> **Hackathon prototype.** All people, doctors, hospitals and results are **synthetic/fictional**. This is not a medical device, is not clinically validated and does not replace professional medical advice. Local JSON storage is for demonstration only and is **not suitable for real patient data**.

---

## What runs today

| Area | Status |
|---|---|
| Runs with **no database** and **no OpenAI key** | ✅ Local JSON files + deterministic AI labelled `DEMO MODE – NOT LIVE AI` |
| Demo login (patient and doctor) | ✅ PBKDF2-hashed passwords, signed bearer tokens |
| Health Vault: PDF/JPG/PNG upload, validation, search, filters, preview, download, delete | ✅ Files stored privately and served only through authenticated, consent-checked API calls |
| Document intelligence | ✅ Rule-based extraction from PDF text (no OCR). Images: manual-review flow. Optional live AI extraction if a key is set. Nothing is saved until the user reviews and confirms. |
| Unified medical history timeline with filters and source-document links | ✅ |
| Medication intelligence: statuses, history, adherence, review flags | ✅ Duplicates, curated known interactions, allergy conflicts, missing details. Every flag needs clinician review. |
| Health analytics: trends, reference ranges, reminders | ✅ Reference bands only where documented. Descriptive trend with 95% CI. No forecasts. |
| AI Health Assistant (patient and doctor) | ✅ Grounded answers with citations. Says so when data is missing. |
| Doctor Connect: directory, requests, scoped and time-limited grants, revoke, audit log | ✅ Simulated consent, enforced server-side |
| Consultations with doctor-authored proposed prescriptions | ✅ Clearly labelled demo records. AI never writes prescriptions. |
| Tests | ✅ 23 backend tests (pytest), TypeScript check, Next.js production build |
| Deployment | ⏳ Prepared (Dockerfile, Vercel notes), **not deployed** |

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the detailed checklist.

**Demo recording:** [docs/submission/my_kshema_demo.mp4](https://github.com/chandrra111/MyKshema/blob/main/docs/submission/my_kshema_demo.mp4)

## Quick start (local)

Requires Python 3.11+ and Node 18.18+ (tested with Python 3.12.5 and Node 24). No database, no API keys.

**Backend** (http://localhost:8000, API docs at `/docs`):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Synthetic demo data seeds itself on first start into `backend/data/` (JSON) and `backend/uploads/` (PDFs).

**Frontend** (http://localhost:3000):

```powershell
cd frontend
npm install        # PowerShell blocks this? use npm.cmd install
npm run dev        # or npm.cmd run dev
```

Set `NEXT_PUBLIC_API_URL` (see `frontend/.env.example`) if the API is not at `http://localhost:8000`.

### Windows one-click start

Double-click **`scripts\start-all.cmd`**. It opens the API and the web app in two windows, then your browser at http://localhost:3000. Individual helpers: `scripts\run-backend.cmd`, `scripts\run-frontend.cmd`, `scripts\reset-demo-data.cmd` (each server script takes an optional port, e.g. `run-backend.cmd 8001`).

> **"running scripts is disabled on this system"?** Many Windows machines block PowerShell `.ps1` scripts, and that includes `npm` itself when typed in PowerShell. Use the `.cmd` helpers above, or type `npm.cmd` instead of `npm` (for example `npm.cmd run dev`). No security setting needs changing. The `.ps1` helpers in `scripts\` are for machines that allow them.

### Demo accounts (all fictional, password `Demo@2036`)

| Role | Email | What to show |
|---|---|---|
| Patient | `ananya.rao@demo.mykshema.test` | 2 years of history: type 2 diabetes, hypertension, dyslipidaemia, penicillin allergy |
| Patient | `rahul.menon@demo.mykshema.test` | Smaller asthma record |
| Doctor | `meera.iyer@demo.mykshema.test` | Endocrinologist with active consent from Ananya |
| Doctor | `arjun.shah@demo.mykshema.test` | Cardiologist with a **pending** request: approve it as Ananya |
| Doctor | `kavya.nair@demo.mykshema.test` | GP with access to Rahul; expired grant for Ananya |

Sample files to upload are in [`sample-data/`](sample-data): a lab-report PDF, a prescription PDF (dd/mm/yyyy date) and a PNG "scan" that shows the no-OCR manual-review path.

### Reset demo data

```powershell
cd backend
.\.venv\Scripts\python -m scripts.reset_demo_data
```

Or use **Profile & Settings → Reset demo data** in the app.

### Optional live AI

Copy `backend/.env.example` to `backend/.env` and set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`). The assistant, summaries and document extraction then call the model with only the authorised records as context. They fall back to the deterministic demo answer on any error. Live AI has **not been tested** in this build because no key was available.

## Tests

```powershell
cd backend; .\.venv\Scripts\python -m pytest -q
cd frontend; npm run typecheck; npm run build
```

## Repository layout

```
backend/        FastAPI app (app/), tests, seed/reset scripts
  app/storage/  Repository interface + JSON-file and in-memory adapters (PostgreSQL-ready boundary)
  app/services/ access control, extraction, medication review, analytics, AI, audit
  app/routers/  REST endpoints
frontend/       Next.js 15 + React 19 + TypeScript + Tailwind + Recharts + Lucide
docs/           architecture, API, security, PostgreSQL migration, deployment, demo script, submission
sample-data/    fictional documents for the upload demo
scripts/        run/reset helpers
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md) (live OpenAPI at `http://localhost:8000/docs`)
- [Security, privacy and safety](docs/SECURITY.md)
- [Future PostgreSQL migration plan](docs/POSTGRES_MIGRATION.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Demo video script](docs/DEMO_SCRIPT.md)
- [BUILD 2036 submission pack](docs/SUBMISSION.md)

## Technology actually used

Next.js 15, React 19, TypeScript, Tailwind CSS 3, Recharts, Lucide icons · Python 3.12, FastAPI, Pydantic v2, Uvicorn, pypdf, httpx · local JSON-file storage and browser localStorage · pytest. The OpenAI API is supported via environment variable but optional and untested here.
