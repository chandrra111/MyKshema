"""Synthetic demo data. EVERYTHING HERE IS FICTIONAL.

People, doctors, hospitals, registration numbers and results are invented
for the BUILD 2036 hackathon demo. Do not load real patient data.
"""
from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta, timezone

from . import models as m
from .config import get_settings
from .security import hash_password
from .services.pdfgen import make_pdf
from .storage import Repos, get_repos

DEMO_PASSWORD = "Demo@2036"
FICTION = "SYNTHETIC DEMO RECORD - FICTIONAL PATIENT - NOT FOR CLINICAL USE"

# Fixed IDs keep demo links/screenshots stable across resets.
P_ANANYA, P_RAHUL = "pat_ananya", "pat_rahul"
D_MEERA, D_ARJUN, D_KAVYA, D_FARHAN, D_LAKSHMI = "doc_meera", "doc_arjun", "doc_kavya", "doc_farhan", "doc_lakshmi"

HOSP = {
    D_MEERA: "Lotus Endocrine & Diabetes Centre",
    D_ARJUN: "Heartline Cardiac Institute",
    D_KAVYA: "Sunrise Family Clinic",
    D_FARHAN: "Riverbend Kidney Care",
    D_LAKSHMI: "ClearView Eye Hospital",
}
LAB = "CityCare Diagnostics (fictional)"


