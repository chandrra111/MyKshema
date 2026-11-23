"use client";

import { useApi } from "@/lib/hooks";
import type { AuditLog } from "@/lib/types";
import { Badge, Card, PageHeader, Spinner } from "@/components/ui";
import { fmtDateTime } from "@/lib/format";

export default function ActivityPage() {
  const logs = useApi<{ logs: AuditLog[] }>("/api/audit-logs?limit=300");
  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Activity Log" title="Your actions"
        subtitle="Every patient-record view, AI request, consultation and blocked access attempt is recorded in the demo audit log — patients see these too." />
      <Card>
        {logs.loading && !logs.data ? <Spinner /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500">
                <tr><th className="px-5 py-2">When</th><th className="px-5 py-2">Action</th><th className="px-5 py-2">Outcome</th><th className="px-5 py-2">Detail</th></tr>
              </thead>
              <tbody>
                {(logs.data?.logs ?? []).map((l) => (
                  <tr key={l.id} className="border-t border-slate-100">
                    <td className="whitespace-nowrap px-5 py-2 text-xs text-slate-500">{fmtDateTime(l.timestamp)}</td>
                    <td className="whitespace-nowrap px-5 py-2 font-mono text-xs text-navy-800">{l.action}</td>
                    <td className="px-5 py-2"><Badge tone={l.outcome === "denied" ? "rose" : "emerald"}>{l.outcome}</Badge></td>
                    <td className="px-5 py-2 text-xs text-slate-600">{l.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
