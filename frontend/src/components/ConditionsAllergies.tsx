"use client";

import { HeartPulse, ShieldAlert } from "lucide-react";
import { useApi } from "@/lib/hooks";
import type { Allergy, Condition } from "@/lib/types";
import { Badge, Card, CardHeader } from "./ui";
import { fmtDate } from "@/lib/format";

export function ConditionsAllergies({ patientId }: { patientId: string }) {
  const cond = useApi<Condition[]>(`/api/patients/${patientId}/conditions`);
  const alg = useApi<Allergy[]>(`/api/patients/${patientId}/allergies`);
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader icon={<HeartPulse className="h-4 w-4" />} title="Conditions" />
        <ul className="divide-y divide-slate-100">
          {cond.error && <li className="px-5 py-3 text-sm text-slate-500">Not shared.</li>}
          {(cond.data ?? []).map((c) => (
            <li key={c.id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-navy-900">{c.name}</p>
                <Badge tone={c.status === "active" ? "teal" : "slate"}>{c.status}</Badge>
              </div>
              <p className="text-xs text-slate-500">{fmtDate(c.diagnosed_on)}{c.diagnosed_by ? ` · ${c.diagnosed_by}` : ""}</p>
            </li>
          ))}
          {cond.data && !cond.data.length && <li className="px-5 py-3 text-sm text-slate-500">None recorded.</li>}
        </ul>
      </Card>
      <Card>
        <CardHeader icon={<ShieldAlert className="h-4 w-4" />} title="Allergies" />
        <ul className="divide-y divide-slate-100">
          {alg.error && <li className="px-5 py-3 text-sm text-slate-500">Not shared.</li>}
          {(alg.data ?? []).map((a) => (
            <li key={a.id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-2"><p className="text-sm font-medium text-navy-900">{a.substance}</p><Badge tone="rose">{a.severity}</Badge></div>
              <p className="text-xs text-slate-500">{a.reaction || "Reaction not recorded"} · {fmtDate(a.recorded_on)}</p>
            </li>
          ))}
          {alg.data && !alg.data.length && <li className="px-5 py-3 text-sm text-slate-500">No allergies recorded.</li>}
        </ul>
      </Card>
    </div>
  );
}
