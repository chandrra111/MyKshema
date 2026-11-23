from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import models as m
from ..security import CurrentUser, get_current_user, require_patient
from ..services import records
from ..services.access import allowed_scopes, ensure_patient_access
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("/me")
def my_profile(cu: CurrentUser = Depends(require_patient)) -> dict:
    p = get_repos().patients.require(cu.user.patient_id)  # type: ignore[arg-type]
    b = records.load_bundle(p.id, m.ALL_SCOPES)
    return {**p.model_dump(mode="json"), "age": b.age, "email": cu.user.email}


class ProfileUpdate(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=40)
    city: Optional[str] = Field(default=None, max_length=80)
    emergency_contact: Optional[str] = Field(default=None, max_length=120)
    blood_group: Optional[str] = Field(default=None, max_length=5)
    height_cm: Optional[float] = Field(default=None, ge=50, le=250)


@router.patch("/me")
def update_profile(body: ProfileUpdate, cu: CurrentUser = Depends(require_patient)) -> dict:
    r = get_repos()
    p = r.patients.require(cu.user.patient_id)  # type: ignore[arg-type]
    updated = p.model_copy(update={k: v for k, v in body.model_dump().items() if v is not None})
    r.patients.update(updated)
    audit(cu, "profile.updated", patient_id=p.id, resource_type="patient", resource_id=p.id)
    return updated.model_dump(mode="json")


@router.get("/{patient_id}")
def patient_profile(patient_id: str, cu: CurrentUser = Depends(get_current_user)) -> dict:
    ensure_patient_access(cu, patient_id)
    p = get_repos().patients.require(patient_id)
    b = records.load_bundle(patient_id, [])
    return {**p.model_dump(mode="json"), "age": b.age, "shared_scopes": allowed_scopes(cu, patient_id)}


@router.get("/{patient_id}/history", summary="Consolidated history (filtered to shared scopes)")
def history(patient_id: str, cu: CurrentUser = Depends(get_current_user)) -> dict:
    ensure_patient_access(cu, patient_id)
    scopes = allowed_scopes(cu, patient_id)
    b = records.load_bundle(patient_id, scopes)
    if cu.is_doctor:
        audit(cu, "patient.history_viewed", patient_id=patient_id, resource_type="patient", resource_id=patient_id)
    dump = lambda items: [i.model_dump(mode="json") for i in items]  # noqa: E731
    return {
        "patient": {**b.profile.model_dump(mode="json"), "age": b.age},
        "shared_scopes": scopes,
        "conditions": dump(b.conditions),
        "allergies": dump(b.allergies),
        "medications": dump(b.medications),
        "consultations": dump(b.consultations),
        "prescriptions": dump(b.prescriptions),
        "documents_count": len(b.documents),
        "observations_count": len(b.observations),
    }


@router.get("/{patient_id}/timeline", summary="Chronological events with links to source documents")
def timeline(patient_id: str, cu: CurrentUser = Depends(get_current_user),
             type: Optional[str] = None, doctor: Optional[str] = None, q: Optional[str] = None,
             date_from: Optional[date] = None, date_to: Optional[date] = None) -> dict:
    ensure_patient_access(cu, patient_id, m.Scope.history)
    scopes = allowed_scopes(cu, patient_id)
    events = records.build_timeline(records.load_bundle(patient_id, scopes))
    if type:
        events = [e for e in events if e["type"] in type.split(",")]
    if doctor:
        events = [e for e in events if doctor.lower() in (e.get("doctor") or "").lower()]
    if date_from:
        events = [e for e in events if e["date"] >= date_from.isoformat()]
    if date_to:
        events = [e for e in events if e["date"] <= date_to.isoformat()]
    if q:
        ql = q.lower()
        events = [e for e in events if ql in " ".join(str(v) for v in e.values() if v).lower()]
    doctors = sorted({e["doctor"] for e in events if e.get("doctor")})
    hospitals = sorted({e["hospital"] for e in events if e.get("hospital")})
    return {"events": events, "count": len(events), "doctors": doctors, "hospitals": hospitals,
            "shared_scopes": scopes}


@router.get("/{patient_id}/conditions")
def conditions(patient_id: str, cu: CurrentUser = Depends(get_current_user)) -> list[dict]:
    ensure_patient_access(cu, patient_id, m.Scope.history)
    return [c.model_dump(mode="json") for c in get_repos().conditions.find(patient_id=patient_id)]


@router.get("/{patient_id}/allergies")
def allergies(patient_id: str, cu: CurrentUser = Depends(get_current_user)) -> list[dict]:
    ensure_patient_access(cu, patient_id, m.Scope.allergies)
    return [a.model_dump(mode="json") for a in get_repos().allergies.find(patient_id=patient_id)]


class AllergyIn(BaseModel):
    substance: str = Field(min_length=2, max_length=120)
    drug_class: Optional[str] = Field(default=None, max_length=80)
    reaction: Optional[str] = Field(default=None, max_length=200)
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    recorded_on: Optional[date] = None


@router.post("/me/allergies", status_code=201)
def add_allergy(body: AllergyIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    a = m.Allergy(id=m.new_id("alg"), patient_id=cu.user.patient_id, **body.model_dump())  # type: ignore[arg-type]
    if a.recorded_on is None:
        a.recorded_on = date.today()
    get_repos().allergies.add(a)
    audit(cu, "allergy.added", patient_id=a.patient_id, resource_type="allergy", resource_id=a.id, detail=a.substance)
    return a.model_dump(mode="json")
