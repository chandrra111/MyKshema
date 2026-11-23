export type Role = "patient" | "doctor";
export type Scope = "history" | "medications" | "allergies" | "labs" | "documents" | "consultations";
export const ALL_SCOPES: Scope[] = ["history", "medications", "allergies", "labs", "documents", "consultations"];
export const SCOPE_LABEL: Record<Scope, string> = {
  history: "Medical history",
  medications: "Medications",
  allergies: "Allergies",
  labs: "Lab results & vitals",
  documents: "Documents (files)",
  consultations: "Consultations",
};

export interface PatientProfile {
  id: string;
  full_name: string;
  date_of_birth: string;
  sex: string;
  blood_group?: string | null;
  height_cm?: number | null;
  phone?: string | null;
  city?: string | null;
  emergency_contact?: string | null;
  age?: number;
  shared_scopes?: Scope[];
}

export interface DoctorProfile {
  id: string;
  full_name: string;
  specialty: string;
  hospital: string;
  city: string;
  registration_no: string;
  years_experience: number;
  bio?: string | null;
  has_portal_login?: boolean;
  active_grant?: Grant | null;
}

export interface User {
  id: string;
  email: string;
  role: Role;
  display_name: string;
  patient_id?: string | null;
  doctor_id?: string | null;
  profile?: PatientProfile | DoctorProfile | null;
}

export interface Doc {
  id: string;
  patient_id: string;
  title: string;
  category: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  document_date?: string | null;
  doctor_name?: string | null;
  hospital?: string | null;
  notes?: string | null;
  tags: string[];
  uploaded_at: string;
  extraction_status: "not_started" | "pending_review" | "confirmed" | "skipped";
  extraction_id?: string | null;
  file_endpoint: string;
  is_demo: boolean;
}

export interface EField { value: string | null; confidence: number }
export interface EMed { name: string; dosage?: string | null; frequency?: string | null; duration?: string | null }
export interface ELab { test_name: string; value?: number | null; value_text?: string | null; unit?: string | null; reference_range?: string | null }
export interface Extraction {
  id: string;
  document_id: string;
  method: "pdf_text_rules" | "live_ai" | "demo_template" | "manual";
  method_label: string;
  raw_text_excerpt?: string | null;
  overall_confidence: number;
  status: string;
  warnings: string[];
  fields: {
    category: EField; consultation_date: EField; doctor_name: EField; hospital: EField;
    diagnosis: EField; allergies: EField; medications: EMed[]; labs: ELab[];
  };
}

export interface TimelineEvent {
  id: string;
  date: string;
  type: "consultation" | "prescription" | "lab_report" | "document" | "medication" | "allergy" | "diagnosis";
  type_label: string;
  title: string;
  doctor?: string | null;
  hospital?: string | null;
  summary?: string | null;
  diagnoses?: string[];
  medications?: string[];
  flags?: string[];
  follow_up?: string | null;
  source_document_id?: string | null;
  source_document_title?: string | null;
  created_via?: string;
  status?: string;
}

export interface Medication {
  id: string;
  name: string;
  generic_name?: string | null;
  brand_name?: string | null;
  drug_class?: string | null;
  dosage?: string | null;
  frequency?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  duration?: string | null;
  status: "active" | "patient_reported" | "discontinued" | "completed" | "proposed";
  prescribed_by?: string | null;
  source_document_id?: string | null;
  source_document_title?: string | null;
  adherence?: string | null;
  notes?: string | null;
  verified: boolean;
}

export interface Flag {
  id: string;
  type: string;
  severity: "high" | "moderate" | "low" | "info";
  title: string;
  detail: string;
  medication_names: string[];
  evidence: string;
  requires_clinician_review: boolean;
}

export interface MedEvent { id: string; event_date: string; event_type: string; description: string; by?: string | null }

export interface TrendPoint { date: string; value: number; status: string; source_document_id?: string | null; source_label?: string | null }
export interface Trend {
  code: string;
  name: string;
  unit: string;
  panel?: string | null;
  points: TrendPoint[];
  latest: { date: string; value: number; status: string };
  previous?: { date: string; value: number } | null;
  change?: number | null;
  reference?: { low?: number | null; high?: number | null; text?: string | null } | null;
  trend?: { per_month: number; ci95_low: number; ci95_high: number; n_points: number; method: string } | null;
}

export interface Reminder { kind: string; priority: "high" | "medium" | "low"; due: string; title: string; detail: string; basis: string }

export interface Citation { type: string; id: string; label: string; date?: string | null }
export interface AIResult {
  mode: "live" | "demo";
  label: string;
  kind: string;
  answer: string;
  citations: Citation[];
  disclaimer: string;
  flags?: Flag[];
  table?: { columns: string[]; rows: string[][] };
}

export interface Grant {
  id: string;
  patient_id: string;
  doctor_id: string;
  scopes: Scope[];
  granted_at: string;
  expires_at: string;
  revoked_at?: string | null;
  state?: "active" | "revoked" | "expired";
  doctor?: DoctorProfile | null;
  patient_name?: string | null;
}

export interface AccessRequest {
  id: string;
  patient_id: string;
  doctor_id: string;
  initiated_by: Role;
  requested_scopes: Scope[];
  reason?: string | null;
  duration_hours: number;
  status: "pending" | "approved" | "denied" | "cancelled";
  created_at: string;
  decided_at?: string | null;
  doctor?: DoctorProfile | null;
  patient_name?: string | null;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor_name?: string | null;
  actor_role?: string | null;
  action: string;
  resource_type?: string | null;
  detail?: string | null;
  outcome: "success" | "denied" | "error";
}

export interface RxItem { name: string; dosage: string; frequency: string; duration?: string | null; instructions?: string | null }
export interface Consultation {
  id: string;
  patient_id: string;
  doctor_name: string;
  hospital?: string | null;
  consultation_date: string;
  reason?: string | null;
  notes: string;
  diagnoses: string[];
  follow_up?: string | null;
  follow_up_date?: string | null;
  created_via: "seed" | "doctor_portal";
  source_document_id?: string | null;
  source_document_title?: string | null;
  prescription?: { id: string; status: string; items: RxItem[] } | null;
}

export interface Condition { id: string; name: string; status: string; diagnosed_on?: string | null; diagnosed_by?: string | null }
export interface Allergy { id: string; substance: string; reaction?: string | null; severity: string; recorded_on?: string | null }
