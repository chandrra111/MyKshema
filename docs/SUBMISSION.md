# BUILD 2036 submission pack

> Prepared values only. **Do not submit without explicit approval.**

## 1. Prototype brief

MyKshema is an AI-powered personal health intelligence platform that creates a unified, lifelong medical record for every individual. Patients can securely upload prescriptions, laboratory reports, diagnostic scans and discharge summaries, which AI converts into structured, chronological health records. Authorized doctors can access a consolidated patient history, review previous diagnoses, medications, allergies and treatment patterns, and make informed clinical decisions. The platform uses AI to summarize medical history, identify potential medication duplications and interactions, track health trends and highlight preventive-care opportunities for clinical review. With secure, consent-based record sharing, intelligent health analytics and a doctor-centric dashboard, MyKshema transforms fragmented medical information into connected, accessible and preventive healthcare.

_Prototype note for judges:_ the working prototype uses synthetic data, local JSON storage and a deterministic, clearly labelled demo mode for AI features when no OpenAI key is configured. Document extraction in the prototype is rule-based on PDF text, plus a manual-review flow for images.

## 2. Technology stack (implemented only)

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS 3, Recharts, Lucide icons
- **Backend:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, pypdf (PDF text), httpx
- **Storage:** local JSON-file repository adapter (atomic writes) + browser localStorage; repository interface ready for PostgreSQL
- **Security:** PBKDF2 password hashing, HMAC-signed tokens, server-side consent/role checks, audit log, upload validation
- **AI:** deterministic grounded assistant (demo mode); optional OpenAI Chat Completions integration via `OPENAI_API_KEY` (implemented, not exercised in this build)
- **Testing:** pytest (23 tests), TypeScript type-check, Next.js production build

## 3. GitHub URL

https://github.com/chandrra111/MyKshema (public, `main` branch)

## 4. Demo video

Script and screen-recording sequence: [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Video: _to be recorded from the running app._

## 5. Deployed URL

_None yet._ Add only after deploying and testing.

## 6. Ten-slide deck (16:9) – content

1. **Vision**: "Your Health. Your History. Your Well-being." One lifelong, patient-controlled health record for every Indian.
2. **Problem**: Records scattered across paper, PDFs and phone photos; repeated tests; doctors decide with partial history; medication duplication and interactions go unseen when several doctors prescribe.
3. **Solution**: MyKshema: Health Vault → document intelligence → unified timeline → analytics → consent-based doctor sharing, with an AI assistant on top.
4. **Patient and doctor experience**: patient overview, vault, timeline, Doctor Connect · doctor dashboard, scoped record, AI clinical summary, consultation entry.
5. **AI document intelligence**: upload → validate → extract fields with confidence → human review → structured record with source links. Never treats uncertain extraction as fact.
6. **Medication intelligence and preventive analytics**: duplicate-therapy, interaction and allergy flags for clinician review; HbA1c/BP/lipid trends with documented ranges; follow-up and screening prompts. No disease predictions.
7. **Architecture**: Next.js ↔ FastAPI; services for access, extraction, medication review, analytics, AI; repository boundary (JSON today → PostgreSQL + object storage next); audit log.
8. **Working prototype**: real screenshots (overview, extraction review, doctor summary, consent/revoke) + test results (23 pytest, build passing).
9. **Impact and scalability**: fewer repeated tests, safer prescribing, continuity of care across providers; scaling path: managed DB, object storage, IdP, ABDM interoperability, DPDP-aligned consent.
10. **Roadmap**: OCR/vision extraction, FHIR/ABDM integration, verified doctor identity, clinical knowledge-base for interactions, multilingual assistant, clinical validation pilots.

Deck file: build from the official *Build 2036 Prototype Submission Deck Template* and export to PDF under 5 MB (pending).

## 7. Form values (draft, not submitted)

| Field | Value |
|---|---|
| Project name | MyKshema |
| Tagline | Your Health. Your History. Your Well-being. |
| Challenge | BUILD 2036 – Health, Longevity & Biotechnology |
| Short description | AI-powered personal health intelligence: a unified, consent-based lifelong health record with document intelligence, medication-review flags and health trends. |
| Brief | Section 1 |
| Tech stack | Section 2 |
| GitHub | https://github.com/chandrra111/MyKshema |
| Demo video | _pending recording_ |
| Deployed URL | _pending deployment_ |
| Deck | _pending PDF export_ |
