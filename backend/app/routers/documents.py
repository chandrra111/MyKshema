from __future__ import annotations

import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import models as m
from ..config import get_settings
from ..security import CurrentUser, get_current_user, require_patient
from ..services import extraction
from ..services.access import ensure_patient_access, resolve_patient_id
from ..services.audit import audit
from ..storage import get_repos

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXT = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _doc_out(d: m.Document) -> dict:
    out = d.model_dump(mode="json", exclude={"stored_filename"})
    out["file_endpoint"] = f"/api/documents/{d.id}/file"  # authenticated, never a public URL
    return out


def _load_doc(doc_id: str, cu: CurrentUser) -> m.Document:
    d = get_repos().documents.get(doc_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    ensure_patient_access(cu, d.patient_id, m.Scope.documents)
    return d


@router.post("/upload", status_code=201, summary="Upload a PDF/JPG/PNG (validated by extension, magic bytes, size)")
async def upload(
    file: UploadFile = File(...),
    category: m.DocumentCategory = Form(m.DocumentCategory.other),
    title: Optional[str] = Form(None, max_length=150),
    document_date: Optional[date] = Form(None),
    doctor_name: Optional[str] = Form(None, max_length=120),
    hospital: Optional[str] = Form(None, max_length=150),
    notes: Optional[str] = Form(None, max_length=1000),
    analyze: bool = Form(True),
    cu: CurrentUser = Depends(require_patient),
) -> dict:
    settings = get_settings()
    name = file.filename or "upload"
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF, JPG, JPEG and PNG files are allowed")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB limit")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    sniffed = extraction.sniff_type(data[:16])
    if sniffed != ALLOWED_EXT[ext]:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content does not match its extension")

    doc_id = m.new_id("doc")
    stored = f"{doc_id}{'.jpg' if ext == '.jpeg' else ext}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / stored).write_bytes(data)
    safe_title = title or re.sub(r"[_\-]+", " ", name.rsplit(".", 1)[0]).strip().title()[:150]
    doc = m.Document(
        id=doc_id, patient_id=cu.user.patient_id, uploaded_by=cu.id, title=safe_title, category=category,  # type: ignore[arg-type]
        original_filename=name[:200], stored_filename=stored, content_type=sniffed, size_bytes=len(data),
        document_date=document_date, doctor_name=doctor_name, hospital=hospital, notes=notes,
    )
    r = get_repos()
    r.documents.add(doc)
    audit(cu, "document.uploaded", patient_id=doc.patient_id, resource_type="document", resource_id=doc.id,
          detail=f"{doc.title} ({doc.category}, {len(data)} bytes)")
    result: dict = {"document": _doc_out(doc), "extraction": None}
    if analyze:
        ext_rec = run_analysis(doc, cu)
        result["document"] = _doc_out(r.documents.require(doc.id))
        result["extraction"] = ext_rec.model_dump(mode="json")
    return result


def run_analysis(doc: m.Document, cu: CurrentUser) -> m.Extraction:
    r = get_repos()
    for old in r.extractions.find(document_id=doc.id, status="pending_review"):
        r.extractions.delete(old.id)
    ext_rec = extraction.analyze(doc)
    r.extractions.add(ext_rec)
    doc.extraction_status = "pending_review"
    doc.extraction_id = ext_rec.id
    r.documents.update(doc)
    audit(cu, "document.analyzed", patient_id=doc.patient_id, resource_type="document", resource_id=doc.id,
          detail=f"method={ext_rec.method}, confidence={ext_rec.overall_confidence}")
    return ext_rec


@router.get("", summary="List documents with search and filters")
def list_documents(
    cu: CurrentUser = Depends(get_current_user),
    patient_id: Optional[str] = None,
    q: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    doctor: Optional[str] = None,
) -> dict:
    pid = resolve_patient_id(cu, patient_id)
    ensure_patient_access(cu, pid, m.Scope.documents)
    docs = get_repos().documents.find(patient_id=pid)
    if category:
        docs = [d for d in docs if d.category in category.split(",")]
    if date_from:
        docs = [d for d in docs if d.document_date and d.document_date >= date_from]
    if date_to:
        docs = [d for d in docs if d.document_date and d.document_date <= date_to]
    if doctor:
        docs = [d for d in docs if doctor.lower() in (d.doctor_name or "").lower()]
    if q:
        ql = q.lower()
        docs = [d for d in docs if ql in " ".join(filter(None, [d.title, d.doctor_name, d.hospital, d.notes,
                                                                 d.original_filename, d.category, *d.tags])).lower()]
    docs.sort(key=lambda d: (d.document_date or d.uploaded_at.date()), reverse=True)
    return {"documents": [_doc_out(d) for d in docs], "count": len(docs),
            "max_upload_mb": get_settings().max_upload_mb,
            "categories": [c.value for c in m.DocumentCategory]}


