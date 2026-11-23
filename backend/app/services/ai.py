"""AI health assistant.

Without OPENAI_API_KEY every answer is generated deterministically from the
caller's authorised records and labelled "DEMO MODE - NOT LIVE AI". With a
key, the model receives the same authorised records as JSON context and must
cite them; on any failure we fall back to the deterministic answer.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import HTTPException, status

from ..config import get_settings
from . import analytics, llm, medication_review
from .records import PatientBundle, range_status

DEMO_LABEL = "DEMO MODE - NOT LIVE AI"
DISCLAIMER = ("Generated from synthetic records for a hackathon prototype. Not medical advice and not a "
              "clinically validated tool. Discuss any decision with a qualified clinician.")


# ---------------------------------------------------------------- rate limit
_calls: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def check_rate_limit(user_id: str) -> None:
    limit = get_settings().ai_rate_limit_per_minute
    now = time.monotonic()
    with _lock:
        q = _calls[user_id]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"AI rate limit: {limit} requests per minute")
        q.append(now)


# ---------------------------------------------------------------- helpers
def _cite(kind: str, rid: str | None, label: str, d: date | str | None = None) -> dict | None:
    if not rid:
        return None
    return {"type": kind, "id": rid, "label": label, "date": d.isoformat() if isinstance(d, date) else d}


def _uniq(cites: list[dict | None]) -> list[dict]:
    seen, out = set(), []
    for c in cites:
        if c and c["id"] not in seen:
            seen.add(c["id"])
            out.append(c)
    return out


def _fmt_status(s: str) -> str:
    return {"above_range": "above documented range", "below_range": "below documented range",
            "within_range": "within documented range", "no_documented_range": "no documented range"}[s]


def _result(answer: str, cites: list, kind: str, mode: str = "demo", extra: dict | None = None) -> dict:
    s = get_settings()
    out = {
        "mode": mode,
        "label": DEMO_LABEL if mode == "demo" else f"Live AI ({s.openai_model}) - verify against cited records",
        "kind": kind,
        "answer": answer,
        "citations": _uniq(cites),
        "disclaimer": DISCLAIMER,
    }
    if extra:
        out.update(extra)
    return out


def _not_shared(b: PatientBundle, scope: str) -> str | None:
    if scope not in b.scopes:
        return f"The patient has not shared their {scope} with you, so I cannot answer this."
    return None


# ---------------------------------------------------------------- deterministic skills
def current_meds(b: PatientBundle):
    return [x for x in b.medications if x.status in ("active", "patient_reported", "proposed")]


def skill_summary(b: PatientBundle, audience: str = "patient") -> dict:
    p = b.profile
    you = "You" if audience == "patient" else p.full_name
    lines = [f"Health summary for {p.full_name} ({b.age} y, {p.sex}, blood group {p.blood_group or 'not recorded'})."]
    cites: list = []
    if "history" in b.scopes:
        active = [c for c in b.conditions if c.status == "active"]
        resolved = [c for c in b.conditions if c.status != "active"]
        if active:
            lines.append("\nActive conditions: " + "; ".join(
                f"{c.name} (since {c.diagnosed_on.isoformat() if c.diagnosed_on else 'date not recorded'}, "
                f"{c.diagnosed_by or 'clinician not recorded'})" for c in active) + ".")
        if resolved:
            lines.append("Resolved / past: " + "; ".join(c.name for c in resolved) + ".")
        if not b.conditions:
            lines.append("\nNo diagnoses are recorded.")
    if "allergies" in b.scopes:
        lines.append("Allergies: " + ("; ".join(f"{a.substance} - {a.reaction or 'reaction not recorded'} "
                                                 f"({a.severity})" for a in b.allergies) if b.allergies
                                      else "none recorded") + ".")
    if "medications" in b.scopes:
        cm = current_meds(b)
        if cm:
            lines.append("\nCurrent medicines (" + str(len(cm)) + "): " + "; ".join(
                f"{x.name}{' ' + x.frequency if x.frequency else ''}"
                f"{' [patient-reported]' if x.status == 'patient_reported' else ''}" for x in cm) + ".")
            cites += [_cite("document", x.source_document_id, b.doc_title(x.source_document_id) or x.name,
                            x.start_date) for x in cm]
    if "labs" in b.scopes and b.observations:
        tr = {t["code"]: t for t in analytics.trends(b)}
        bits = []
        for code in ("hba1c", "fasting_glucose", "ldl", "bp_systolic", "egfr", "weight"):
            t = tr.get(code)
            if not t:
                continue
            first = t["points"][0]
            last = t["latest"]
            bits.append(f"{t['name']} {last['value']:g} {t['unit']} on {last['date']} "
                        f"(first recorded {first['value']:g} on {first['date']}; {_fmt_status(last['status'])})")
            src = t["points"][-1]
            cites.append(_cite("document", src["source_document_id"], src["source_label"] or t["name"], last["date"]))
        if bits:
            lines.append("\nKey measurements: " + "; ".join(bits) + ".")
    if b.consultations:
        c = b.consultations[-1]
        lines.append(f"\nLatest consultation: {c.consultation_date.isoformat()} with {c.doctor_name} - "
                     f"{c.reason or 'visit'}. " + (f"Follow-up: {c.follow_up}." if c.follow_up else ""))
        cites.append(_cite("consultation", c.source_document_id or c.id, f"Consultation {c.consultation_date}",
                           c.consultation_date))
        doctors = sorted({x.doctor_name for x in b.consultations})
        lines.append(f"{you} {'have' if audience == 'patient' else 'has'} seen {len(doctors)} doctor(s): "
                     + ", ".join(doctors) + ".")
    if "medications" in b.scopes:
        flags = [f for f in medication_review.review(b.medications, b.allergies) if f["severity"] in ("high", "moderate")]
        if flags:
            lines.append("\nItems for clinician review: " + "; ".join(f["title"] for f in flags) + ".")
    return _result("\n".join(lines), cites, "history_summary")


def skill_medications(b: PatientBundle) -> dict:
    if msg := _not_shared(b, "medications"):
        return _result(msg, [], "medications")
    groups = {"active": "Prescribed - current", "patient_reported": "Patient-reported - current",
              "proposed": "Proposed in demo consultation", "discontinued": "Discontinued", "completed": "Completed course"}
    lines, cites = [], []
    for st, title in groups.items():
        items = [x for x in b.medications if x.status == st]
        if not items:
            continue
        lines.append(f"{title}:")
        for x in items:
            lines.append(f"  - {x.name}: {x.dosage or 'dose not recorded'}, {x.frequency or 'frequency not recorded'}"
                         f"; started {x.start_date or 'unknown'}" + (f", ended {x.end_date}" if x.end_date else "")
                         + (f"; by {x.prescribed_by}" if x.prescribed_by else ""))
            cites.append(_cite("document", x.source_document_id, b.doc_title(x.source_document_id) or x.name,
                               x.start_date))
    if not lines:
        return _result("No medications are recorded.", [], "medications")
    return _result("Recorded medications:\n" + "\n".join(lines), cites, "medications")


def skill_med_changes(b: PatientBundle) -> dict:
    if msg := _not_shared(b, "medications"):
        return _result(msg, [], "medication_changes")
    if not b.medication_events:
        return _result("No medication changes are recorded.", [], "medication_changes")
    lines = [f"  - {e.event_date}: {e.description}" for e in b.medication_events]
    return _result("Medication changes (oldest first):\n" + "\n".join(lines), [], "medication_changes")


def skill_compare_reports(b: PatientBundle, n: int = 3) -> dict:
    if msg := _not_shared(b, "labs"):
        return _result(msg, [], "compare_reports")
    labs = [o for o in b.observations if o.panel != "Vitals"]
    by_doc: dict[str, list] = defaultdict(list)
    for o in labs:
        by_doc[o.source_document_id or o.observed_on.isoformat()].append(o)
    reports = sorted(by_doc.items(), key=lambda kv: kv[1][0].observed_on)[-n:]
    if not reports:
        return _result("No laboratory reports are recorded.", [], "compare_reports")
    codes: list[str] = []
    for _, obs in reports:
        for o in obs:
            if o.code not in codes:
                codes.append(o.code)
    header = "Test | " + " | ".join(obs[0].observed_on.isoformat() for _, obs in reports)
    rows = [header]
    for code in codes:
        name, unit, cells = code, "", []
        for _, obs in reports:
            o = next((x for x in obs if x.code == code), None)
            if o:
                name, unit = o.name, o.unit
                mark = {"above_range": " (H)", "below_range": " (L)"}.get(range_status(o), "")
                cells.append(f"{o.value:g}{mark}")
            else:
                cells.append("-")
        rows.append(f"{name} ({unit}) | " + " | ".join(cells))
    cites = [_cite("document", k if k.startswith("doc") else None, obs[0].source_label or "Lab report",
                   obs[0].observed_on) for k, obs in reports]
    note = "\n(H)/(L) = above/below the reference range printed on that report."
    return _result(f"Comparison of the last {len(reports)} lab reports:\n" + "\n".join(rows) + note, cites,
                   "compare_reports", extra={"table": {"columns": header.split(" | "),
                                                       "rows": [r.split(" | ") for r in rows[1:]]}})


def skill_trend(b: PatientBundle, code: str) -> dict:
    if msg := _not_shared(b, "labs"):
        return _result(msg, [], "trend")
    t = next((x for x in analytics.trends(b) if x["code"] == code), None)
    if not t:
        return _result(f"No {code.replace('_', ' ')} results are recorded.", [], "trend")
    pts = t["points"]
    lines = [f"{t['name']} ({t['unit']}) - {len(pts)} recorded values:"]
    lines += [f"  - {p['date']}: {p['value']:g} ({_fmt_status(p['status'])})" for p in pts]
    if len(pts) > 1:
        diff = pts[-1]["value"] - pts[0]["value"]
        lines.append(f"Change since first record: {diff:+.2f} {t['unit']}.")
    if t["trend"]:
        tr = t["trend"]
        lines.append(f"Descriptive trend: {tr['per_month'] * 3:+.2f} {t['unit']} per 3 months "
                     f"(95% CI {tr['ci95_low'] * 3:+.2f} to {tr['ci95_high'] * 3:+.2f}; n={tr['n_points']}). "
                     "This describes past values only and is not a prediction.")
    if t["reference"]:
        lines.append(f"Reference range on latest report: {t['reference']['text']}.")
    cites = [_cite("document", p["source_document_id"], p["source_label"] or t["name"], p["date"]) for p in pts]
    return _result("\n".join(lines), cites, "trend", extra={"series": pts, "code": code})


def skill_doctors(b: PatientBundle) -> dict:
    if not b.consultations:
        return _result("No consultations are recorded, so no previous doctors are listed.", [], "doctors")
    seen: dict[str, dict] = {}
    for c in b.consultations:
        d = seen.setdefault(c.doctor_name, {"hospital": c.hospital, "visits": 0, "last": c.consultation_date})
        d["visits"] += 1
        d["last"] = max(d["last"], c.consultation_date)
    lines = [f"  - {name} ({v['hospital'] or 'facility not recorded'}): {v['visits']} visit(s), last on {v['last']}"
             for name, v in sorted(seen.items(), key=lambda kv: kv[1]["last"], reverse=True)]
    return _result("Doctors in the record:\n" + "\n".join(lines), [], "doctors")


def skill_latest_consultation(b: PatientBundle) -> dict:
    if not b.consultations:
        return _result("No consultations are recorded.", [], "latest_consultation")
    c = b.consultations[-1]
    txt = (f"Latest consultation: {c.consultation_date} with {c.doctor_name} at {c.hospital or 'facility not recorded'}.\n"
           f"Reason: {c.reason or 'not recorded'}\nNotes: {c.notes}\n"
           f"Diagnoses: {', '.join(c.diagnoses) or 'none recorded'}\nFollow-up: {c.follow_up or 'none recorded'}")
    return _result(txt, [_cite("document", c.source_document_id, f"Consultation note {c.consultation_date}",
                               c.consultation_date)], "latest_consultation")


def skill_consultations(b: PatientBundle) -> dict:
    if not b.consultations:
        return _result("No consultations are recorded.", [], "consultations")
    lines = [f"  - {c.consultation_date} | {c.doctor_name}: {c.reason or 'visit'} -> {', '.join(c.diagnoses) or 'no diagnosis recorded'}"
             for c in b.consultations]
    return _result(f"{len(b.consultations)} consultations recorded:\n" + "\n".join(lines),
                   [_cite("document", c.source_document_id, f"Consultation {c.consultation_date}", c.consultation_date)
                    for c in b.consultations[-5:]], "consultations")


def skill_med_review(b: PatientBundle) -> dict:
    if msg := _not_shared(b, "medications"):
        return _result(msg, [], "medication_review", extra={"flags": []})
    flags = medication_review.review(b.medications, b.allergies)
    if not flags:
        txt = "No duplicate, interaction, allergy or missing-detail flags were found in the recorded data."
    else:
        txt = (f"{len(flags)} item(s) flagged for clinician review (rule-based, from recorded data and a curated "
               "demo reference table):\n" + "\n".join(f"  - [{f['severity'].upper()}] {f['title']}: {f['detail']}"
                                                      for f in flags)
               + "\nMyKshema never changes medicines. A qualified clinician must review each flag.")
    return _result(txt, [], "medication_review", extra={"flags": flags})


def skill_allergies(b: PatientBundle) -> dict:
    if msg := _not_shared(b, "allergies"):
        return _result(msg, [], "allergies")
    if not b.allergies:
        return _result("No allergies are recorded.", [], "allergies")
    return _result("Recorded allergies:\n" + "\n".join(
        f"  - {a.substance}: {a.reaction or 'reaction not recorded'} ({a.severity}), recorded {a.recorded_on}"
        for a in b.allergies), [], "allergies")


def skill_insights(b: PatientBundle) -> dict:
    if msg := _not_shared(b, "labs"):
        return _result(msg, [], "health_insights", extra={"insights": []})
    insights = []
    for t in analytics.trends(b):
        last = t["latest"]
        if t["previous"] and t["change"] is not None:
            direction = "up" if t["change"] > 0 else "down" if t["change"] < 0 else "unchanged"
            insights.append({
                "code": t["code"], "title": f"{t['name']}: {last['value']:g} {t['unit']}",
                "detail": f"{direction} {abs(t['change']):g} {t['unit']} since {t['previous']['date']}; "
                          f"{_fmt_status(last['status'])}.",
                "status": last["status"],
            })
    rem = analytics.reminders(b)
    txt = "Observations from your recorded measurements:\n" + "\n".join(f"  - {i['title']} - {i['detail']}"
                                                                         for i in insights[:8])
    if rem:
        txt += "\n\nReminders and preventive-care prompts:\n" + "\n".join(f"  - {r['title']}: {r['detail']}" for r in rem)
    txt += "\n\nThese are descriptive observations, not diagnoses or predictions."
    return _result(txt, [], "health_insights", extra={"insights": insights, "reminders": rem})


INTENTS: list[tuple[str, list[str]]] = [
    ("med_review", ["duplicate", "interaction", "medication review", "review medication", "flag", "conflict"]),
    ("med_changes", ["medication change", "changes in medication", "medicine change", "dose change", "changed"]),
    ("compare", ["compare", "last three", "last 3", "comparison"]),
    ("trend_hba1c", ["hba1c", "a1c", "sugar trend", "glycated"]),
    ("trend_glucose", ["glucose", "sugar"]),
    ("trend_bp", ["blood pressure", " bp", "bp ", "hypertension"]),
    ("trend_ldl", ["ldl", "cholesterol", "lipid"]),
    ("trend_weight", ["weight", "bmi"]),
    ("trend_egfr", ["kidney", "egfr", "creatinine"]),
    ("latest_consult", ["latest consultation", "last consultation", "last visit", "recent visit", "latest visit"]),
    ("consultations", ["consultations", "visits"]),
    ("doctors", ["doctor", "physician", "specialist"]),
    ("allergies", ["allerg"]),
    ("medications", ["medication", "medicine", "drug", "tablet", "prescri", "pill"]),
    ("insights", ["insight", "remind", "preventive", "screening", "due"]),
    ("summary", ["summar", "history", "overview", "about me", "health record"]),
]


def detect_intent(question: str) -> str | None:
    q = f" {question.lower()} "
    for intent, kws in INTENTS:
        if any(k in q for k in kws):
            return intent
    return None


def deterministic_answer(question: str, b: PatientBundle, audience: str) -> dict:
    intent = detect_intent(question)
    match intent:
        case "med_review": return skill_med_review(b)
        case "med_changes": return skill_med_changes(b)
        case "compare": return skill_compare_reports(b)
        case "trend_hba1c": return skill_trend(b, "hba1c")
        case "trend_glucose": return skill_trend(b, "fasting_glucose")
        case "trend_bp":
            r = skill_trend(b, "bp_systolic")
            d = skill_trend(b, "bp_diastolic")
            r["answer"] += "\n\n" + d["answer"]
            return r
        case "trend_ldl": return skill_trend(b, "ldl")
        case "trend_weight": return skill_trend(b, "weight")
        case "trend_egfr": return skill_trend(b, "egfr")
        case "latest_consult": return skill_latest_consultation(b)
        case "consultations": return skill_consultations(b)
        case "doctors": return skill_doctors(b)
        case "allergies": return skill_allergies(b)
        case "medications": return skill_medications(b)
        case "insights": return skill_insights(b)
        case "summary": return skill_summary(b, audience)
    return _result(
        "In demo mode I can answer questions grounded in the record, for example:\n"
        "  - Summarise my history\n  - List my recorded medications\n  - Compare my last three reports\n"
        "  - Show my HbA1c trend\n  - List my previous doctors\n  - Summarise my latest consultation\n"
        "  - Show medication changes\n  - Identify possible duplicate therapies\n"
        "I could not match your question to one of these, and I will not guess.", [], "help")


# ---------------------------------------------------------------- live AI wrapper
def _context_json(b: PatientBundle) -> str:
    def dump(items, limit=200):  # noqa: ANN001
        return [i.model_dump(mode="json", exclude={"is_demo"}) for i in items[-limit:]]

    ctx = {
        "patient": b.profile.model_dump(mode="json", include={"id", "full_name", "date_of_birth", "sex", "blood_group"}),
        "shared_scopes": b.scopes, "conditions": dump(b.conditions), "allergies": dump(b.allergies),
        "medications": dump(b.medications), "medication_events": dump(b.medication_events),
        "observations": dump(b.observations, 150), "consultations": dump(b.consultations),
        "documents": [{"id": d.id, "title": d.title, "category": d.category, "date": str(d.document_date)}
                      for d in b.documents],
    }
    return json.dumps(ctx, default=str)[:60000]


def answer(question: str, b: PatientBundle, audience: str) -> dict:
    """Live AI if configured, otherwise deterministic. Deterministic citations are attached either way."""
    base = deterministic_answer(question, b, audience)
    if not get_settings().live_ai_enabled:
        return base
    who = "the patient themself" if audience == "patient" else "an authorised doctor reviewing this patient"
    content = llm.chat([
        {"role": "system", "content": llm.GROUNDING_RULES + f" You are answering {who}."},
        {"role": "user", "content": f"Records (JSON):\n{_context_json(b)}\n\nQuestion: {question}"},
    ])
    if not content:
        base["answer"] += "\n\n(Live AI was unavailable; this is the deterministic demo answer.)"
        return base
    valid_ids = {d.id for d in b.documents} | {c.id for c in b.consultations}
    cited = [cid for cid in re.findall(r"\[([a-z]{2,4}_[A-Za-z0-9]+)\]", content) if cid in valid_ids]
    extra_cites = [_cite("document", cid, b.doc_title(cid) or cid) for cid in cited]
    out = _result(content, base["citations"] + extra_cites, base["kind"], mode="live")
    for k in ("flags", "table", "series", "insights", "reminders"):
        if k in base:
            out[k] = base[k]
    return out


def summarize(b: PatientBundle, audience: str) -> dict:
    return answer("Summarise this patient's medical history, current medicines, allergies, key lab trends and "
                  "latest consultation.", b, audience) if get_settings().live_ai_enabled else skill_summary(b, audience)
