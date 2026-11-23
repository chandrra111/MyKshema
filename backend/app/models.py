"""Typed domain models (Pydantic). Storage-agnostic: the JSON adapter stores
these as dicts today; a future PostgreSQL adapter maps them to tables."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Record(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    id: str
    is_demo: bool = True  # every record in this prototype is synthetic


# ---------------------------------------------------------------- identity
class Role(str, Enum):
    patient = "patient"
    doctor = "doctor"


class User(Record):
    email: str
    password_hash: str
    role: Role
    display_name: str
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None


class PatientProfile(Record):
    user_id: str
    full_name: str
    date_of_birth: date
    sex: Literal["female", "male", "other", "unspecified"] = "unspecified"
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    emergency_contact: Optional[str] = None


class DoctorProfile(Record):
    user_id: Optional[str] = None
    full_name: str
    specialty: str
    hospital: str
    city: str
    registration_no: str  # fictional
    years_experience: int = 0
    bio: Optional[str] = None


# ---------------------------------------------------------------- consent / access
class Scope(str, Enum):
    history = "history"
    medications = "medications"
    allergies = "allergies"
    labs = "labs"
    documents = "documents"
    consultations = "consultations"


ALL_SCOPES = [s.value for s in Scope]


class AccessRequest(Record):
    patient_id: str
    doctor_id: str
    initiated_by: Role
    requested_scopes: list[Scope]
    reason: Optional[str] = None
    duration_hours: int = 72
    status: Literal["pending", "approved", "denied", "cancelled"] = "pending"
    created_at: datetime = Field(default_factory=utcnow)
    decided_at: Optional[datetime] = None
    grant_id: Optional[str] = None


class AccessGrant(Record):
    patient_id: str
    doctor_id: str
    scopes: list[Scope]
    granted_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    request_id: Optional[str] = None

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        return self.revoked_at is None and self.expires_at > now


# ---------------------------------------------------------------- documents
class DocumentCategory(str, Enum):
    prescription = "prescription"
    blood_report = "blood_report"
    diagnostic_report = "diagnostic_report"
    xray = "xray"
    mri = "mri"
    ct_scan = "ct_scan"
    discharge_summary = "discharge_summary"
    consultation_note = "consultation_note"
    vaccination_record = "vaccination_record"
    other = "other"


class Document(Record):
    patient_id: str
    uploaded_by: str  # user id
    title: str
    category: DocumentCategory
    original_filename: str
    stored_filename: str  # private, never exposed as a public URL
    content_type: str
    size_bytes: int
    document_date: Optional[date] = None
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    uploaded_at: datetime = Field(default_factory=utcnow)
    extraction_status: Literal["not_started", "pending_review", "confirmed", "skipped"] = "not_started"
    extraction_id: Optional[str] = None


class ExtractedMedication(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class ExtractedLab(BaseModel):
    test_name: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class ExtractedField(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0  # 0..1


class ExtractionFields(BaseModel):
    category: ExtractedField = Field(default_factory=ExtractedField)
    consultation_date: ExtractedField = Field(default_factory=ExtractedField)
    doctor_name: ExtractedField = Field(default_factory=ExtractedField)
    hospital: ExtractedField = Field(default_factory=ExtractedField)
    diagnosis: ExtractedField = Field(default_factory=ExtractedField)
    allergies: ExtractedField = Field(default_factory=ExtractedField)
    medications: list[ExtractedMedication] = Field(default_factory=list)
    labs: list[ExtractedLab] = Field(default_factory=list)


class Extraction(Record):
    document_id: str
    patient_id: str
    method: Literal["pdf_text_rules", "live_ai", "demo_template", "manual"]
    method_label: str
    raw_text_excerpt: Optional[str] = None
    fields: ExtractionFields
    overall_confidence: float
    status: Literal["pending_review", "confirmed", "discarded"] = "pending_review"
    created_at: datetime = Field(default_factory=utcnow)
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- clinical
class Condition(Record):
    patient_id: str
    name: str
    status: Literal["active", "resolved", "suspected"] = "active"
    diagnosed_on: Optional[date] = None
    diagnosed_by: Optional[str] = None
    source_document_id: Optional[str] = None
    source_consultation_id: Optional[str] = None
    notes: Optional[str] = None


class Allergy(Record):
    patient_id: str
    substance: str
    drug_class: Optional[str] = None
    reaction: Optional[str] = None
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    recorded_on: Optional[date] = None
    source_document_id: Optional[str] = None


class MedicationStatus(str, Enum):
    active = "active"  # prescribed, currently taking
    patient_reported = "patient_reported"  # current, self-reported (OTC/supplement)
    discontinued = "discontinued"
    completed = "completed"  # historical, course finished
    proposed = "proposed"  # proposed by a doctor in a demo consultation


class Medication(Record):
    patient_id: str
    name: str  # as written
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    drug_class: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = "oral"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration: Optional[str] = None
    status: MedicationStatus
    prescribed_by: Optional[str] = None  # doctor name
    prescriber_doctor_id: Optional[str] = None
    source_document_id: Optional[str] = None
    source_prescription_id: Optional[str] = None
    adherence: Optional[Literal["taking_as_prescribed", "sometimes_missed", "often_missed", "stopped_on_own"]] = None
    notes: Optional[str] = None
    verified: bool = True  # False when it came from unconfirmed patient report


class MedicationEvent(Record):
    patient_id: str
    medication_id: str
    event_date: date
    event_type: Literal["started", "dose_changed", "stopped", "completed", "reported", "proposed"]
    description: str
    by: Optional[str] = None


class Observation(Record):
    """A lab result or vital sign measurement."""
    patient_id: str
    code: str  # e.g. hba1c, fasting_glucose, bp_systolic
    name: str
    value: float
    unit: str
    observed_on: date
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None  # documented range as printed on report
    panel: Optional[str] = None
    source_document_id: Optional[str] = None
    source_label: Optional[str] = None
    verified: bool = True


class PrescriptionItem(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: Optional[str] = None
    instructions: Optional[str] = None

    @field_validator("name", "dosage", "frequency")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class Consultation(Record):
    patient_id: str
    doctor_id: Optional[str] = None
    doctor_name: str
    hospital: Optional[str] = None
    consultation_date: date
    reason: Optional[str] = None
    notes: str
    diagnoses: list[str] = Field(default_factory=list)
    follow_up: Optional[str] = None
    follow_up_date: Optional[date] = None
    prescription_id: Optional[str] = None
    source_document_id: Optional[str] = None
    created_via: Literal["seed", "doctor_portal"] = "seed"
    created_at: datetime = Field(default_factory=utcnow)


class Prescription(Record):
    patient_id: str
    doctor_id: Optional[str] = None
    doctor_name: str
    consultation_id: Optional[str] = None
    issued_on: date
    items: list[PrescriptionItem]
    status: Literal["issued", "proposed_demo"] = "issued"
    authored_by: Literal["doctor"] = "doctor"  # never AI
    source_document_id: Optional[str] = None


class AISummary(Record):
    patient_id: str
    requested_by: str
    kind: str
    mode: Literal["live", "demo"]
    content: str
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(Record):
    timestamp: datetime = Field(default_factory=utcnow)
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    patient_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    outcome: Literal["success", "denied", "error"] = "success"
