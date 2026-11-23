from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import models as m
from ..config import get_settings
from ..security import CurrentUser, get_current_user, require_patient
from ..services import ai, records
from ..services.access import allowed_scopes, ensure_patient_access, resolve_patient_id
from ..services.audit import audit
from ..storage import get_repos
from .documents import _load_doc, run_analysis

router = APIRouter(prefix="/api/ai", tags=["ai"])


class PatientRef(BaseModel):
    patient_id: Optional[str] = None


class AskIn(PatientRef):
    question: str = Field(min_length=2, max_length=500)


def _bundle(cu: CurrentUser, patient_id: Optional[str], scope: m.Scope | None = None) -> records.PatientBundle:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, scope)
    ai.check_rate_limit(cu.id)
    return records.load_bundle(pid, allowed_scopes(cu, pid))


def _store(cu: CurrentUser, b: records.PatientBundle, res: dict) -> dict:
    get_repos().ai_summaries.add(m.AISummary(id=m.new_id("ais"), patient_id=b.profile.id, requested_by=cu.id,
                                             kind=res["kind"], mode=res["mode"], content=res["answer"][:8000]))
    audit(cu, f"ai.{res['kind']}", patient_id=b.profile.id, resource_type="ai_summary", detail=f"mode={res['mode']}")
    return res


@router.get("/status")
def ai_status() -> dict:
    s = get_settings()
    return {"live_ai": s.live_ai_enabled, "model": s.openai_model if s.live_ai_enabled else None,
            "label": "Live AI enabled" if s.live_ai_enabled else ai.DEMO_LABEL,
            "ocr": "none - rule-based PDF text extraction" + (" + live AI vision" if s.live_ai_enabled else "")}


@router.post("/summarize-history")
def summarize_history(body: PatientRef, cu: CurrentUser = Depends(get_current_user)) -> dict:
    b = _bundle(cu, body.patient_id, m.Scope.history)
    return _store(cu, b, ai.summarize(b, "patient" if cu.is_patient else "doctor"))


@router.post("/ask", summary="Ask a question about the signed-in/authorised patient's records")
def ask(body: AskIn, cu: CurrentUser = Depends(get_current_user)) -> dict:
    b = _bundle(cu, body.patient_id)
    return _store(cu, b, ai.answer(body.question, b, "patient" if cu.is_patient else "doctor"))


@router.post("/medication-review")
def medication_review(body: PatientRef, cu: CurrentUser = Depends(get_current_user)) -> dict:
    b = _bundle(cu, body.patient_id, m.Scope.medications)
    return _store(cu, b, ai.skill_med_review(b))


@router.post("/health-insights")
def health_insights(body: PatientRef, cu: CurrentUser = Depends(get_current_user)) -> dict:
    b = _bundle(cu, body.patient_id, m.Scope.labs)
    return _store(cu, b, ai.skill_insights(b))


class AnalyzeIn(BaseModel):
    document_id: str


@router.post("/analyze-document", summary="Extract candidate fields from a document (requires user review)")
def analyze_document(body: AnalyzeIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    ai.check_rate_limit(cu.id)
    d = _load_doc(body.document_id, cu)
    return run_analysis(d, cu).model_dump(mode="json")
