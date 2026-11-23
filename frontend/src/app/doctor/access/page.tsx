"use client";

import { useApi } from "@/lib/hooks";
import { SCOPE_LABEL, type AccessRequest, type Grant } from "@/lib/types";
import { Badge, Card, CardHeader, PageHeader, Spinner } from "@/components/ui";
import { RequestAccessCard } from "@/components/DoctorPatients";
import { fmtDateTime } from "@/lib/format";

const TONE = { pending: "amber", approved: "emerald", denied: "rose", cancelled: "slate" } as const;

export default function DoctorAccessPage() {
  const reqs = useApi<{ requests: AccessRequest[] }>("/api/access-requests");
  const grants = useApi<{ grants: Grant[] }>("/api/access-grants");
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Access Requests" title="Consent requests & grants" subtitle="Simulated consent workflow — every decision belongs to the patient." />
      <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Requests you sent" />
            {reqs.loading && !reqs.data ? <Spinner /> : (
              <ul className="divide-y divide-slate-100">
                {(reqs.data?.requests ?? []).map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                    <div>
                      <p className="text-sm font-medium text-navy-900">{r.patient_name}</p>
                      <p className="text-xs text-slate-500">{fmtDateTime(r.created_at)} · {r.requested_scopes.map((s) => SCOPE_LABEL[s]).join(", ")}</p>
                    </div>
                    <Badge tone={TONE[r.status]}>{r.status}</Badge>
                  </li>
                ))}
                {reqs.data && !reqs.data.requests.length && <li className="px-5 py-6 text-sm text-slate-500">No requests yet.</li>}
              </ul>
            )}
          </Card>
          <Card>
            <CardHeader title="Grants (active, expired, revoked)" />
            <ul className="divide-y divide-slate-100">
              {(grants.data?.grants ?? []).map((g) => (
                <li key={g.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                  <div>
                    <p className="text-sm font-medium text-navy-900">{g.patient_name}</p>
                    <p className="text-xs text-slate-500">Granted {fmtDateTime(g.granted_at)} · {g.state === "revoked" ? `revoked ${fmtDateTime(g.revoked_at)}` : `expires ${fmtDateTime(g.expires_at)}`}</p>
                    <p className="text-[11px] text-slate-400">{g.scopes.map((s) => SCOPE_LABEL[s]).join(" · ")}</p>
                  </div>
                  <Badge tone={g.state === "active" ? "teal" : g.state === "revoked" ? "rose" : "slate"}>{g.state}</Badge>
                </li>
              ))}
            </ul>
          </Card>
        </div>
        <RequestAccessCard onDone={() => { reqs.reload(); grants.reload(); }} />
      </div>
    </div>
  );
}
