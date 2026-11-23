from datetime import date

from app import models as m
from app.security import hash_password, verify_password
from app.services import extraction, medication_review
from app.storage.json_store import JsonFileStore
from app.storage.memory_store import MemoryStore
from app.storage.base import Repository


def test_password_hash_roundtrip():
    h = hash_password("Demo@2036")
    assert h.startswith("pbkdf2_sha256$") and "Demo@2036" not in h
    assert verify_password("Demo@2036", h) and not verify_password("x", h)


def test_json_store_atomic_and_missing(tmp_path):
    s = JsonFileStore(tmp_path)
    assert s.load("things") == []
    s.save("things", [{"id": "a"}])
    assert s.load("things") == [{"id": "a"}]
    assert not list(tmp_path.glob("*.tmp"))


def test_repository_works_on_memory_store():
    repo = Repository(MemoryStore(), "allergies", m.Allergy)
    a = m.Allergy(id="a1", patient_id="p", substance="Sulfa")
    repo.add(a)
    assert repo.get("a1").substance == "Sulfa"
    a.severity = "severe"
    repo.update(a)
    assert repo.require("a1").severity == "severe"
    assert repo.delete("a1") and repo.all() == []


def test_reference_parsing():
    assert extraction.parse_reference("4.0 - 5.6 %") == (4.0, 5.6)
    assert extraction.parse_reference("< 100 mg/dL") == (None, 100)
    assert extraction.parse_reference(">= 90") == (90, None)
    assert extraction.parse_reference(None) == (None, None)


def test_rule_extract_prescription_ddmmyyyy():
    text = ("Prescription\nPrescriber: Dr. Rohan Kulkarni\nFacility: Greenleaf Clinic\nDate: 21/11/2026\n"
            "Diagnosis: Early osteoarthritis\nAllergies: Penicillin\nRx:\n"
            "- Paracetamol 650 mg | Three times daily as needed | 10 days\n- Glucosamine 1500 mg | Once daily | 8 weeks")
    f, warnings = extraction.rule_extract(text)
    assert f.category.value == "prescription"
    assert f.consultation_date.value == "2026-11-21"
    assert f.doctor_name.value == "Dr. Rohan Kulkarni"
    assert f.allergies.value == "Penicillin"
    names = [x.name for x in f.medications]
    assert names == ["Paracetamol", "Glucosamine"]
    assert f.medications[0].duration == "10 days" and f.medications[1].frequency.lower().startswith("once daily")
    assert not warnings


def _med(i, name, generic, cls, status="active", dosage="10 mg", freq="daily"):
    return m.Medication(id=i, patient_id="p", name=name, generic_name=generic, drug_class=cls, status=status,
                        dosage=dosage, frequency=freq, start_date=date(2025, 1, 1))


def test_no_flags_for_unrelated_medicines():
    meds = [_med("1", "Metformin", "metformin", "biguanide"), _med("2", "Telmisartan", "telmisartan",
                                                                    "angiotensin receptor blocker")]
    assert medication_review.review(meds, []) == []


def test_flags_only_from_table_and_records():
    meds = [_med("1", "Warfarin", "warfarin", "anticoagulant"), _med("2", "Aspirin", "aspirin", "antiplatelet"),
            _med("3", "Old Amoxicillin", "amoxicillin", "penicillin", status="completed")]
    alg = [m.Allergy(id="a", patient_id="p", substance="Penicillin", drug_class="penicillin")]
    flags = medication_review.review(meds, alg)
    kinds = sorted(f["type"] for f in flags)
    assert kinds == ["allergy_conflict", "interaction"]
    assert next(f for f in flags if f["type"] == "allergy_conflict")["severity"] == "info"  # historical only