class _Seeder:
    def __init__(self, repos: Repos, today: date):
        self.r = repos
        self.today = today
        self.settings = get_settings()
        self.docs: list[m.Document] = []
        self.obs: list[m.Observation] = []
        self.meds: list[m.Medication] = []
        self.events: list[m.MedicationEvent] = []
        self.consults: list[m.Consultation] = []
        self.rx: list[m.Prescription] = []
        self.conditions: list[m.Condition] = []
        self.allergies: list[m.Allergy] = []
        self._n = 0

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}_seed{self._n:04d}"

    # -------------------------------------------------- documents
    def doc(self, patient_id: str, uploader: str, title: str, category: str, d: date, lines: list[str],
            doctor: str | None = None, hospital: str | None = None, tags: list[str] | None = None) -> str:
        doc_id = self._id("doc")
        stored = f"{doc_id}.pdf"
        pdf = make_pdf([title, FICTION, ""] + lines, title=title)
        (self.settings.upload_dir / stored).write_bytes(pdf)
        self.docs.append(m.Document(
            id=doc_id, patient_id=patient_id, uploaded_by=uploader, title=title, category=category,
            original_filename=title.lower().replace(" ", "_").replace("/", "-") + ".pdf", stored_filename=stored,
            content_type="application/pdf", size_bytes=len(pdf), document_date=d, doctor_name=doctor,
            hospital=hospital, tags=tags or [], extraction_status="confirmed",
            uploaded_at=datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
        ))
        return doc_id

    # -------------------------------------------------- labs
    REF = {
        "hba1c": ("HbA1c", "%", 4.0, 5.6, "4.0 - 5.6 %"),
        "fasting_glucose": ("Fasting Blood Glucose", "mg/dL", 70, 99, "70 - 99 mg/dL"),
        "total_cholesterol": ("Total Cholesterol", "mg/dL", None, 200, "< 200 mg/dL"),
        "ldl": ("LDL Cholesterol", "mg/dL", None, 100, "< 100 mg/dL"),
        "hdl": ("HDL Cholesterol", "mg/dL", 50, None, "> 50 mg/dL"),
        "triglycerides": ("Triglycerides", "mg/dL", None, 150, "< 150 mg/dL"),
        "creatinine": ("Serum Creatinine", "mg/dL", 0.5, 1.1, "0.5 - 1.1 mg/dL"),
        "egfr": ("eGFR", "mL/min/1.73m2", 90, None, ">= 90 mL/min/1.73m2"),
        "vitamin_d": ("Vitamin D (25-OH)", "ng/mL", 30, 100, "30 - 100 ng/mL"),
        "urine_acr": ("Urine Albumin/Creatinine Ratio", "mg/g", None, 30, "< 30 mg/g"),
        "tsh": ("TSH", "uIU/mL", 0.4, 4.0, "0.4 - 4.0 uIU/mL"),
    }

    def lab_report(self, patient_id: str, uploader: str, d: date, values: dict[str, float], ordered_by: str) -> str:
        lines = [f"Laboratory: {LAB}", f"Report date: {d.isoformat()}", f"Referring doctor: {ordered_by}", "",
                 "Test | Result | Unit | Reference range"]
        for code, val in values.items():
            name, unit, *_r, text = self.REF[code]
            lines.append(f"{name} | {val:g} | {unit} | {text}")
        title = f"Blood Report {d.strftime('%b %Y')}"
        doc_id = self.doc(patient_id, uploader, title, "blood_report", d, lines, doctor=ordered_by, hospital=LAB,
                          tags=["lab"])
        for code, val in values.items():
            name, unit, lo, hi, text = self.REF[code]
            self.obs.append(m.Observation(
                id=self._id("obs"), patient_id=patient_id, code=code, name=name, value=val, unit=unit,
                observed_on=d, reference_low=lo, reference_high=hi, reference_text=text, panel="Laboratory",
                source_document_id=doc_id, source_label=title,
            ))
        return doc_id

    def vital(self, patient_id: str, d: date, code: str, name: str, value: float, unit: str,
              ref_low: float | None = None, ref_high: float | None = None, ref_text: str | None = None,
              source: str = "Home measurement log (patient-entered)") -> None:
        self.obs.append(m.Observation(
            id=self._id("obs"), patient_id=patient_id, code=code, name=name, value=value, unit=unit, observed_on=d,
            reference_low=ref_low, reference_high=ref_high, reference_text=ref_text, panel="Vitals",
            source_label=source, verified=True,
        ))

    # -------------------------------------------------- consultations / prescriptions
    def consult(self, patient_id: str, doctor_id: str, doctor_name: str, d: date, reason: str, notes: str,
                diagnoses: list[str], follow_up: str | None = None, follow_up_date: date | None = None,
                rx_items: list[m.PrescriptionItem] | None = None, uploader: str = "") -> tuple[str, str | None]:
        cid = self._id("con")
        note_lines = [f"Doctor: {doctor_name}", f"Facility: {HOSP[doctor_id]}", f"Date: {d.isoformat()}",
                      f"Reason for visit: {reason}", "", "Clinical notes:", notes, "",
                      "Diagnosis: " + ("; ".join(diagnoses) if diagnoses else "-")]
        rx_id = None
        rx_doc = None
        if rx_items:
            rx_id = self._id("rx")
            rx_lines = [f"Prescriber: {doctor_name}", f"Facility: {HOSP[doctor_id]}", f"Date: {d.isoformat()}",
                        "Diagnosis: " + "; ".join(diagnoses), "", "Rx:"]
            for it in rx_items:
                rx_lines.append(f"- {it.name} {it.dosage} | {it.frequency} | {it.duration or 'until review'}")
            rx_doc = self.doc(patient_id, uploader, f"Prescription {doctor_name.split()[-1]} {d.strftime('%b %Y')}",
                              "prescription", d, rx_lines, doctor=doctor_name, hospital=HOSP[doctor_id], tags=["rx"])
            self.rx.append(m.Prescription(
                id=rx_id, patient_id=patient_id, doctor_id=doctor_id, doctor_name=doctor_name, consultation_id=cid,
                issued_on=d, items=rx_items, status="issued", source_document_id=rx_doc,
            ))
        if follow_up:
            note_lines.append(f"Follow-up: {follow_up}")
        note_doc = self.doc(patient_id, uploader, f"Consultation Note {d.strftime('%d %b %Y')}", "consultation_note",
                            d, note_lines, doctor=doctor_name, hospital=HOSP[doctor_id])
        self.consults.append(m.Consultation(
            id=cid, patient_id=patient_id, doctor_id=doctor_id, doctor_name=doctor_name, hospital=HOSP[doctor_id],
            consultation_date=d, reason=reason, notes=notes, diagnoses=diagnoses, follow_up=follow_up,
            follow_up_date=follow_up_date, prescription_id=rx_id, source_document_id=note_doc, created_via="seed",
            created_at=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
        ))
        return cid, rx_doc

    def med(self, patient_id: str, name: str, generic: str, drug_class: str | None, dosage: str | None,
            freq: str | None, start: date | None, status: str, by: str | None = None, doctor_id: str | None = None,
            end: date | None = None, duration: str | None = None, source_doc: str | None = None,
            brand: str | None = None, adherence: str | None = None, notes: str | None = None,
            verified: bool = True) -> str:
        mid = self._id("med")
        self.meds.append(m.Medication(
            id=mid, patient_id=patient_id, name=name, generic_name=generic, brand_name=brand, drug_class=drug_class,
            dosage=dosage, frequency=freq, start_date=start, end_date=end, duration=duration, status=status,
            prescribed_by=by, prescriber_doctor_id=doctor_id, source_document_id=source_doc, adherence=adherence,
            notes=notes, verified=verified,
        ))
        if start:
            etype = "reported" if status == "patient_reported" else "started"
            self.event(patient_id, mid, start, etype, f"{name} {dosage or ''} {freq or ''}".strip()
                       + (f" started by {by}" if by else " reported by patient"), by)
        return mid

    def event(self, patient_id: str, mid: str, d: date, etype: str, desc: str, by: str | None = None) -> None:
        self.events.append(m.MedicationEvent(id=self._id("mev"), patient_id=patient_id, medication_id=mid,
                                             event_date=d, event_type=etype, description=desc, by=by))


