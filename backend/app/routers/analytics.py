from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import models as m
from ..security import CurrentUser, get_current_user, require_patient
from ..services import analytics, records
from ..services.access import allowed_scopes, ensure_patient_access, resolve_patient_id
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/health-trends", summary="Per-measure series, latest values and documented reference ranges")
def health_trends(cu: CurrentUser = Depends(get_current_user), patient_id: Optional[str] = None) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, m.Scope.labs)
    b = records.load_bundle(pid, allowed_scopes(cu, pid))
    return {"trends": analytics.trends(b),
            "note": "Reference indicators are shown only where a range is documented on the source report. "
                    "Trend slopes are descriptive (OLS, 95% CI) and are not forecasts."}


@router.get("/observations")
def observations(cu: CurrentUser = Depends(get_current_user), patient_id: Optional[str] = None,
                 code: Optional[str] = None) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, m.Scope.labs)
    obs = get_repos().observations.find(patient_id=pid)
    if code:
        obs = [o for o in obs if o.code in code.split(",")]
    obs.sort(key=lambda o: o.observed_on, reverse=True)
    return {"observations": [o.model_dump(mode="json") for o in obs]}


VITALS = {
    "bp_systolic": ("Systolic BP", "mmHg"), "bp_diastolic": ("Diastolic BP", "mmHg"),
    "heart_rate": ("Resting Heart Rate", "bpm"), "weight": ("Weight", "kg"),
    "fasting_glucose_home": ("Home Fasting Glucose (glucometer)", "mg/dL"),
}


class VitalIn(BaseModel):
    code: Literal["bp_systolic", "bp_diastolic", "heart_rate", "weight", "fasting_glucose_home"]
    value: float = Field(gt=0, lt=1000)
    observed_on: date = Field(default_factory=date.today)


@router.post("/observations", status_code=201, summary="Patient logs a home measurement")
def add_observation(body: VitalIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    name, unit = VITALS[body.code]
    o = m.Observation(id=m.new_id("obs"), patient_id=cu.user.patient_id, code=body.code, name=name,  # type: ignore[arg-type]
                      value=body.value, unit=unit, observed_on=body.observed_on, panel="Vitals",
                      source_label="Home measurement log (patient-entered)")
    get_repos().observations.add(o)
    audit(cu, "observation.added", patient_id=o.patient_id, resource_type="observation", resource_id=o.id,
          detail=f"{name} {body.value} {unit}")
    return o.model_dump(mode="json")


@router.get("/reminders", summary="Follow-ups and preventive-care prompts from recorded data")
def reminders(cu: CurrentUser = Depends(get_current_user), patient_id: Optional[str] = None) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid)
    b = records.load_bundle(pid, allowed_scopes(cu, pid))
    return {"reminders": analytics.reminders(b),
            "note": "Prompts are based only on what is recorded. Discuss timing with your doctor."}
