"use client";

import { useState } from "react";
import { CalendarCheck, FileText, Pill, Stethoscope } from "lucide-react";
import { qs } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Consultation } from "@/lib/types";
import { Badge, Card, Empty, ErrorBox, Spinner } from "./ui";
import { DocumentViewer } from "./DocumentViewer";
import { fmtDate } from "@/lib/format";

export function ConsultationsList({ patientId, canViewDocs = true, refreshKey = 0 }: { patientId?: string; canViewDocs?: boolean; refreshKey?: number }) {
  const { data, error, loading, reload } = useApi<{ consultations: Consultation[] }>(`/api/consultations${qs({ patient_id: patientId, r: refreshKey || undefined })}`);
  const [viewDoc, setViewDoc] = useState<{ id: string; title?: string | null } | null>(null);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const list = data?.consultations ?? [];
  if (!list.length) return <Card><Empty icon={<Stethoscope className="h-5 w-5" />} title="No consultations recorded" /></Card>;
  return (
    <div className="space-y-3">
      {list.map((c) => (
        <Card key={c.id} className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-navy-50 text-navy-700"><Stethoscope className="h-5 w-5" /></div>
              <div>
                <p className="font-medium text-navy-900">{c.reason || "Consultation"}</p>
                <p className="text-sm text-slate-500">{c.doctor_name}{c.hospital ? ` · ${c.hospital}` : ""}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {c.created_via === "doctor_portal" && <Badge tone="amber">Demo record · doctor portal</Badge>}
              <Badge tone="slate">{fmtDate(c.consultation_date)}</Badge>
            </div>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{c.notes}</p>
          {!!c.diagnoses.length && <div className="mt-3 flex flex-wrap gap-1.5">{c.diagnoses.map((d) => <Badge key={d} tone="navy">{d}</Badge>)}</div>}
          {c.prescription && (
            <div className="mt-3 rounded-xl border border-teal-100 bg-teal-50/40 p-3">
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-teal-800">
                <Pill className="h-3.5 w-3.5" /> {c.prescription.status === "proposed_demo" ? "Proposed prescription (demo · authored by doctor)" : "Prescription (authored by doctor)"}
              </p>
              <ul className="space-y-0.5 text-sm text-navy-800">
                {c.prescription.items.map((it, i) => <li key={i}>• {it.name} {it.dosage} — {it.frequency}{it.duration ? ` · ${it.duration}` : ""}{it.instructions ? ` · ${it.instructions}` : ""}</li>)}
              </ul>
            </div>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-500">
            {c.follow_up && <span className="inline-flex items-center gap-1"><CalendarCheck className="h-3.5 w-3.5" /> Follow-up: {c.follow_up}{c.follow_up_date ? ` (${fmtDate(c.follow_up_date)})` : ""}</span>}
            {c.source_document_id && canViewDocs && (
              <button onClick={() => setViewDoc({ id: c.source_document_id!, title: c.source_document_title })} className="inline-flex items-center gap-1 font-medium text-teal-700 hover:underline">
                <FileText className="h-3.5 w-3.5" /> {c.source_document_title || "Consultation note"}
              </button>
            )}
          </div>
        </Card>
      ))}
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </div>
  );
}
