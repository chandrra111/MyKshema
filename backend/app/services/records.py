"""Assemble a patient's record, filtered to the scopes the caller may see."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .. import models as m
from ..storage import get_repos


@dataclass
class PatientBundle:
    profile: m.PatientProfile
    scopes: list[str]
    conditions: list[m.Condition] = field(default_factory=list)
    allergies: list[m.Allergy] = field(default_factory=list)
    medications: list[m.Medication] = field(default_factory=list)
    medication_events: list[m.MedicationEvent] = field(default_factory=list)
    observations: list[m.Observation] = field(default_factory=list)
    consultations: list[m.Consultation] = field(default_factory=list)
    prescriptions: list[m.Prescription] = field(default_factory=list)
    documents: list[m.Document] = field(default_factory=list)

    @property
    def age(self) -> int:
        today = date.today()
        dob = self.profile.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def doc_title(self, doc_id: str | None) -> str | None:
        if not doc_id:
            return None
        for d in self.documents:
            if d.id == doc_id:
                return d.title
        return None


def load_bundle(patient_id: str, scopes: list[str]) -> PatientBundle:
    r = get_repos()
    profile = r.patients.require(patient_id)
    b = PatientBundle(profile=profile, scopes=scopes)
    s = set(scopes)
    if "history" in s:
        b.conditions = sorted(r.conditions.find(patient_id=patient_id), key=lambda c: c.diagnosed_on or date.min)
    if "allergies" in s:
        b.allergies = r.allergies.find(patient_id=patient_id)
    if "medications" in s:
        b.medications = r.medications.find(patient_id=patient_id)
        b.medication_events = sorted(r.medication_events.find(patient_id=patient_id), key=lambda e: e.event_date)
        b.prescriptions = sorted(r.prescriptions.find(patient_id=patient_id), key=lambda p: p.issued_on)
    if "labs" in s:
        b.observations = sorted(r.observations.find(patient_id=patient_id), key=lambda o: o.observed_on)
    if "consultations" in s or "history" in s:
        b.consultations = sorted(r.consultations.find(patient_id=patient_id), key=lambda c: c.consultation_date)
    if "documents" in s:
        b.documents = sorted(r.documents.find(patient_id=patient_id), key=lambda d: d.document_date or date.min)
    else:
        # Titles of source documents are still useful as citations, but files stay inaccessible.
        b.documents = []
    return b


TYPE_LABEL = {
    "consultation": "Consultation",
    "prescription": "Prescription",
    "lab_report": "Lab report",
    "document": "Document",
    "medication": "Medication change",
    "diagnosis": "Diagnosis",
    "allergy": "Allergy recorded",
}


def build_timeline(b: PatientBundle) -> list[dict]:
    events: list[dict] = []
    docs_by_id = {d.id: d for d in b.documents}
    used_docs: set[str] = set()

    for c in b.consultations:
        events.append({
            "id": f"evt_{c.id}", "date": c.consultation_date.isoformat(), "type": "consultation",
            "title": c.reason or "Consultation", "doctor": c.doctor_name, "hospital": c.hospital,
            "summary": c.notes, "diagnoses": c.diagnoses, "follow_up": c.follow_up,
            "source_document_id": c.source_document_id, "record_id": c.id, "created_via": c.created_via,
        })
        if c.source_document_id:
            used_docs.add(c.source_document_id)

    for p in b.prescriptions:
        events.append({
            "id": f"evt_{p.id}", "date": p.issued_on.isoformat(), "type": "prescription",
            "title": "Prescription: " + ", ".join(i.name for i in p.items), "doctor": p.doctor_name,
            "summary": "; ".join(f"{i.name} {i.dosage} - {i.frequency}" + (f" ({i.duration})" if i.duration else "")
                                 for i in p.items),
            "medications": [i.name for i in p.items], "source_document_id": p.source_document_id,
            "record_id": p.id, "status": p.status,
        })
        if p.source_document_id:
            used_docs.add(p.source_document_id)

    labs_by_doc: dict[tuple, list[m.Observation]] = defaultdict(list)
    for o in b.observations:
        if o.panel == "Vitals":
            continue
        labs_by_doc[(o.source_document_id, o.observed_on)].append(o)
    for (doc_id, d), obs in labs_by_doc.items():
        flagged = [o for o in obs if _out_of_range(o)]
        events.append({
            "id": f"evt_lab_{doc_id or d.isoformat()}", "date": d.isoformat(), "type": "lab_report",
            "title": obs[0].source_label or "Lab results", "doctor": docs_by_id[doc_id].doctor_name if doc_id in docs_by_id else None,
            "hospital": docs_by_id[doc_id].hospital if doc_id in docs_by_id else None,
            "summary": ", ".join(f"{o.name} {o.value:g} {o.unit}" for o in obs),
            "flags": [f"{o.name} outside documented range ({o.reference_text})" for o in flagged],
            "source_document_id": doc_id, "record_id": doc_id,
        })
        if doc_id:
            used_docs.add(doc_id)

    for e in b.medication_events:
        if e.event_type in ("dose_changed", "stopped", "completed", "reported", "proposed"):
            events.append({
                "id": f"evt_{e.id}", "date": e.event_date.isoformat(), "type": "medication",
                "title": e.description, "doctor": e.by, "summary": e.description, "record_id": e.medication_id,
                "event_type": e.event_type,
            })

    for a in b.allergies:
        if a.recorded_on:
            events.append({
                "id": f"evt_{a.id}", "date": a.recorded_on.isoformat(), "type": "allergy",
                "title": f"Allergy recorded: {a.substance}", "summary": f"Reaction: {a.reaction or 'not documented'}; "
                f"severity: {a.severity}", "record_id": a.id, "source_document_id": a.source_document_id,
            })

    for d in b.documents:
        if d.id in used_docs:
            continue
        events.append({
            "id": f"evt_{d.id}", "date": (d.document_date or d.uploaded_at.date()).isoformat(), "type": "document",
            "title": d.title, "doctor": d.doctor_name, "hospital": d.hospital, "category": d.category,
            "summary": d.notes or f"{d.category.replace('_', ' ').title()} uploaded", "source_document_id": d.id,
            "record_id": d.id, "extraction_status": d.extraction_status,
        })

    for e in events:
        sid = e.get("source_document_id")
        e["source_document_title"] = docs_by_id[sid].title if sid in docs_by_id else None
        e["type_label"] = TYPE_LABEL.get(e["type"], e["type"])
    events.sort(key=lambda e: (e["date"], e["type"]), reverse=True)
    return events


def _out_of_range(o: m.Observation) -> bool:
    if o.reference_low is not None and o.value < o.reference_low:
        return True
    if o.reference_high is not None and o.value > o.reference_high:
        return True
    return False


def range_status(o: m.Observation) -> str:
    if o.reference_low is None and o.reference_high is None:
        return "no_documented_range"
    if o.reference_low is not None and o.value < o.reference_low:
        return "below_range"
    if o.reference_high is not None and o.value > o.reference_high:
        return "above_range"
    return "within_range"