def _ago(today: date, days: int) -> date:
    return today - timedelta(days=days)


def seed(repos: Repos | None = None, today: date | None = None) -> dict[str, int]:
    """Wipe and re-create all demo data. Returns per-collection counts."""
    repos = repos or get_repos()
    settings = get_settings()
    today = today or date.today()
    repos.store.clear()
    if settings.upload_dir.exists():
        shutil.rmtree(settings.upload_dir)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / ".gitkeep").write_text("", encoding="utf-8")

    s = _Seeder(repos, today)
    pw = hash_password(DEMO_PASSWORD)

    # ---------------- users / profiles
    doctors = [
        m.DoctorProfile(id=D_MEERA, user_id="usr_meera", full_name="Dr. Meera Iyer", specialty="Endocrinology",
                        hospital=HOSP[D_MEERA], city="Bengaluru", registration_no="DEMO-KMC-40211", years_experience=14,
                        bio="Diabetes and thyroid care. Fictional demo doctor."),
        m.DoctorProfile(id=D_ARJUN, user_id="usr_arjun", full_name="Dr. Arjun Shah", specialty="Cardiology",
                        hospital=HOSP[D_ARJUN], city="Bengaluru", registration_no="DEMO-KMC-38870", years_experience=18,
                        bio="Preventive cardiology. Fictional demo doctor."),
        m.DoctorProfile(id=D_KAVYA, user_id="usr_kavya", full_name="Dr. Kavya Nair", specialty="General Medicine",
                        hospital=HOSP[D_KAVYA], city="Bengaluru", registration_no="DEMO-KMC-51902", years_experience=9,
                        bio="Family physician. Fictional demo doctor."),
        m.DoctorProfile(id=D_FARHAN, full_name="Dr. Farhan Qureshi", specialty="Nephrology", hospital=HOSP[D_FARHAN],
                        city="Mysuru", registration_no="DEMO-KMC-29934", years_experience=21,
                        bio="Kidney health. Directory-only fictional doctor."),
        m.DoctorProfile(id=D_LAKSHMI, full_name="Dr. Lakshmi Venkat", specialty="Ophthalmology",
                        hospital=HOSP[D_LAKSHMI], city="Chennai", registration_no="DEMO-TNMC-77120",
                        years_experience=12, bio="Diabetic retinopathy screening. Directory-only fictional doctor."),
    ]
    users = [
        m.User(id="usr_ananya", email="ananya.rao@demo.mykshema.test", password_hash=pw, role="patient",
               display_name="Ananya Rao", patient_id=P_ANANYA),
        m.User(id="usr_rahul", email="rahul.menon@demo.mykshema.test", password_hash=pw, role="patient",
               display_name="Rahul Menon", patient_id=P_RAHUL),
        m.User(id="usr_meera", email="meera.iyer@demo.mykshema.test", password_hash=pw, role="doctor",
               display_name="Dr. Meera Iyer", doctor_id=D_MEERA),
        m.User(id="usr_arjun", email="arjun.shah@demo.mykshema.test", password_hash=pw, role="doctor",
               display_name="Dr. Arjun Shah", doctor_id=D_ARJUN),
        m.User(id="usr_kavya", email="kavya.nair@demo.mykshema.test", password_hash=pw, role="doctor",
               display_name="Dr. Kavya Nair", doctor_id=D_KAVYA),
    ]
    patients = [
        m.PatientProfile(id=P_ANANYA, user_id="usr_ananya", full_name="Ananya Rao", date_of_birth=date(1973, 6, 14),
                         sex="female", blood_group="B+", height_cm=160, phone="+91-90000-00001 (fictional)",
                         city="Bengaluru", emergency_contact="Vikram Rao (spouse) +91-90000-00002 (fictional)"),
        m.PatientProfile(id=P_RAHUL, user_id="usr_rahul", full_name="Rahul Menon", date_of_birth=date(1988, 2, 3),
                         sex="male", blood_group="O+", height_cm=176, phone="+91-90000-00003 (fictional)",
                         city="Kochi", emergency_contact="Asha Menon (sister) +91-90000-00004 (fictional)"),
    ]

    # ---------------- Ananya: ~2 years of history
    A, U = P_ANANYA, "usr_ananya"
    t = today
    d0 = _ago(t, 735)  # first visit ~2 years ago

    def dd(days_after_start: int) -> date:
        return d0 + timedelta(days=days_after_start)

    s.consult(A, D_KAVYA, "Dr. Kavya Nair", dd(0), "Fatigue, increased thirst and frequent urination for 6 weeks",
              "Complains of tiredness and polyuria. No chest pain. BMI 28.9. BP 144/90. Advised fasting labs and lipid "
              "profile.", ["Suspected diabetes mellitus - awaiting labs"], "Review with lab reports in 1 week",
              dd(7), uploader=U)
    s.lab_report(A, U, dd(2), {"hba1c": 8.4, "fasting_glucose": 168, "total_cholesterol": 228, "ldl": 142, "hdl": 42,
                               "triglycerides": 190, "creatinine": 0.9, "egfr": 82, "tsh": 2.1}, "Dr. Kavya Nair")
    _, rx1 = s.consult(A, D_KAVYA, "Dr. Kavya Nair", dd(7), "Lab review",
                       "HbA1c 8.4% and fasting glucose 168 mg/dL confirm type 2 diabetes. LDL 142 mg/dL. Diet and "
                       "exercise counselling given. Started metformin and atorvastatin.",
                       ["Type 2 diabetes mellitus", "Dyslipidemia"], "Endocrinology referral; repeat HbA1c in 3 months",
                       dd(97), [m.PrescriptionItem(name="Metformin", dosage="500 mg", frequency="Twice daily after meals",
                                                   duration="Until review"),
                                m.PrescriptionItem(name="Atorvastatin", dosage="10 mg", frequency="Once daily at night",
                                                   duration="Until review")], uploader=U)
    met = s.med(A, "Metformin 500 mg", "metformin", "biguanide", "500 mg", "Twice daily", dd(7), "active",
                "Dr. Kavya Nair", D_KAVYA, source_doc=rx1, brand="Glycomet (example brand)",
                adherence="taking_as_prescribed")
    s.med(A, "Atorvastatin 10 mg", "atorvastatin", "statin", "10 mg", "Once daily at night", dd(7), "active",
          "Dr. Kavya Nair", D_KAVYA, source_doc=rx1, adherence="sometimes_missed",
          notes="Not explicitly stopped when rosuvastatin was started by cardiology.")
    s.conditions += [
        m.Condition(id=s._id("cnd"), patient_id=A, name="Type 2 diabetes mellitus", status="active",
                    diagnosed_on=dd(7), diagnosed_by="Dr. Kavya Nair"),
        m.Condition(id=s._id("cnd"), patient_id=A, name="Dyslipidemia", status="active", diagnosed_on=dd(7),
                    diagnosed_by="Dr. Kavya Nair"),
    ]

    _, rx_amox = s.consult(A, D_KAVYA, "Dr. Kavya Nair", dd(52), "Sore throat and fever for 3 days",
                           "Acute pharyngitis. Temp 38.4 C. Prescribed 5-day antibiotic course.",
                           ["Acute pharyngitis"], None, None,
                           [m.PrescriptionItem(name="Amoxicillin", dosage="500 mg", frequency="Three times daily",
                                               duration="5 days")], uploader=U)
    amox = s.med(A, "Amoxicillin 500 mg", "amoxicillin", "penicillin", "500 mg", "Three times daily", dd(52),
                 "discontinued", "Dr. Kavya Nair", D_KAVYA, end=dd(55), duration="5 days (stopped day 3)",
                 source_doc=rx_amox)
    s.event(A, amox, dd(55), "stopped", "Amoxicillin stopped on day 3 due to itchy rash", "Dr. Kavya Nair")
    s.allergies.append(m.Allergy(id=s._id("alg"), patient_id=A, substance="Penicillin (amoxicillin)",
                                 drug_class="penicillin", reaction="Itchy maculopapular rash", severity="moderate",
                                 recorded_on=dd(55)))

    s.lab_report(A, U, dd(96), {"hba1c": 8.1, "fasting_glucose": 152, "creatinine": 0.9, "egfr": 81},
                 "Dr. Meera Iyer")
    _, rx2 = s.consult(A, D_MEERA, "Dr. Meera Iyer", dd(104), "Endocrinology referral - diabetes management",
                       "HbA1c 8.1% on metformin 500 mg BD. Increase metformin to 1000 mg BD and add glimepiride 1 mg. "
                       "Clinic BP 146/92 - home BP monitoring advised. BP target documented: < 130/80 mmHg.",
                       ["Type 2 diabetes mellitus - suboptimal control", "Elevated blood pressure"],
                       "Repeat HbA1c in 3 months", dd(194),
                       [m.PrescriptionItem(name="Metformin", dosage="1000 mg", frequency="Twice daily after meals",
                                           duration="Until review"),
                        m.PrescriptionItem(name="Glimepiride", dosage="1 mg", frequency="Once daily before breakfast",
                                           duration="Until review")], uploader=U)
    s.event(A, met, dd(104), "dose_changed", "Metformin increased from 500 mg to 1000 mg twice daily", "Dr. Meera Iyer")
    for med in s.meds:
        if med.id == met:
            med.dosage, med.name, med.source_document_id, med.prescribed_by, med.prescriber_doctor_id = (
                "1000 mg", "Metformin 1000 mg", rx2, "Dr. Meera Iyer", D_MEERA)
    glim = s.med(A, "Glimepiride 1 mg", "glimepiride", "sulfonylurea", "1 mg", "Once daily before breakfast", dd(104),
                 "discontinued", "Dr. Meera Iyer", D_MEERA, source_doc=rx2)

    s.lab_report(A, U, dd(187), {"hba1c": 7.6, "fasting_glucose": 138}, "Dr. Meera Iyer")
    _, rx3 = s.consult(A, D_KAVYA, "Dr. Kavya Nair", dd(201), "Home BP readings persistently high",
                       "Home BP average 142/90 over 4 weeks. Starting ARB. Advised salt restriction.",
                       ["Essential hypertension"], "BP review in 3 months", dd(291),
                       [m.PrescriptionItem(name="Telmisartan", dosage="40 mg", frequency="Once daily morning",
                                           duration="Until review")], uploader=U)
    s.med(A, "Telmisartan 40 mg", "telmisartan", "angiotensin receptor blocker", "40 mg", "Once daily morning",
          dd(201), "active", "Dr. Kavya Nair", D_KAVYA, source_doc=rx3, adherence="taking_as_prescribed")
    s.conditions.append(m.Condition(id=s._id("cnd"), patient_id=A, name="Essential hypertension", status="active",
                                    diagnosed_on=dd(201), diagnosed_by="Dr. Kavya Nair"))

    s.lab_report(A, U, dd(279), {"hba1c": 7.3, "fasting_glucose": 131, "total_cholesterol": 201, "ldl": 118,
                                 "hdl": 45, "triglycerides": 165}, "Dr. Meera Iyer")
    s.consult(A, D_MEERA, "Dr. Meera Iyer", dd(286), "Diabetes follow-up",
              "HbA1c improving at 7.3%. Continue current regimen. Annual eye and kidney screening advised.",
              ["Type 2 diabetes mellitus - improving"], "Review in 3 months with HbA1c, kidney function and urine ACR",
              dd(376), uploader=U)

    s.lab_report(A, U, dd(370), {"hba1c": 7.0, "fasting_glucose": 124, "total_cholesterol": 190, "ldl": 108,
                                 "hdl": 47, "triglycerides": 150, "creatinine": 1.0, "egfr": 76, "urine_acr": 24},
                 "Dr. Meera Iyer")
    s.doc(A, U, "Treadmill Stress Test Report", "diagnostic_report", dd(388),
          [f"Facility: {HOSP[D_ARJUN]}", "Referring doctor: Dr. Arjun Shah", "Protocol: Bruce, 9.2 min, 10.1 METs",
           "Max HR 148 bpm (88% predicted). No ST-segment changes. No arrhythmia.",
           "Impression: Negative for inducible ischaemia at achieved workload."],
          doctor="Dr. Arjun Shah", hospital=HOSP[D_ARJUN], tags=["cardiology"])
    _, rx4 = s.consult(A, D_ARJUN, "Dr. Arjun Shah", dd(392), "Exertional chest discomfort",
                       "Atypical chest discomfort. ECG normal sinus rhythm. TMT negative for inducible ischaemia. "
                       "Given diabetes and LDL above target, starting rosuvastatin.",
                       ["Atypical chest pain - TMT negative", "Dyslipidemia"], "Cardiology review in 6 months",
                       dd(572), [m.PrescriptionItem(name="Rosuvastatin", dosage="10 mg", frequency="Once daily at night",
                                                    duration="Until review")], uploader=U)
    s.med(A, "Rosuvastatin 10 mg", "rosuvastatin", "statin", "10 mg", "Once daily at night", dd(392), "active",
          "Dr. Arjun Shah", D_ARJUN, source_doc=rx4, adherence="taking_as_prescribed",
          notes="Prescription does not state whether atorvastatin should be stopped.")

    s.lab_report(A, U, dd(461), {"hba1c": 6.9, "fasting_glucose": 118, "vitamin_d": 18}, "Dr. Meera Iyer")
    _, rx5 = s.consult(A, D_MEERA, "Dr. Meera Iyer", dd(468), "Diabetes follow-up; dizziness before lunch",
                       "Two self-reported low glucose episodes (62 and 58 mg/dL) before lunch. Glimepiride stopped. "
                       "Vitamin D 18 ng/mL - weekly supplementation for 8 weeks.",
                       ["Type 2 diabetes mellitus", "Hypoglycaemia episodes on sulfonylurea", "Vitamin D deficiency"],
                       "Repeat HbA1c in 3 months", dd(558),
                       [m.PrescriptionItem(name="Cholecalciferol", dosage="60000 IU", frequency="Once weekly",
                                           duration="8 weeks")], uploader=U)
    s.event(A, glim, dd(468), "stopped", "Glimepiride stopped after hypoglycaemia episodes", "Dr. Meera Iyer")
    for med in s.meds:
        if med.id == glim:
            med.end_date = dd(468)
            med.notes = "Stopped due to hypoglycaemia episodes."
    vd = s.med(A, "Cholecalciferol 60000 IU", "cholecalciferol", "vitamin D", "60000 IU", "Once weekly", dd(468),
               "completed", "Dr. Meera Iyer", D_MEERA, end=dd(524), duration="8 weeks", source_doc=rx5)
    s.event(A, vd, dd(524), "completed", "Vitamin D course completed (8 weeks)", "Dr. Meera Iyer")
    s.conditions.append(m.Condition(id=s._id("cnd"), patient_id=A, name="Vitamin D deficiency", status="resolved",
                                    diagnosed_on=dd(468), diagnosed_by="Dr. Meera Iyer"))

    s.doc(A, U, "Influenza Vaccination Certificate", "vaccination_record", dd(505),
          ["Vaccine: Inactivated quadrivalent influenza vaccine (demo)", "Dose: 0.5 mL IM, left deltoid",
           "Batch: DEMO-FLU-2026-118", f"Administered at: {HOSP[D_KAVYA]}"], doctor="Dr. Kavya Nair",
          hospital=HOSP[D_KAVYA], tags=["vaccine"])
    s.lab_report(A, U, dd(552), {"hba1c": 7.1, "fasting_glucose": 126, "vitamin_d": 34}, "Dr. Meera Iyer")
    s.med(A, "Ibuprofen 400 mg", "ibuprofen", "NSAID", "400 mg", "As needed for knee pain", dd(600),
          "patient_reported", None, None, adherence=None, verified=False,
          notes="Over-the-counter, self-reported. About 3-4 times a week.")
    s.med(A, "Multivitamin", "multivitamin", "supplement", None, None, dd(610), "patient_reported", verified=False,
          notes="Self-reported. Brand and dose not recorded.")
    s.lab_report(A, U, dd(643), {"hba1c": 6.8, "fasting_glucose": 116, "total_cholesterol": 168, "ldl": 92, "hdl": 49,
                                 "triglycerides": 138, "creatinine": 1.0, "egfr": 74, "urine_acr": 27},
                 "Dr. Meera Iyer")
    next_fu = t + timedelta(days=14)
    s.consult(A, D_MEERA, "Dr. Meera Iyer", dd(657), "Diabetes and lipid follow-up",
              "HbA1c 6.8% - at target. LDL 92 mg/dL. eGFR 74, urine ACR 27 mg/g - monitor kidney function. "
              "Discussed knee pain; patient reports using OTC ibuprofen - to be reviewed with GP.",
              ["Type 2 diabetes mellitus - at target", "Dyslipidemia - improving"],
              "Review in 3 months with HbA1c, kidney function, urine ACR; annual diabetic eye exam due",
              next_fu, uploader=U)

    # vitals: home BP / HR monthly, weight every 2 months
    import math
    for i in range(0, 24):
        day = dd(14 + i * 30)
        if day > t:
            break
        sys_ = round(148 - i * 0.9 - (6 if i >= 7 else 0) + 2 * math.sin(i), 0)
        dia = round(94 - i * 0.5 - (4 if i >= 7 else 0) + math.cos(i), 0)
        ref = "Target < 130/80 mmHg (documented by Dr. Meera Iyer)"
        s.vital(A, day, "bp_systolic", "Systolic BP", sys_, "mmHg", None, 130, ref)
        s.vital(A, day, "bp_diastolic", "Diastolic BP", dia, "mmHg", None, 80, ref)
        s.vital(A, day, "heart_rate", "Resting Heart Rate", round(82 - i * 0.25 + math.sin(i * 1.7) * 2, 0), "bpm")
        if i % 2 == 0:
            w = round(74.0 - i * 0.22, 1)
            s.vital(A, day, "weight", "Weight", w, "kg")
            s.vital(A, day, "bmi", "BMI", round(w / (1.60 ** 2), 1), "kg/m2", source="Calculated from weight and height")

    # ---------------- Rahul: smaller record (used to show access is denied without consent)
    R, UR = P_RAHUL, "usr_rahul"
    r0 = _ago(t, 420)
    _, rr1 = s.consult(R, D_KAVYA, "Dr. Kavya Nair", r0, "Wheeze and night cough",
                       "Episodic wheeze, worse with dust. Spirometry shows reversible obstruction.",
                       ["Mild persistent asthma"], "Review in 3 months", r0 + timedelta(days=90),
                       [m.PrescriptionItem(name="Budesonide/Formoterol inhaler", dosage="200/6 mcg",
                                           frequency="1 puff twice daily", duration="Until review"),
                        m.PrescriptionItem(name="Salbutamol inhaler", dosage="100 mcg", frequency="2 puffs as needed",
                                           duration="Until review")], uploader=UR)
    s.med(R, "Budesonide/Formoterol 200/6 mcg", "budesonide/formoterol", "inhaled corticosteroid/LABA", "200/6 mcg",
          "1 puff twice daily", r0, "active", "Dr. Kavya Nair", D_KAVYA, source_doc=rr1)
    s.med(R, "Salbutamol 100 mcg", "salbutamol", "short-acting beta agonist", "100 mcg", "2 puffs as needed", r0,
          "active", "Dr. Kavya Nair", D_KAVYA, source_doc=rr1)
    s.conditions.append(m.Condition(id=s._id("cnd"), patient_id=R, name="Mild persistent asthma", status="active",
                                    diagnosed_on=r0, diagnosed_by="Dr. Kavya Nair"))
    s.lab_report(R, UR, r0 + timedelta(days=200), {"vitamin_d": 22, "tsh": 1.8, "fasting_glucose": 92}, "Dr. Kavya Nair")
    s.lab_report(R, UR, r0 + timedelta(days=380), {"vitamin_d": 31, "fasting_glucose": 95}, "Dr. Kavya Nair")

    # ---------------- consent / access (simulated)
    now = datetime.now(timezone.utc)
    all_scopes = m.ALL_SCOPES
    req_meera = m.AccessRequest(id="req_seed_meera", patient_id=A, doctor_id=D_MEERA, initiated_by="doctor",
                                requested_scopes=all_scopes, reason="Ongoing diabetes care", duration_hours=24 * 30,
                                status="approved", created_at=now - timedelta(days=10),
                                decided_at=now - timedelta(days=10), grant_id="grt_seed_meera")
    grants = [
        m.AccessGrant(id="grt_seed_meera", patient_id=A, doctor_id=D_MEERA, scopes=all_scopes,
                      granted_at=now - timedelta(days=10), expires_at=now + timedelta(days=20),
                      request_id="req_seed_meera"),
        m.AccessGrant(id="grt_seed_kavya_old", patient_id=A, doctor_id=D_KAVYA,
                      scopes=["history", "medications", "allergies"], granted_at=now - timedelta(days=60),
                      expires_at=now - timedelta(days=57)),
        m.AccessGrant(id="grt_seed_kavya_rahul", patient_id=R, doctor_id=D_KAVYA, scopes=all_scopes,
                      granted_at=now - timedelta(days=3), expires_at=now + timedelta(days=4)),
    ]
    requests = [
        req_meera,
        m.AccessRequest(id="req_seed_arjun", patient_id=A, doctor_id=D_ARJUN, initiated_by="doctor",
                        requested_scopes=["history", "medications", "labs", "consultations"],
                        reason="Cardiology 6-month review", duration_hours=72, status="pending",
                        created_at=now - timedelta(hours=5)),
    ]
    audits = [
        m.AuditLog(id="aud_seed_1", timestamp=now - timedelta(days=60), actor_user_id="usr_ananya",
                   actor_role="patient", actor_name="Ananya Rao", action="access.granted", patient_id=A,
                   resource_type="access_grant", resource_id="grt_seed_kavya_old",
                   detail="Shared history, medications, allergies with Dr. Kavya Nair for 72h"),
        m.AuditLog(id="aud_seed_2", timestamp=now - timedelta(days=10), actor_user_id="usr_ananya",
                   actor_role="patient", actor_name="Ananya Rao", action="access.request_approved", patient_id=A,
                   resource_type="access_grant", resource_id="grt_seed_meera",
                   detail="Approved Dr. Meera Iyer: all scopes for 30 days"),
        m.AuditLog(id="aud_seed_3", timestamp=now - timedelta(days=9), actor_user_id="usr_meera", actor_role="doctor",
                   actor_name="Dr. Meera Iyer", action="patient.history_viewed", patient_id=A,
                   resource_type="patient", resource_id=A),
        m.AuditLog(id="aud_seed_4", timestamp=now - timedelta(hours=5), actor_user_id="usr_arjun",
                   actor_role="doctor", actor_name="Dr. Arjun Shah", action="access.requested", patient_id=A,
                   resource_type="access_request", resource_id="req_seed_arjun",
                   detail="Requested history, medications, labs, consultations for 72h"),
    ]

    repos.users.replace_all(users)
    repos.patients.replace_all(patients)
    repos.doctors.replace_all(doctors)
    repos.documents.replace_all(s.docs)
    repos.extractions.replace_all([])
    repos.observations.replace_all(s.obs)
    repos.medications.replace_all(s.meds)
    repos.medication_events.replace_all(s.events)
    repos.consultations.replace_all(s.consults)
    repos.prescriptions.replace_all(s.rx)
    repos.conditions.replace_all(s.conditions)
    repos.allergies.replace_all(s.allergies)
    repos.access_grants.replace_all(grants)
    repos.access_requests.replace_all(requests)
    repos.ai_summaries.replace_all([])
    repos.audit_logs.replace_all(audits)
    repos.store.save("_meta", [{"id": "meta", "seeded_at": now.isoformat(), "seed_reference_date": today.isoformat(),
                                "notice": FICTION}])
    return {c: len(repos.store.load(c)) for c in repos.store.collections()}


def ensure_seeded(repos: Repos | None = None) -> bool:
    """Seed on first run, or if users are missing/corrupt. Returns True if seeded."""
    repos = repos or get_repos()
    if repos.users.all():
        return False
    seed(repos)
    return True
