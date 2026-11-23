"""Ownership and consent checks, enforced server-side on every patient-data route."""
from __future__ import annotations

from fastapi import HTTPException, status

from ..models import AccessGrant, Scope
from ..security import CurrentUser
from ..storage import get_repos
from .audit import audit


def active_grant(doctor_id: str, patient_id: str) -> AccessGrant | None:
    grants = [
        g for g in get_repos().access_grants.find(doctor_id=doctor_id, patient_id=patient_id) if g.is_active()
    ]
    if not grants:
        return None
    return max(grants, key=lambda g: g.expires_at)


def ensure_patient_access(cu: CurrentUser, patient_id: str, scope: Scope | str | None = None) -> AccessGrant | None:
    """Raise 403/404 unless `cu` may read `patient_id` data in `scope`.

    Patients may read only their own record. Doctors need an active,
    unrevoked, unexpired demo grant that covers the scope.
    """
    if get_repos().patients.get(patient_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    if cu.is_patient:
        if cu.user.patient_id != patient_id:
            audit(cu, "access.denied", patient_id=patient_id, detail="patient tried to read another record", outcome="denied")
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only access your own records")
        return None
    if cu.is_doctor and cu.user.doctor_id:
        grant = active_grant(cu.user.doctor_id, patient_id)
        scope_value = scope.value if isinstance(scope, Scope) else scope
        if grant is None:
            audit(cu, "access.denied", patient_id=patient_id, detail="no active consent grant", outcome="denied")
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No active patient consent for this doctor")
        if scope_value and scope_value not in grant.scopes:
            audit(cu, "access.denied", patient_id=patient_id, detail=f"scope '{scope_value}' not granted", outcome="denied")
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Patient has not shared '{scope_value}' with you")
        return grant
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")


def resolve_patient_id(cu: CurrentUser, patient_id: str | None) -> str:
    """Patients default to themselves; doctors must name a patient."""
    if patient_id:
        return patient_id
    if cu.is_patient and cu.user.patient_id:
        return cu.user.patient_id
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "patient_id is required")


def allowed_scopes(cu: CurrentUser, patient_id: str) -> list[str]:
    from ..models import ALL_SCOPES

    if cu.is_patient:
        return ALL_SCOPES if cu.user.patient_id == patient_id else []
    if cu.is_doctor and cu.user.doctor_id:
        g = active_grant(cu.user.doctor_id, patient_id)
        return list(g.scopes) if g else []
    return []
