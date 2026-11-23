"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { Card, Empty, inputCls, PageHeader, Spinner } from "@/components/ui";
import { AssistantView } from "@/components/AssistantView";
import type { DoctorPatientsResp } from "@/components/DoctorPatients";

export default function DoctorAssistantPage() {
  const { user } = useAuth();
  const pts = useApi<DoctorPatientsResp>("/api/doctor/patients");
  const [pid, setPid] = useState("");
  useEffect(() => { if (!pid && pts.data?.patients.length) setPid(pts.data.patients[0].patient_id); }, [pts.data, pid]);
  const current = pts.data?.patients.find((p) => p.patient_id === pid);

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="AI Clinical Assistant" title="Ask about an authorised patient"
        subtitle="Summaries, medication changes, lab comparisons and possible duplicate therapies — only from records the patient shared with you."
        actions={pts.data?.patients.length ? (
          <select className={inputCls} value={pid} onChange={(e) => setPid(e.target.value)} aria-label="Patient">
            {pts.data.patients.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.full_name}</option>)}
          </select>
        ) : undefined} />
      {pts.loading && !pts.data ? <Spinner /> : !current ? (
        <Card><Empty title="No authorised patients">The assistant works only for patients who currently share records with you.</Empty></Card>
      ) : (
        <AssistantView key={pid} patientId={pid} role="doctor" storageKey={`doctor.${user!.id}.${pid}`} canViewDocs={current.scopes.includes("documents")} />
      )}
    </div>
  );
}
