"use client";

import { useState } from "react";
import { useApi } from "@/lib/hooks";
import { PageHeader } from "@/components/ui";
import { PatientCards, PatientSearch, type DoctorPatientsResp } from "@/components/DoctorPatients";

export default function MyPatientsPage() {
  const pts = useApi<DoctorPatientsResp>("/api/doctor/patients");
  const [q, setQ] = useState("");
  return (
    <div className="space-y-4">
      <PageHeader eyebrow="My Patients" title="Authorised patients"
        subtitle="Only patients with an active, unexpired and unrevoked consent grant appear here. Access is enforced by the API on every request." />
      <PatientSearch value={q} onChange={setQ} />
      <PatientCards data={pts.data} loading={pts.loading} error={pts.error} reload={pts.reload} filter={q} />
    </div>
  );
}
