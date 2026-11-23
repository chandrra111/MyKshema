"use client";

import Link from "next/link";
import { Clock, KeyRound, Stethoscope, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { AuditLog } from "@/lib/types";
import { SCOPE_LABEL } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, Notice, PageHeader, Stat } from "@/components/ui";
import { PatientCards, RequestAccessCard, type DoctorPatientsResp } from "@/components/DoctorPatients";
import { relTime } from "@/lib/format";

export default function DoctorDashboard() {
  const { user } = useAuth();
  const pts = useApi<DoctorPatientsResp>("/api/doctor/patients");
  const logs = useApi<{ logs: AuditLog[] }>("/api/audit-logs?limit=300");
  const pending = pts.data?.pending_requests ?? [];
  const authored = (logs.data?.logs ?? []).filter((l) => l.action === "consultation.created").length;

  async function cancel(id: string) { await api(`/api/access-requests/${id}/cancel`, { method: "POST" }); pts.reload(); }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Doctor portal" title={`Welcome, ${user!.display_name}`}
        subtitle="Review consolidated histories of patients who have shared their records with you." />
      <Notice tone="warn"><b>Prototype simulation.</b> {pts.data?.note ?? ""} All patients and records are synthetic.</Notice>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Stat label="Patients sharing with you" value={pts.data?.patients.length ?? "—"} icon={<Users className="h-4 w-4" />} />
        <Stat label="Pending requests" value={pending.length} icon={<Clock className="h-4 w-4" />} tone="amber" sub="Awaiting patient decision" />
        <Stat label="Demo consultations authored" value={authored} icon={<Stethoscope className="h-4 w-4" />} tone="navy" />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
        <div className="space-y-3">
          <div className="flex items-center justify-between"><h2 className="font-semibold text-navy-900">Patients with active consent</h2><Link href="/doctor/patients" className="text-sm font-medium text-teal-700">All →</Link></div>
          <PatientCards data={pts.data} loading={pts.loading} error={pts.error} reload={pts.reload} />
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader icon={<KeyRound className="h-4 w-4" />} title="Your pending requests" />
            {pending.length === 0 ? <Empty title="No pending requests" /> : (
              <ul className="divide-y divide-slate-100">
                {pending.map((r) => (
                  <li key={r.id} className="px-5 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-navy-900">{r.patient_name}</p>
                      <Button size="sm" variant="ghost" onClick={() => cancel(r.id)}>Cancel</Button>
                    </div>
                    <p className="text-xs text-slate-500">Sent {relTime(r.created_at)} · {r.requested_scopes.map((s) => SCOPE_LABEL[s]).join(", ")}</p>
                    <Badge tone="amber" className="mt-1">Waiting for patient</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <RequestAccessCard onDone={pts.reload} />
        </div>
      </div>
    </div>
  );
}
