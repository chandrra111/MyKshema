"""Trend analytics over recorded observations. Descriptive only: no disease
prediction. A trend slope is reported only with >= 5 points, with a 95%
confidence interval, and is never extrapolated into a forecast."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

from .. import models as m
from .records import PatientBundle, range_status

DISPLAY_ORDER = ["hba1c", "fasting_glucose", "bp_systolic", "bp_diastolic", "ldl", "total_cholesterol", "hdl",
                 "triglycerides", "weight", "bmi", "heart_rate", "creatinine", "egfr", "urine_acr", "vitamin_d", "tsh"]


def _slope_ci(points: list[tuple[date, float]]) -> dict | None:
    if len(points) < 5:
        return None
    t0 = points[0][0]
    xs = [(d - t0).days / 30.44 for d, _ in points]  # months
    ys = [v for _, v in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r * r for r in resid) / (n - 2) / sxx) if n > 2 else float("nan")
    t_crit = {3: 12.71, 4: 4.30, 5: 3.18, 6: 2.78, 7: 2.57, 8: 2.45, 9: 2.36, 10: 2.31, 11: 2.26, 12: 2.23}.get(n, 2.0)
    return {
        "per_month": round(slope, 4),
        "ci95_low": round(slope - t_crit * se, 4),
        "ci95_high": round(slope + t_crit * se, 4),
        "n_points": n,
        "method": "Ordinary least squares on recorded values; descriptive trend only, not a forecast.",
    }


def trends(b: PatientBundle) -> list[dict]:
    by_code: dict[str, list[m.Observation]] = defaultdict(list)
    for o in b.observations:
        by_code[o.code].append(o)
    out = []
    for code, obs in by_code.items():
        obs.sort(key=lambda o: o.observed_on)
        latest = obs[-1]
        prev = obs[-2] if len(obs) > 1 else None
        out.append({
            "code": code, "name": latest.name, "unit": latest.unit, "panel": latest.panel,
            "points": [{"date": o.observed_on.isoformat(), "value": o.value, "status": range_status(o),
                        "source_document_id": o.source_document_id, "source_label": o.source_label} for o in obs],
            "latest": {"date": latest.observed_on.isoformat(), "value": latest.value, "status": range_status(latest)},
            "previous": {"date": prev.observed_on.isoformat(), "value": prev.value} if prev else None,
            "change": round(latest.value - prev.value, 2) if prev else None,
            "reference": {"low": latest.reference_low, "high": latest.reference_high, "text": latest.reference_text}
            if latest.reference_text else None,
            "trend": _slope_ci([(o.observed_on, o.value) for o in obs]),
        })
    out.sort(key=lambda t: DISPLAY_ORDER.index(t["code"]) if t["code"] in DISPLAY_ORDER else 99)
    return out


def reminders(b: PatientBundle, today: date | None = None) -> list[dict]:
    """Follow-ups and preventive-care prompts derived from recorded data only."""
    today = today or date.today()
    out: list[dict] = []
    for c in b.consultations:
        if c.follow_up_date and c.follow_up_date >= today:
            out.append({"kind": "follow_up", "priority": "high", "due": c.follow_up_date.isoformat(),
                        "title": f"Follow-up with {c.doctor_name}", "detail": c.follow_up or "Scheduled follow-up",
                        "basis": f"Consultation on {c.consultation_date.isoformat()}"})
    conditions = {c.name.lower() for c in b.conditions if c.status == "active"}
    diabetic = any("diabetes" in c for c in conditions)
    last = {}
    for o in b.observations:
        last[o.code] = max(last.get(o.code, o.observed_on), o.observed_on)

    def due(code: str, every_days: int, title: str, why: str) -> None:
        when = last.get(code)
        if when is None:
            out.append({"kind": "preventive", "priority": "medium", "due": today.isoformat(), "title": title,
                        "detail": f"No {title.lower()} result recorded.", "basis": why})
        elif (today - when).days > every_days:
            out.append({"kind": "preventive", "priority": "medium",
                        "due": (when + timedelta(days=every_days)).isoformat(), "title": title,
                        "detail": f"Last recorded {when.isoformat()} ({(today - when).days} days ago).", "basis": why})

    if b.observations:
        if diabetic:
            due("hba1c", 90, "HbA1c test", "Recorded diagnosis of diabetes; HbA1c commonly monitored every 3 months")
            due("urine_acr", 365, "Urine albumin/creatinine test", "Annual kidney screening is commonly advised in diabetes")
            due("ldl", 365, "Lipid profile", "Annual lipid review commonly advised in diabetes")
        else:
            due("ldl", 365 * 3, "Lipid profile", "Periodic lipid screening")
    if diabetic:
        eye = [d for d in b.documents if "eye" in (d.title or "").lower() or "retin" in (d.title or "").lower()]
        if not eye:
            out.append({"kind": "preventive", "priority": "medium", "due": today.isoformat(),
                        "title": "Diabetic eye examination",
                        "detail": "No eye examination record found in your vault.",
                        "basis": "Annual diabetic retinopathy screening is commonly advised"})
    vacc = [d for d in b.documents if d.category == "vaccination_record"]
    if b.documents and (not vacc or (today - max(d.document_date or today for d in vacc)).days > 365):
        out.append({"kind": "preventive", "priority": "low", "due": today.isoformat(), "title": "Influenza vaccination",
                    "detail": "No influenza vaccination recorded in the last 12 months.",
                    "basis": "Annual influenza vaccination is commonly advised for adults with chronic conditions"})
    out.sort(key=lambda r: ({"high": 0, "medium": 1, "low": 2}[r["priority"]], r["due"]))
    return out