@router.get("/{doc_id}")
def get_document(doc_id: str, cu: CurrentUser = Depends(get_current_user)) -> dict:
    d = _load_doc(doc_id, cu)
    ext = get_repos().extractions.get(d.extraction_id) if d.extraction_id else None
    return {"document": _doc_out(d), "extraction": ext.model_dump(mode="json") if ext else None}


@router.get("/{doc_id}/file", summary="Download/preview the file (requires auth + consent)")
def get_file(doc_id: str, cu: CurrentUser = Depends(get_current_user), download: bool = False) -> FileResponse:
    d = _load_doc(doc_id, cu)
    path = get_settings().upload_dir / d.stored_filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing from local demo storage")
    audit(cu, "document.downloaded" if download else "document.viewed", patient_id=d.patient_id,
          resource_type="document", resource_id=d.id)
    return FileResponse(path, media_type=d.content_type, filename=d.original_filename if download else None,
                        headers={"Cache-Control": "private, no-store"})


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=150)
    category: Optional[m.DocumentCategory] = None
    document_date: Optional[date] = None
    doctor_name: Optional[str] = Field(default=None, max_length=120)
    hospital: Optional[str] = Field(default=None, max_length=150)
    notes: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[list[str]] = None


@router.patch("/{doc_id}")
def update_document(doc_id: str, body: DocumentUpdate, cu: CurrentUser = Depends(require_patient)) -> dict:
    d = _load_doc(doc_id, cu)
    upd = d.model_copy(update={k: v for k, v in body.model_dump().items() if v is not None})
    get_repos().documents.update(upd)
    audit(cu, "document.updated", patient_id=d.patient_id, resource_type="document", resource_id=d.id)
    return _doc_out(upd)


@router.delete("/{doc_id}", summary="Delete a document (demo). Linked confirmed records keep a dangling reference.")
def delete_document(doc_id: str, cu: CurrentUser = Depends(require_patient)) -> dict:
    d = _load_doc(doc_id, cu)
    r = get_repos()
    r.documents.delete(d.id)
    for e in r.extractions.find(document_id=d.id):
        r.extractions.delete(e.id)
    (get_settings().upload_dir / d.stored_filename).unlink(missing_ok=True)
    audit(cu, "document.deleted", patient_id=d.patient_id, resource_type="document", resource_id=d.id, detail=d.title)
    return {"deleted": True, "id": d.id}


@router.post("/{doc_id}/analyze", summary="(Re)run extraction; result needs user review")
def analyze_document(doc_id: str, cu: CurrentUser = Depends(require_patient)) -> dict:
    d = _load_doc(doc_id, cu)
    return run_analysis(d, cu).model_dump(mode="json")


class ConfirmIn(BaseModel):
    category: Optional[m.DocumentCategory] = None
    consultation_date: Optional[date] = None
    doctor_name: Optional[str] = Field(default=None, max_length=120)
    hospital: Optional[str] = Field(default=None, max_length=150)
    diagnosis: Optional[str] = Field(default=None, max_length=300)
    allergies: Optional[str] = Field(default=None, max_length=300)
    medications: list[m.ExtractedMedication] = Field(default_factory=list, max_length=30)
    labs: list[m.ExtractedLab] = Field(default_factory=list, max_length=60)


