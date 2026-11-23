# Security, privacy and safety

## What the prototype does

- **Synthetic data only.** Seed data is fictional and marked `is_demo: true`; generated documents carry a "SYNTHETIC DEMO RECORD" banner.
- **Passwords** hashed with PBKDF2-SHA256 (120k iterations, per-user salt). Tokens are HMAC-SHA256 signed with expiry. The secret comes from `MYKSHEMA_TOKEN_SECRET` or a random per-install file in the data dir (git-ignored).
- **No secrets in code.** `OPENAI_API_KEY` comes only from the environment; `.env` is git-ignored.
- **Authorisation on the server** for every patient-data route (ownership for patients, active scoped grant for doctors). Role checks on writes: only patients upload, confirm, revoke; only authorised doctors write consultations.
- **Uploads**: extension allow-list (PDF/JPG/JPEG/PNG), magic-byte sniffing must match the extension, size limit (10 MB default), random server-side filenames, files outside any static path, `Cache-Control: private, no-store`.
- **Audit log** for logins, views, downloads, uploads, extraction confirmations, AI requests, consent changes, consultations and **denied** access attempts. Patients can see the events on their record.
- **AI safety.** Deterministic mode is labelled `DEMO MODE – NOT LIVE AI`. Answers come only from the caller's authorised records; missing data is reported as missing. Live mode uses grounding instructions and validates cited IDs. AI never prescribes or modifies medicines. Medication flags always require clinician review. Analytics make no disease predictions.
- **Per-user rate limit** on AI endpoints. CORS allow-list. Basic security headers on the frontend.

## Why this is not production-safe

| Gap | Production requirement |
|---|---|
| Local JSON files, no encryption at rest, single-process locking | Managed PostgreSQL with RLS, encryption, backups, PITR |
| Local uploads folder (ephemeral on most cloud hosts) | Private object storage, server-side encryption, malware scanning, signed URLs after consent check |
| Demo login, tokens in localStorage, no MFA or revocation list | Hardened IdP (OIDC), MFA, httpOnly cookies, session revocation |
| Doctor identity not verified | Verification against the official medical register (e.g. NMC/state councils) |
| Simulated consent | Legally reviewed consent artefacts; ABDM/HIE-CM-compatible consent manager if integrating with India's digital health stack |
| In-memory rate limit | Gateway-level rate limiting, WAF |
| No monitoring | Centralised logging, alerting, tamper-evident audit storage |

## India – DPDP Act 2023 and healthcare considerations (future design)

Health data is personal data under the Digital Personal Data Protection Act, 2023. A production MyKshema should provide: notice and purpose-specific, freely given consent with easy withdrawal (the grant/revoke model is a starting point); data minimisation (scoped sharing); rights to access, correction and erasure; breach notification to the Data Protection Board and affected users; appropriate security safeguards; and care with children's data (verifiable parental consent). Also consider ABDM health data management policy, Telemedicine Practice Guidelines (for any consultation features), CDSCO software-as-a-medical-device rules if clinical decision-support claims are made, and data-localisation expectations. These need legal review. This prototype claims none of them.

## Clinical disclaimer

MyKshema is a hackathon prototype. It is not a clinically validated medical device and not a substitute for professional medical advice, diagnosis or treatment.
