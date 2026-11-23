"""Document intelligence.

Order of preference:
1. Live AI (OPENAI_API_KEY set): PDF text or image sent to the model for
   structured extraction.
2. PDF with embedded text: deterministic rule-based parsing (pypdf). No OCR.
3. Scanned image / no text: DEMO manual-review template, pre-filled only
   with the metadata the user typed. No clinical values are invented.

Results are always saved as `pending_review`; nothing is treated as verified
until the user confirms (and can correct) every field.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

from .. import models as m
from ..config import get_settings
from . import llm

LAB_ALIASES = {
    "hba1c": ["hba1c", "glycated haemoglobin", "glycated hemoglobin", "a1c"],
    "fasting_glucose": ["fasting blood glucose", "fasting glucose", "fbs", "fbg", "fasting plasma glucose"],
    "total_cholesterol": ["total cholesterol"],
    "ldl": ["ldl cholesterol", "ldl"],
    "hdl": ["hdl cholesterol", "hdl"],
    "triglycerides": ["triglycerides", "tg"],
    "creatinine": ["serum creatinine", "creatinine"],
    "egfr": ["egfr"],
    "vitamin_d": ["vitamin d (25-oh)", "vitamin d", "25-oh vitamin d"],
    "urine_acr": ["urine albumin/creatinine ratio", "urine acr", "uacr"],
    "tsh": ["tsh"],
    "hemoglobin": ["haemoglobin", "hemoglobin", "hb"],
}

CATEGORY_KEYWORDS = [
    ("discharge_summary", ["discharge summary", "date of discharge"]),
    ("vaccination_record", ["vaccine", "vaccination", "immunisation", "immunization"]),
    ("mri", ["mri", "magnetic resonance"]),
    ("ct_scan", ["ct scan", "computed tomography", "hrct"]),
    ("xray", ["x-ray", "xray", "radiograph"]),
    ("prescription", ["rx:", "prescription", "prescriber"]),
    ("blood_report", ["reference range", "laboratory", "haematology", "biochemistry"]),
    ("diagnostic_report", ["stress test", "ecg", "echocardiogram", "ultrasound", "impression:"]),
    ("consultation_note", ["consultation", "clinical notes", "reason for visit"]),
]

FREQ_PATTERNS = [
    r"once daily(?: [a-z ]+)?", r"twice daily(?: [a-z ]+)?", r"three times daily", r"four times daily",
    r"once weekly", r"as needed(?: [a-z ]+)?", r"every \d+ hours", r"\b(?:OD|BD|BID|TDS|TID|QID|HS|SOS|PRN)\b",
    r"\d-\d-\d", r"\d+ puffs? [a-z ]+",
]
DOSE_RE = r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?\s?(?:mg|mcg|g|iu|IU|ml|mL|units?))"


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:10]).strip()
    except Exception:
        return ""


def _f(value: str | None, confidence: float) -> m.ExtractedField:
    return m.ExtractedField(value=value.strip() if value else None, confidence=confidence if value else 0.0)


def _labelled(text: str, *labels: str) -> str | None:
    for label in labels:
        mt = re.search(rf"^\s*{label}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        if mt:
            return mt.group(1).strip()
    return None


def _normalise_date(raw: str | None) -> str | None:
    if not raw:
        return None
    mt = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if mt:
        return mt.group(0)
    mt = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", raw)
    if mt:
        d, mo, y = mt.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"  # dd/mm/yyyy (Indian convention)
    return None


def lab_code_for(name: str) -> str | None:
    n = name.lower().strip()
    for code, aliases in LAB_ALIASES.items():
        if any(n == a or n.startswith(a) for a in aliases):
            return code
    return None


def parse_reference(text: str | None) -> tuple[float | None, float | None]:
    if not text:
        return None, None
    t = text.replace(",", "")
    mt = re.search(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)", t)
    if mt:
        return float(mt.group(1)), float(mt.group(2))
    mt = re.search(r"(?:<|≤|<=|below|up to)\s*=?\s*(\d+(?:\.\d+)?)", t)
    if mt:
        return None, float(mt.group(1))
    mt = re.search(r"(?:>|≥|>=|above)\s*=?\s*(\d+(?:\.\d+)?)", t)
    if mt:
        return float(mt.group(1)), None
    return None, None


def rule_extract(text: str) -> tuple[m.ExtractionFields, list[str]]:
    warnings: list[str] = []
    low = text.lower()
    fields = m.ExtractionFields()

    category = next((cat for cat, kws in CATEGORY_KEYWORDS if any(k in low for k in kws)), None)
    fields.category = _f(category, 0.7)

    date_raw = _labelled(text, "date", "report date", "consultation date", "date of visit", "date of discharge")
    iso = _normalise_date(date_raw) or _normalise_date(text)
    fields.consultation_date = _f(iso, 0.85 if date_raw else 0.5)

    doctor = _labelled(text, "doctor", "prescriber", "referring doctor", "consultant", "attending")
    if not doctor:
        mt = re.search(r"\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", text)
        doctor = mt.group(0) if mt else None
        fields.doctor_name = _f(doctor, 0.55)
    else:
        fields.doctor_name = _f(doctor, 0.85)

    hospital = _labelled(text, "facility", "hospital", "laboratory", "clinic", "administered at")
    fields.hospital = _f(hospital, 0.8)
    fields.diagnosis = _f(_labelled(text, "diagnosis", "diagnoses", "impression", "final diagnosis"), 0.75)
    fields.allergies = _f(_labelled(text, "allergies", "allergy", "known allergies"), 0.8)

    # medications: lines in an Rx block or bullet lines that contain a dose
    meds: list[m.ExtractedMedication] = []
    for line in text.splitlines():
        ln = line.strip().lstrip("-*•").strip()
        dose = re.search(DOSE_RE, ln)
        if not dose or "|" in ln and lab_code_for(ln.split("|")[0]) is not None:
            continue
        name = ln[: dose.start()].strip(" :-")
        if not name or len(name) > 60 or not re.match(r"^[A-Za-z]", name) or re.search(r"\d{4}", name):
            continue
        if any(w in name.lower() for w in ("protocol", "dose:", "batch", "max hr", "vaccine")):
            continue
        rest = ln[dose.end():]
        freq = None
        for pat in FREQ_PATTERNS:
            fm = re.search(pat, rest, re.IGNORECASE)
            if fm:
                freq = fm.group(0).strip()
                break
        dur = re.search(r"(\d+\s*(?:days?|weeks?|months?))|until review", rest, re.IGNORECASE)
        meds.append(m.ExtractedMedication(name=name, dosage=dose.group(1), frequency=freq,
                                          duration=dur.group(0) if dur else None))
    fields.medications = meds

    labs: list[m.ExtractedLab] = []
    for line in text.splitlines():
        parts = [p.strip() for p in re.split(r"\s*\|\s*", line) if p.strip()]
        if len(parts) >= 2 and lab_code_for(parts[0]):
            val = re.search(r"-?\d+(?:\.\d+)?", parts[1])
            labs.append(m.ExtractedLab(test_name=parts[0], value=float(val.group(0)) if val else None,
                                       value_text=parts[1], unit=parts[2] if len(parts) > 2 else None,
                                       reference_range=parts[3] if len(parts) > 3 else None))
            continue
        mt = re.match(r"^\s*([A-Za-z][A-Za-z0-9 ()/\-]+?)\s*[:\-]\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z%/0-9.]+)?\s*(?:\((.*)\))?",
                      line)
        if mt and lab_code_for(mt.group(1)):
            labs.append(m.ExtractedLab(test_name=mt.group(1).strip(), value=float(mt.group(2)),
                                       value_text=mt.group(2), unit=mt.group(3), reference_range=mt.group(4)))
    fields.labs = labs
    if not meds and not labs and not fields.diagnosis.value:
        warnings.append("No medications, lab values or diagnosis were recognised. Please review the document "
                        "and enter values manually.")
    return fields, warnings


def _overall(fields: m.ExtractionFields) -> float:
    scores = [f.confidence for f in (fields.category, fields.consultation_date, fields.doctor_name, fields.hospital)
              if f.value]
    if fields.medications or fields.labs:
        scores.append(0.75)
    return round(sum(scores) / len(scores), 2) if scores else 0.0


AI_SCHEMA_HINT = (
    'Return JSON: {"category": one of [prescription, blood_report, diagnostic_report, xray, mri, ct_scan, '
    'discharge_summary, consultation_note, vaccination_record, other], "consultation_date": "YYYY-MM-DD"|null, '
    '"doctor_name": str|null, "hospital": str|null, "diagnosis": str|null, "allergies": str|null, '
    '"medications": [{"name","dosage","frequency","duration"}], "labs": [{"test_name","value","unit",'
    '"reference_range"}], "confidence": 0..1}. Use null for anything not clearly present. Do not guess.'
)


def _ai_extract(text: str | None, image: tuple[bytes, str] | None) -> m.ExtractionFields | None:
    content: list[dict] | str
    if image:
        b64 = base64.b64encode(image[0]).decode()
        content = [{"type": "text", "text": "Extract structured data from this medical document. " + AI_SCHEMA_HINT},
                   {"type": "image_url", "image_url": {"url": f"data:{image[1]};base64,{b64}"}}]
    else:
        content = "Extract structured data from this medical document text.\n" + AI_SCHEMA_HINT + "\n\n" + (text or "")[:12000]
    data = llm.chat_json([{"role": "system", "content": llm.GROUNDING_RULES}, {"role": "user", "content": content}])
    if not data:
        return None
    conf = float(data.get("confidence") or 0.6)
    try:
        return m.ExtractionFields(
            category=_f(data.get("category"), conf), consultation_date=_f(_normalise_date(data.get("consultation_date")), conf),
            doctor_name=_f(data.get("doctor_name"), conf), hospital=_f(data.get("hospital"), conf),
            diagnosis=_f(data.get("diagnosis"), conf), allergies=_f(data.get("allergies"), conf),
            medications=[m.ExtractedMedication(**{k: (str(v) if v is not None else None) for k, v in x.items()
                                                  if k in ("name", "dosage", "frequency", "duration")})
                         for x in data.get("medications") or [] if x.get("name")],
            labs=[m.ExtractedLab(test_name=str(x.get("test_name")), value=_num(x.get("value")),
                                 value_text=str(x.get("value")), unit=x.get("unit"),
                                 reference_range=x.get("reference_range"))
                  for x in data.get("labs") or [] if x.get("test_name")],
        )
    except Exception:
        return None


def _num(v) -> float | None:  # noqa: ANN001
    try:
        return float(re.search(r"-?\d+(?:\.\d+)?", str(v)).group(0))  # type: ignore[union-attr]
    except Exception:
        return None


def analyze(doc: m.Document) -> m.Extraction:
    settings = get_settings()
    path = settings.upload_dir / doc.stored_filename
    is_pdf = doc.content_type == "application/pdf"
    text = extract_pdf_text(path) if is_pdf else ""
    warnings: list[str] = []
    fields: m.ExtractionFields | None = None
    method, label = "demo_template", ""

    if settings.live_ai_enabled:
        image = None if is_pdf else (path.read_bytes(), doc.content_type)
        if is_pdf and not text:
            warnings.append("PDF has no embedded text (likely a scan); live AI text extraction skipped.")
        else:
            fields = _ai_extract(text, image)
        if fields:
            method, label = "live_ai", f"Live AI extraction ({settings.openai_model}) - verify every field"

    if fields is None and text:
        fields, w = rule_extract(text)
        warnings += w
        method = "pdf_text_rules"
        label = "Rule-based extraction from embedded PDF text (no OCR, no AI) - verify every field"

    if fields is None:
        method = "demo_template"
        label = "DEMO MODE - no OCR/AI configured. Manual review: enter values from the document."
        fields = m.ExtractionFields(
            category=_f(doc.category, 0.3),
            consultation_date=_f(doc.document_date.isoformat() if doc.document_date else None, 0.3),
            doctor_name=_f(doc.doctor_name, 0.3), hospital=_f(doc.hospital, 0.3),
        )
        warnings.append("Text could not be read from this file without OCR. Fields are pre-filled only from the "
                        "details you entered at upload. No clinical values were generated.")

    return m.Extraction(
        id=m.new_id("ext"), document_id=doc.id, patient_id=doc.patient_id, method=method, method_label=label,
        raw_text_excerpt=text[:1500] if text else None, fields=fields, overall_confidence=_overall(fields),
        warnings=warnings, is_demo=True,
    )


def sniff_type(head: bytes) -> str | None:
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


