# API reference

Interactive OpenAPI docs: `http://localhost:8000/docs` (ReDoc at `/redoc`).
Auth: `Authorization: Bearer <token>` from `POST /api/auth/demo-login`.
Errors: `{"error": {"status": 403, "message": "...", "details": [...]}}`.

Legend: 🧑 patient · 🩺 doctor (needs an active grant covering the scope) · 🔓 public

| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `/health` | 🔓 | storage label, `database: none`, AI mode |
| POST | `/api/auth/demo-login` | 🔓 | `{email, password}` → token + user |
| GET | `/api/auth/me` | 🧑🩺 | |
| GET | `/api/auth/demo-accounts` | 🔓 | fictional accounts |
| GET / PATCH | `/api/patients/me` | 🧑 | profile |
| POST | `/api/patients/me/allergies` | 🧑 | patient-reported allergy |
| GET | `/api/patients/{id}` | 🧑🩺 | includes `shared_scopes` |
| GET | `/api/patients/{id}/history` | 🧑🩺 | consolidated, scope-filtered |
| GET | `/api/patients/{id}/timeline` | 🧑🩺 history | `type, doctor, q, date_from, date_to` |
| GET | `/api/patients/{id}/conditions` · `/allergies` | 🧑🩺 | |
| POST | `/api/documents/upload` | 🧑 | multipart: `file, category, title, document_date, doctor_name, hospital, notes, analyze` |
| GET | `/api/documents` | 🧑🩺 documents | `patient_id, q, category, date_from, date_to, doctor` |
| GET / PATCH / DELETE | `/api/documents/{id}` | 🧑 (GET also 🩺) | |
| GET | `/api/documents/{id}/file` | 🧑🩺 documents | private file stream, `?download=true` |
| POST | `/api/documents/{id}/analyze` | 🧑 | re-run extraction |
| POST | `/api/documents/{id}/confirm-extraction` | 🧑 | reviewed fields → record |
| POST | `/api/documents/{id}/skip-extraction` | 🧑 | keep file only |
| GET | `/api/medications` | 🧑🩺 medications | list + review flags |
| POST | `/api/medications` | 🧑 | self-reported, unverified |
| PATCH | `/api/medications/{id}/adherence` | 🧑 | |
| GET | `/api/medications/history` | 🧑🩺 medications | events |
| GET | `/api/analytics/health-trends` | 🧑🩺 labs | series, ranges, trend CI |
| GET / POST | `/api/analytics/observations` | 🧑🩺 labs / 🧑 | POST logs a home vital |
| GET | `/api/analytics/reminders` | 🧑🩺 | follow-ups + preventive prompts |
| GET | `/api/ai/status` | 🔓 | live vs demo |
| POST | `/api/ai/summarize-history` | 🧑🩺 history | `{patient_id?}` |
| POST | `/api/ai/ask` | 🧑🩺 | `{question, patient_id?}` |
| POST | `/api/ai/medication-review` | 🧑🩺 medications | |
| POST | `/api/ai/health-insights` | 🧑🩺 labs | |
| POST | `/api/ai/analyze-document` | 🧑 | `{document_id}` |
| GET | `/api/doctors` | 🧑🩺 | directory (+ your grant status for patients) |
| GET | `/api/doctor/me` · `/api/doctor/patients` | 🩺 | authorised patients + pending requests |
| GET | `/api/doctor/patient-lookup?email=` | 🩺 | name/city only, audited |
| POST / GET | `/api/access-requests` | 🩺🧑 | create / list |
| POST | `/api/access-requests/{id}/approve` | 🧑 | `{scopes?, duration_hours?}` |
| POST | `/api/access-requests/{id}/deny` · `/cancel` | 🧑 / 🧑🩺 | |
| POST / GET | `/api/access-grants` | 🧑 / 🧑🩺 | direct share / list with state |
| POST | `/api/access-grants/{id}/revoke` | 🧑 | immediate |
| GET | `/api/audit-logs` | 🧑🩺 | patient: events on their record; doctor: own actions |
| POST / GET | `/api/consultations` | 🩺 consultations / 🧑🩺 | doctor-authored proposed Rx |
| POST | `/api/demo/reset` | 🧑🩺 | restore seed (disable with `MYKSHEMA_ALLOW_DEMO_RESET=false`) |

AI endpoints are rate-limited per user (`MYKSHEMA_AI_RATE_LIMIT`, default 20/min). Every AI response includes `mode` (`demo`/`live`), `label`, `citations` and `disclaimer`.
