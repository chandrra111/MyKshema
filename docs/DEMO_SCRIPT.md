# Demo video script (3–4 minutes)

Record the **real running app** (local or deployed). Don't splice in mock screens. Reset first: `scripts\reset-demo-data.ps1`.
Setup: browser at 1440×900, zoom 100%, two windows or profiles (patient / doctor), `sample-data/sample_lab_report_nov2026.pdf` ready.

| Time | Screen | Action | Voice-over (approx.) |
|---|---|---|---|
| 0:00–0:20 | Login page | Show the hero, then click **Ananya Rao · Patient** | "Medical records in India are scattered across paper prescriptions, lab PDFs and WhatsApp photos. MyKshema turns them into one lifelong, patient-controlled health record." |
| 0:20–0:45 | Overview | Point to HbA1c 6.8 %, BP, the pending request banner and the DEMO MODE badge | "Ananya sees her latest results, follow-ups and items for her doctor to review. All data here is synthetic, and without an API key the AI runs in a clearly labelled demo mode." |
| 0:45–1:25 | Health Vault | Drag in `sample_lab_report_nov2026.pdf`, category Blood report → **Upload & extract** → review modal: show confidence badges, edit a value, tick the check → **Confirm & save** | "Uploading a report extracts the date, lab, tests, values and printed reference ranges, each with a confidence score. Nothing becomes part of the record until Ananya reviews and confirms it, and every value links back to its source." |
| 1:25–1:50 | Health Analytics | HbA1c card → chart with shaded documented range; show the new 6.7 % point and the trend CI; open the reminders | "Trends show reference ranges only where the report documented them. The trend is descriptive, with a confidence interval, and there are no disease predictions." |
| 1:50–2:10 | Medications | Show the flags: two statins, ibuprofen + telmisartan, historical penicillin match | "Medication intelligence flags a possible duplicate statin and a known NSAID–ARB interaction for the clinician to review. MyKshema never changes medicines." |
| 2:10–2:35 | Doctor Connect | **Review & approve** Dr. Arjun Shah → untick *Lab results* → 3 days → Approve | "Doctors ask; patients decide exactly what to share and for how long." |
| 2:35–3:15 | Doctor window: Arjun | Dashboard → Ananya → **AI clinical summary** (citations) → Labs tab shows *not shared* → **New consultation** with a proposed Rx → Save | "Dr. Shah gets a consolidated, cited summary, but only of what Ananya shared. Prescriptions are authored by the doctor, never by AI, and are clearly marked as demo records." |
| 3:15–3:40 | Patient window | Doctor Connect → **Revoke** → Access history shows the view and the revoke; doctor window refresh → *Access not available* | "Ananya can revoke at any time. Access ends immediately, and every view and blocked attempt is in her audit log." |
| 3:40–3:55 | Assistant | Ask "Compare my last three reports" | "Ask questions in plain language, answered only from your records. MyKshema: your health, your history, your well-being." |

End card: GitHub URL, "Hackathon prototype · synthetic data · not a medical device".
