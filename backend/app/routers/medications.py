from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .. import models as m
from ..security import CurrentUser, get_current_user, require_patient
from ..services import medication_review
from ..services.access import ensure_patient_access, resolve_patient_id
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(prefix="/api/medications", tags=["medications"])


def _out(x: m.Medication, docs: dict[str, str]) -> dict:
    d = x.model_dump(mode="json")
    d["source_document_title"] = docs.get(x.source_document_id or "")
    return d


@router.get("", summary="Medication list, grouped by status, with review flags")
def list_medications(cu: CurrentUser = Depends(get_current_user), patient_id: Optional[str] = None,
                     status_filter: Optional[str] = None) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, m.Scope.medications)
    r = get_repos()
    meds = r.medications.find(patient_id=pid)
    docs = {d.id: d.title for d in r.documents.find(patient_id=pid)}
    allergies = r.allergies.find(patient_id=pid)
    flags = medication_review.review(meds, allergies)
    if status_filter:
        meds = [x for x in meds if x.status in status_filter.split(",")]
    meds.sort(key=lambda x: x.start_date or date.min, reverse=True)
    return {"medications": [_out(x, docs) for x in meds], "flags": flags,
            "flags_note": "Rule-based flags from recorded data and a curated demo reference table. "
                          "They require review by a qualified clinician. MyKshema never changes medicines."}


@router.get("/history", summary="Chronological medication events")
def medication_history(cu: CurrentUser = Depends(get_current_user), patient_id: Optional[str] = None) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, m.Scope.medications)
    events = sorted(get_repos().medication_events.find(patient_id=pid), key=lambda e: e.event_date, reverse=True)
    return {"events": [e.model_dump(mode="json") for e in events]}


class PatientMedIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    generic_name: Optional[str] = Field(default=None, max_length=120)
    dosage: Optional[str] = Field(default=None, max_length=60)
    frequency: Optional[str] = Field(default=None, max_length=80)
    start_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=300)


@router.post("", status_code=201, summary="Patient records a self-reported current medicine (unverified)")
def add_patient_reported(body: PatientMedIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    pid = cu.user.patient_id
    med = m.Medication(
        id=m.new_id("med"), patient_id=pid, name=body.name, generic_name=(body.generic_name or body.name).lower().split()[0],  # type: ignore[arg-type]
        dosage=body.dosage, frequency=body.frequency, start_date=body.start_date or date.today(),
        status="patient_reported", verified=False, notes=body.notes or "Self-reported by patient.",
    )
    r = get_repos()
    r.medications.add(med)
    r.medication_events.add(m.MedicationEvent(id=m.new_id("mev"), patient_id=pid, medication_id=med.id,  # type: ignore[arg-type]
                                              event_date=med.start_date, event_type="reported",  # type: ignore[arg-type]
                                              description=f"{med.name} reported by patient"))
    audit(cu, "medication.reported", patient_id=pid, resource_type="medication", resource_id=med.id, detail=med.name)
    return med.model_dump(mode="json")


class AdherenceIn(BaseModel):
    adherence: Literal["taking_as_prescribed", "sometimes_missed", "often_missed", "stopped_on_own"]


@router.patch("/{med_id}/adherence", summary="Patient-reported adherence (does not change the prescription)")
def set_adherence(med_id: str, body: AdherenceIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    r = get_repos()
    med = r.medications.get(med_id)
    if med is None or med.patient_id != cu.user.patient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medication not found")
    med.adherence = body.adherence
    r.medications.update(med)
    audit(cu, "medication.adherence_reported", patient_id=med.patient_id, resource_type="medication",
          resource_id=med.id, detail=body.adherence)
    return med.model_dump(mode="json")
