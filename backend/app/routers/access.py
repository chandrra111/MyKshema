"""Doctor directory, simulated consent workflow and audit history.

PROTOTYPE SIMULATION: not production identity verification and not legally
validated consent (see docs/SECURITY.md re: India's DPDP Act)."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .. import models as m
from ..security import CurrentUser, get_current_user, require_doctor, require_patient
from ..services import records
from ..services.access import active_grant
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(tags=["doctor-connect"])

SIM_NOTE = "Not production identity verification or legally validated consent."


def _doctor_card(d: m.DoctorProfile, patient_id: str | None = None) -> dict:
    out = d.model_dump(mode="json")
    out["has_portal_login"] = bool(d.user_id)
    if patient_id:
        g = active_grant(d.id, patient_id)
        out["active_grant"] = g.model_dump(mode="json") if g else None
    return out


@router.get("/api/doctors", summary="Doctor directory (fictional)")
def doctors(cu: CurrentUser = Depends(get_current_user), q: Optional[str] = None,
            specialty: Optional[str] = None) -> dict:
    docs = get_repos().doctors.all()
    if q:
        ql = q.lower()
        docs = [d for d in docs if ql in f"{d.full_name} {d.specialty} {d.hospital} {d.city}".lower()]
    if specialty:
        docs = [d for d in docs if d.specialty.lower() == specialty.lower()]
    pid = cu.user.patient_id if cu.is_patient else None
    return {"doctors": [_doctor_card(d, pid) for d in docs], "note": SIM_NOTE}


@router.get("/api/doctor/me")
def doctor_me(cu: CurrentUser = Depends(require_doctor)) -> dict:
    return get_repos().doctors.require(cu.user.doctor_id).model_dump(mode="json")  # type: ignore[arg-type]


@router.get("/api/doctor/patients", summary="Patients who currently share records with this doctor")
def doctor_patients(cu: CurrentUser = Depends(require_doctor)) -> dict:
    r = get_repos()
    did = cu.user.doctor_id
    out = []
    for g in r.access_grants.find(doctor_id=did):
        if not g.is_active():
            continue
        p = r.patients.get(g.patient_id)
        if not p:
            continue
        b = records.load_bundle(p.id, list(g.scopes))
        last_c = b.consultations[-1] if b.consultations else None
        out.append({
            "patient_id": p.id, "full_name": p.full_name, "age": b.age, "sex": p.sex, "city": p.city,
            "scopes": g.scopes, "expires_at": g.expires_at.isoformat(), "grant_id": g.id,
            "active_conditions": [c.name for c in b.conditions if c.status == "active"],
            "last_consultation": last_c.consultation_date.isoformat() if last_c else None,
        })
    pending = [x.model_dump(mode="json") | {"patient_name": (r.patients.get(x.patient_id).full_name  # type: ignore[union-attr]
                                                              if r.patients.get(x.patient_id) else None)}
               for x in r.access_requests.find(doctor_id=did, status="pending")]
    return {"patients": out, "pending_requests": pending, "note": SIM_NOTE}


@router.get("/api/doctor/patient-lookup", summary="Find a patient by their MyKshema demo email to request access")
def patient_lookup(email: str, cu: CurrentUser = Depends(require_doctor)) -> dict:
    u = get_repos().users.first(email=email.strip().lower())
    if not u or not u.patient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient with that demo email")
    p = get_repos().patients.require(u.patient_id)
    audit(cu, "patient.lookup", patient_id=p.id, detail="looked up by email to request access")
    return {"patient_id": p.id, "full_name": p.full_name, "city": p.city}  # minimal, no health data


class RequestIn(BaseModel):
    patient_id: Optional[str] = None  # doctor -> patient
    doctor_id: Optional[str] = None  # patient -> doctor (patient-initiated share proposal)
    scopes: list[m.Scope] = Field(min_length=1)
    reason: Optional[str] = Field(default=None, max_length=300)
    duration_hours: int = Field(default=72, ge=1, le=24 * 90)


@router.post("/api/access-requests", status_code=201, summary="Doctor requests access to a patient's records")
def create_request(body: RequestIn, cu: CurrentUser = Depends(get_current_user)) -> dict:
    r = get_repos()
    if cu.is_doctor:
        if not body.patient_id or not r.patients.get(body.patient_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
        pid, did = body.patient_id, cu.user.doctor_id
    else:
        if not body.doctor_id or not r.doctors.get(body.doctor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
        pid, did = cu.user.patient_id, body.doctor_id
    if r.access_requests.find(patient_id=pid, doctor_id=did, status="pending"):
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending request already exists")
    req = m.AccessRequest(id=m.new_id("req"), patient_id=pid, doctor_id=did, initiated_by=cu.role,  # type: ignore[arg-type]
                          requested_scopes=body.scopes, reason=body.reason, duration_hours=body.duration_hours)
    r.access_requests.add(req)
    audit(cu, "access.requested", patient_id=pid, resource_type="access_request", resource_id=req.id,
          detail=f"scopes={','.join(req.requested_scopes)}; {req.duration_hours}h")
    return req.model_dump(mode="json")


@router.get("/api/access-requests")
def list_requests(cu: CurrentUser = Depends(get_current_user),
                  status_filter: Optional[Literal["pending", "approved", "denied", "cancelled"]] = None) -> dict:
    r = get_repos()
    reqs = (r.access_requests.find(patient_id=cu.user.patient_id) if cu.is_patient
            else r.access_requests.find(doctor_id=cu.user.doctor_id))
    if status_filter:
        reqs = [x for x in reqs if x.status == status_filter]
    reqs.sort(key=lambda x: x.created_at, reverse=True)
    docs = {d.id: d for d in r.doctors.all()}
    pats = {p.id: p.full_name for p in r.patients.all()}
    return {"requests": [x.model_dump(mode="json") | {
        "doctor": _doctor_card(docs[x.doctor_id]) if x.doctor_id in docs else None,
        "patient_name": pats.get(x.patient_id)} for x in reqs], "note": SIM_NOTE}


class DecisionIn(BaseModel):
    scopes: Optional[list[m.Scope]] = None  # patient may narrow the requested scope
    duration_hours: Optional[int] = Field(default=None, ge=1, le=24 * 90)


def _grant(cu: CurrentUser, patient_id: str, doctor_id: str, scopes: list, hours: int, request_id: str | None) -> m.AccessGrant:
    r = get_repos()
    # one active grant per doctor/patient: supersede any existing one
    for g in r.access_grants.find(patient_id=patient_id, doctor_id=doctor_id):
        if g.is_active():
            g.revoked_at = m.utcnow()
            r.access_grants.update(g)
    g = m.AccessGrant(id=m.new_id("grt"), patient_id=patient_id, doctor_id=doctor_id, scopes=scopes,
                      expires_at=m.utcnow() + timedelta(hours=hours), request_id=request_id)
    r.access_grants.add(g)
    return g


@router.post("/api/access-requests/{req_id}/approve", summary="Patient approves (optionally narrowing scope/duration)")
def approve(req_id: str, body: DecisionIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    r = get_repos()
    req = r.access_requests.get(req_id)
    if not req or req.patient_id != cu.user.patient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {req.status}")
    scopes = body.scopes or req.requested_scopes
    hours = body.duration_hours or req.duration_hours
    g = _grant(cu, req.patient_id, req.doctor_id, scopes, hours, req.id)
    req.status, req.decided_at, req.grant_id = "approved", m.utcnow(), g.id
    r.access_requests.update(req)
    doc = r.doctors.get(req.doctor_id)
    audit(cu, "access.request_approved", patient_id=req.patient_id, resource_type="access_grant", resource_id=g.id,
          detail=f"Approved {doc.full_name if doc else req.doctor_id}: {','.join(scopes)} for {hours}h")
    return {"request": req.model_dump(mode="json"), "grant": g.model_dump(mode="json")}


@router.post("/api/access-requests/{req_id}/deny")
def deny(req_id: str, cu: CurrentUser = Depends(require_patient)) -> dict:
    r = get_repos()
    req = r.access_requests.get(req_id)
    if not req or req.patient_id != cu.user.patient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {req.status}")
    req.status, req.decided_at = "denied", m.utcnow()
    r.access_requests.update(req)
    audit(cu, "access.request_denied", patient_id=req.patient_id, resource_type="access_request", resource_id=req.id)
    return req.model_dump(mode="json")


@router.post("/api/access-requests/{req_id}/cancel")
def cancel(req_id: str, cu: CurrentUser = Depends(get_current_user)) -> dict:
    r = get_repos()
    req = r.access_requests.get(req_id)
    mine = req and ((cu.is_doctor and req.doctor_id == cu.user.doctor_id) or
                    (cu.is_patient and req.patient_id == cu.user.patient_id))
    if not req or not mine:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if req.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {req.status}")
    req.status, req.decided_at = "cancelled", m.utcnow()
    r.access_requests.update(req)
    audit(cu, "access.request_cancelled", patient_id=req.patient_id, resource_type="access_request", resource_id=req.id)
    return req.model_dump(mode="json")


class ShareIn(BaseModel):
    doctor_id: str
    scopes: list[m.Scope] = Field(min_length=1)
    duration_hours: int = Field(default=72, ge=1, le=24 * 90)


@router.post("/api/access-grants", status_code=201, summary="Patient shares selected records with a doctor directly")
def share(body: ShareIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    doc = get_repos().doctors.get(body.doctor_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    g = _grant(cu, cu.user.patient_id, doc.id, body.scopes, body.duration_hours, None)  # type: ignore[arg-type]
    audit(cu, "access.granted", patient_id=g.patient_id, resource_type="access_grant", resource_id=g.id,
          detail=f"Shared {','.join(g.scopes)} with {doc.full_name} for {body.duration_hours}h")
    return g.model_dump(mode="json")


@router.get("/api/access-grants")
def list_grants(cu: CurrentUser = Depends(get_current_user)) -> dict:
    r = get_repos()
    grants = (r.access_grants.find(patient_id=cu.user.patient_id) if cu.is_patient
              else r.access_grants.find(doctor_id=cu.user.doctor_id))
    grants.sort(key=lambda g: g.granted_at, reverse=True)
    docs = {d.id: d for d in r.doctors.all()}
    pats = {p.id: p.full_name for p in r.patients.all()}
    out = []
    for g in grants:
        state = "active" if g.is_active() else ("revoked" if g.revoked_at else "expired")
        out.append(g.model_dump(mode="json") | {"state": state, "patient_name": pats.get(g.patient_id),
                                                "doctor": _doctor_card(docs[g.doctor_id]) if g.doctor_id in docs else None})
    return {"grants": out, "note": SIM_NOTE}


@router.post("/api/access-grants/{grant_id}/revoke", summary="Patient revokes a doctor's access immediately")
def revoke(grant_id: str, cu: CurrentUser = Depends(require_patient)) -> dict:
    r = get_repos()
    g = r.access_grants.get(grant_id)
    if not g or g.patient_id != cu.user.patient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grant not found")
    if g.revoked_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already revoked")
    g.revoked_at = m.utcnow()
    r.access_grants.update(g)
    doc = r.doctors.get(g.doctor_id)
    audit(cu, "access.revoked", patient_id=g.patient_id, resource_type="access_grant", resource_id=g.id,
          detail=f"Revoked {doc.full_name if doc else g.doctor_id}")
    return g.model_dump(mode="json")


@router.get("/api/audit-logs", summary="Patients: who accessed/changed their record. Doctors: their own actions.")
def audit_logs(cu: CurrentUser = Depends(get_current_user), limit: int = 200) -> dict:
    r = get_repos()
    if cu.is_patient:
        logs = r.audit_logs.find(patient_id=cu.user.patient_id)
    else:
        logs = r.audit_logs.find(actor_user_id=cu.id)
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    return {"logs": [x.model_dump(mode="json") for x in logs[: max(1, min(limit, 1000))]]}