@router.post("/{doc_id}/confirm-extraction", summary="Save user-reviewed fields into the health record")
def confirm_extraction(doc_id: str, body: ConfirmIn, cu: CurrentUser = Depends(require_patient)) -> dict:
    d = _load_doc(doc_id, cu)
    r = get_repos()
    ext = r.extractions.get(d.extraction_id) if d.extraction_id else None
    the_date = body.consultation_date or d.document_date or date.today()
    created = {"observations": 0, "medications": 0, "allergies": 0, "conditions": 0, "prescription": None}

    labs_added = []
    for lab in body.labs:
        if lab.value is None or not lab.test_name.strip():
            continue
        code = extraction.lab_code_for(lab.test_name) or re.sub(r"[^a-z0-9]+", "_", lab.test_name.lower()).strip("_")
        lo, hi = extraction.parse_reference(lab.reference_range)
        labs_added.append(m.Observation(
            id=m.new_id("obs"), patient_id=d.patient_id, code=code, name=lab.test_name.strip(), value=lab.value,
            unit=(lab.unit or "").strip(), observed_on=the_date, reference_low=lo, reference_high=hi,
            reference_text=lab.reference_range, panel="Laboratory", source_document_id=d.id, source_label=d.title,
            verified=True,
        ))
    r.observations.add_many(labs_added)
    created["observations"] = len(labs_added)

    meds = [x for x in body.medications if x.name.strip()]
    if meds:
        items = [m.PrescriptionItem(name=x.name, dosage=x.dosage or "not stated", frequency=x.frequency or "not stated",
                                    duration=x.duration) for x in meds]
        rx = m.Prescription(id=m.new_id("rx"), patient_id=d.patient_id, doctor_name=body.doctor_name or "Not recorded",
                            issued_on=the_date, items=items, status="issued", source_document_id=d.id)
        r.prescriptions.add(rx)
        created["prescription"] = rx.id
        for x in meds:
            med = m.Medication(
                id=m.new_id("med"), patient_id=d.patient_id, name=f"{x.name} {x.dosage or ''}".strip(),
                generic_name=x.name.lower().split()[0], dosage=x.dosage, frequency=x.frequency, duration=x.duration,
                start_date=the_date, status="active", prescribed_by=body.doctor_name, source_document_id=d.id,
                source_prescription_id=rx.id, verified=True,
                notes="Added from a user-confirmed document extraction. Drug class not yet classified.",
            )
            r.medications.add(med)
            r.medication_events.add(m.MedicationEvent(
                id=m.new_id("mev"), patient_id=d.patient_id, medication_id=med.id, event_date=the_date,
                event_type="started", description=f"{med.name} recorded from document '{d.title}'",
                by=body.doctor_name))
        created["medications"] = len(meds)

    if body.allergies and body.allergies.strip().lower() not in ("none", "nil", "nkda", "no known allergies"):
        for sub in [s.strip() for s in re.split(r"[;,]", body.allergies) if s.strip()]:
            r.allergies.add(m.Allergy(id=m.new_id("alg"), patient_id=d.patient_id, substance=sub,
                                      recorded_on=the_date, source_document_id=d.id))
            created["allergies"] += 1

    if body.diagnosis:
        existing = {c.name.lower() for c in r.conditions.find(patient_id=d.patient_id)}
        for dx in [s.strip() for s in re.split(r";", body.diagnosis) if s.strip()]:
            if dx.lower() not in existing:
                r.conditions.add(m.Condition(id=m.new_id("cnd"), patient_id=d.patient_id, name=dx,
                                             diagnosed_on=the_date, diagnosed_by=body.doctor_name,
                                             source_document_id=d.id, notes="From confirmed document extraction"))
                created["conditions"] += 1

    d.category = body.category or d.category
    d.document_date = the_date
    d.doctor_name = body.doctor_name or d.doctor_name
    d.hospital = body.hospital or d.hospital
    d.extraction_status = "confirmed"
    r.documents.update(d)
    if ext:
        ext.status = "confirmed"
        ext.confirmed_by = cu.id
        from ..models import utcnow

        ext.confirmed_at = utcnow()
        r.extractions.update(ext)
    audit(cu, "extraction.confirmed", patient_id=d.patient_id, resource_type="document", resource_id=d.id,
          detail=", ".join(f"{k}={v}" for k, v in created.items() if v))
    return {"document": _doc_out(d), "created": created}


@router.post("/{doc_id}/skip-extraction")
def skip_extraction(doc_id: str, cu: CurrentUser = Depends(require_patient)) -> dict:
    d = _load_doc(doc_id, cu)
    r = get_repos()
    if d.extraction_id and (ext := r.extractions.get(d.extraction_id)):
        ext.status = "discarded"
        r.extractions.update(ext)
    d.extraction_status = "skipped"
    r.documents.update(d)
    audit(cu, "extraction.skipped", patient_id=d.patient_id, resource_type="document", resource_id=d.id)
    return _doc_out(d)
