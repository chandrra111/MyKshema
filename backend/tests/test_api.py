"""End-to-end API tests against an isolated, freshly seeded JSON store."""
from app.services.pdfgen import make_pdf


def test_health_reports_no_database_and_demo_ai(client):
    r = client.get("/health").json()
    assert r["status"] == "ok"
    assert r["database"].startswith("none")
    assert r["live_ai"] is False
    assert r["users"] == 5


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/demo-login", json={"email": "ananya.rao@demo.mykshema.test", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["message"]


def test_requires_auth(client):
    assert client.get("/api/patients/me").status_code == 401
    assert client.get("/api/documents", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_patient_profile_and_timeline(client, patient):
    me = client.get("/api/auth/me", headers=patient).json()
    assert me["role"] == "patient"
    pid = me["patient_id"]
    tl = client.get(f"/api/patients/{pid}/timeline", headers=patient).json()
    assert tl["count"] > 20
    types = {e["type"] for e in tl["events"]}
    assert {"consultation", "prescription", "lab_report"} <= types
    dates = [e["date"] for e in tl["events"]]
    assert dates == sorted(dates, reverse=True)
    filtered = client.get(f"/api/patients/{pid}/timeline?type=consultation&doctor=Meera", headers=patient).json()
    assert filtered["count"] >= 3 and all(e["doctor"] == "Dr. Meera Iyer" for e in filtered["events"])


def test_patient_cannot_read_other_patient(client, patient):
    assert client.get("/api/patients/pat_rahul/history", headers=patient).status_code == 403
    assert client.get("/api/documents?patient_id=pat_rahul", headers=patient).status_code == 403


def test_doctor_access_requires_active_grant(client, meera, arjun):
    assert client.get("/api/patients/pat_ananya/history", headers=meera).status_code == 200
    assert client.get("/api/patients/pat_rahul/history", headers=meera).status_code == 403
    # Arjun only has a pending request
    assert client.get("/api/patients/pat_ananya/history", headers=arjun).status_code == 403


def test_consent_approve_scope_and_revoke(client, patient, arjun):
    reqs = client.get("/api/access-requests", headers=patient).json()["requests"]
    pending = [x for x in reqs if x["status"] == "pending"]
    assert pending and pending[0]["doctor_id"] == "doc_arjun"
    # patient narrows scope: no labs
    r = client.post(f"/api/access-requests/{pending[0]['id']}/approve", headers=patient,
                    json={"scopes": ["history", "medications"], "duration_hours": 2})
    assert r.status_code == 200
    grant_id = r.json()["grant"]["id"]
    assert client.get("/api/patients/pat_ananya/timeline", headers=arjun).status_code == 200
    assert client.get("/api/medications?patient_id=pat_ananya", headers=arjun).status_code == 200
    assert client.get("/api/analytics/health-trends?patient_id=pat_ananya", headers=arjun).status_code == 403
    assert client.get("/api/documents?patient_id=pat_ananya", headers=arjun).status_code == 403
    pts = client.get("/api/doctor/patients", headers=arjun).json()["patients"]
    assert [p["patient_id"] for p in pts] == ["pat_ananya"]
    # revoke -> immediate loss of access
    assert client.post(f"/api/access-grants/{grant_id}/revoke", headers=patient).status_code == 200
    assert client.get("/api/patients/pat_ananya/timeline", headers=arjun).status_code == 403
    actions = [x["action"] for x in client.get("/api/audit-logs", headers=patient).json()["logs"]]
    assert "access.revoked" in actions and "access.denied" in actions


def test_patient_direct_share(client, patient, rahul):
    r = client.post("/api/access-grants", headers=patient,
                    json={"doctor_id": "doc_kavya", "scopes": ["allergies"], "duration_hours": 1})
    assert r.status_code == 201
    kavya = client.post("/api/auth/demo-login",
                        json={"email": "kavya.nair@demo.mykshema.test", "password": "Demo@2036"}).json()
    h = {"Authorization": f"Bearer {kavya['access_token']}"}
    assert client.get("/api/patients/pat_ananya/allergies", headers=h).status_code == 200
    assert client.get("/api/patients/pat_ananya/conditions", headers=h).status_code == 403
    # a patient cannot revoke someone else's grant
    assert client.post(f"/api/access-grants/{r.json()['id']}/revoke", headers=rahul).status_code == 404


def test_medication_flags_are_grounded(client, patient):
    data = client.get("/api/medications", headers=patient).json()
    types = {f["type"] for f in data["flags"]}
    assert "duplicate_class" in types  # atorvastatin + rosuvastatin
    assert "interaction" in types  # ibuprofen (NSAID) + telmisartan (ARB)
    assert "allergy_conflict" in types  # amoxicillin vs penicillin allergy (historical)
    assert "missing_details" in types  # multivitamin has no dose
    assert all(f["requires_clinician_review"] for f in data["flags"])
    statuses = {m["status"] for m in data["medications"]}
    assert {"active", "patient_reported", "discontinued", "completed"} <= statuses


def test_analytics_only_uses_documented_ranges(client, patient):
    trends = {t["code"]: t for t in client.get("/api/analytics/health-trends", headers=patient).json()["trends"]}
    assert trends["hba1c"]["reference"]["text"] == "4.0 - 5.6 %"
    assert trends["hba1c"]["trend"]["n_points"] >= 5
    assert trends["heart_rate"]["reference"] is None
    assert all(p["status"] == "no_documented_range" for p in trends["weight"]["points"])
    rem = client.get("/api/analytics/reminders", headers=patient).json()["reminders"]
    assert any(r["kind"] == "follow_up" for r in rem)


def test_ai_demo_mode_labelled_and_grounded(client, patient, meera):
    for q, kind in [("Summarise my history", "history_summary"), ("Show my HbA1c trend", "trend"),
                    ("Compare my last three reports", "compare_reports"), ("List my previous doctors", "doctors"),
                    ("List my recorded medications", "medications"),
                    ("Summarise my latest consultation", "latest_consultation")]:
        r = client.post("/api/ai/ask", headers=patient, json={"question": q}).json()
        assert r["mode"] == "demo" and r["label"] == "DEMO MODE - NOT LIVE AI", q
        assert r["kind"] == kind, q
    unknown = client.post("/api/ai/ask", headers=patient, json={"question": "What is the weather?"}).json()
    assert unknown["kind"] == "help" and "will not guess" in unknown["answer"]
    s = client.post("/api/ai/summarize-history", headers=meera, json={"patient_id": "pat_ananya"}).json()
    assert "Type 2 diabetes" in s["answer"] and s["citations"]
    dup = client.post("/api/ai/ask", headers=meera,
                      json={"patient_id": "pat_ananya", "question": "Identify possible duplicate therapies"}).json()
    assert dup["kind"] == "medication_review" and dup["flags"]
    assert client.post("/api/ai/summarize-history", headers=meera,
                       json={"patient_id": "pat_rahul"}).status_code == 403


def test_upload_extract_confirm_flow(client, patient):
    pdf = make_pdf(["Blood Report", "Laboratory: Test Lab", "Report date: 2026-11-20", "Referring doctor: Dr. Meera Iyer",
                    "Test | Result | Unit | Reference range", "HbA1c | 6.7 | % | 4.0 - 5.6 %",
                    "Fasting Blood Glucose | 112 | mg/dL | 70 - 99 mg/dL"])
    r = client.post("/api/documents/upload", headers=patient, files={"file": ("lab.pdf", pdf, "application/pdf")},
                    data={"category": "blood_report"})
    assert r.status_code == 201, r.text
    doc, ext = r.json()["document"], r.json()["extraction"]
    assert "stored_filename" not in doc
    assert ext["method"] == "pdf_text_rules" and ext["status"] == "pending_review"
    assert ext["fields"]["consultation_date"]["value"] == "2026-11-20"
    labs = {l["test_name"]: l for l in ext["fields"]["labs"]}
    assert labs["HbA1c"]["value"] == 6.7
    # nothing saved to the record before confirmation
    before = len(client.get("/api/analytics/observations?code=hba1c", headers=patient).json()["observations"])
    c = client.post(f"/api/documents/{doc['id']}/confirm-extraction", headers=patient, json={
        "category": "blood_report", "consultation_date": "2026-11-20", "doctor_name": "Dr. Meera Iyer",
        "labs": ext["fields"]["labs"], "medications": []})
    assert c.status_code == 200 and c.json()["created"]["observations"] == 2
    after = client.get("/api/analytics/observations?code=hba1c", headers=patient).json()["observations"]
    assert len(after) == before + 1 and after[0]["source_document_id"] == doc["id"]
    f = client.get(f"/api/documents/{doc['id']}/file", headers=patient)
    assert f.status_code == 200 and f.content.startswith(b"%PDF")
    assert client.get(f"/api/documents/{doc['id']}/file").status_code == 401
    assert client.delete(f"/api/documents/{doc['id']}", headers=patient).json()["deleted"] is True


def test_upload_validation(client, patient):
    bad = client.post("/api/documents/upload", headers=patient,
                      files={"file": ("fake.pdf", b"MZ not a pdf", "application/pdf")})
    assert bad.status_code == 415
    exe = client.post("/api/documents/upload", headers=patient, files={"file": ("x.exe", b"MZ", "application/x")})
    assert exe.status_code == 415
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    img = client.post("/api/documents/upload", headers=patient, files={"file": ("scan.png", png, "image/png")},
                      data={"category": "xray", "doctor_name": "Dr. Test"}).json()
    assert img["extraction"]["method"] == "demo_template"
    assert img["extraction"]["fields"]["labs"] == [] and img["extraction"]["fields"]["medications"] == []
    assert "DEMO" in img["extraction"]["method_label"]


def test_doctor_consultation_with_proposed_rx(client, meera, patient, arjun):
    body = {"patient_id": "pat_ananya", "notes": "Knee pain review. Advised to avoid regular NSAIDs.",
            "diagnoses": ["Osteoarthritis knee"], "follow_up": "4 weeks",
            "prescription_items": [{"name": "Paracetamol", "dosage": "650 mg", "frequency": "As needed"}]}
    r = client.post("/api/consultations", headers=meera, json=body)
    assert r.status_code == 201
    meds = client.get("/api/medications", headers=patient).json()["medications"]
    assert any(m["status"] == "proposed" and m["name"].startswith("Paracetamol") for m in meds)
    assert client.post("/api/consultations", headers=arjun, json=body).status_code == 403
    assert client.post("/api/consultations", headers=patient, json=body).status_code == 403


def test_corrupt_json_file_is_handled(client, patient, tmp_path):
    from app.config import get_settings

    (get_settings().data_dir / "observations.json").write_text("{not json", encoding="utf-8")
    r = client.get("/api/analytics/health-trends", headers=patient)
    assert r.status_code == 200 and r.json()["trends"] == []
    assert list(get_settings().data_dir.glob("observations.corrupt-*.json"))


def test_demo_reset(client, patient):
    client.post("/api/medications", headers=patient, json={"name": "Test Med"})
    r = client.post("/api/demo/reset", headers=patient)
    assert r.status_code == 200 and r.json()["counts"]["users"] == 5
