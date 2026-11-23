"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, CalendarDays, FileText, FlaskConical, Pill, Search, ShieldAlert, Stethoscope, X } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { qs } from "@/lib/api";
import type { TimelineEvent } from "@/lib/types";
import { Badge, Card, Empty, ErrorBox, inputCls, Spinner } from "./ui";
import { DocumentViewer } from "./DocumentViewer";
import { cx, fmtDate } from "@/lib/format";

const TYPES: { value: TimelineEvent["type"]; label: string; icon: React.ComponentType<{ className?: string }>; color: string }[] = [
  { value: "consultation", label: "Consultations", icon: Stethoscope, color: "bg-navy-700" },
  { value: "prescription", label: "Prescriptions", icon: Pill, color: "bg-teal-600" },
  { value: "lab_report", label: "Lab reports", icon: FlaskConical, color: "bg-violet-600" },
  { value: "medication", label: "Medication changes", icon: Pill, color: "bg-amber-500" },
  { value: "allergy", label: "Allergies", icon: ShieldAlert, color: "bg-rose-600" },
  { value: "document", label: "Other documents", icon: FileText, color: "bg-slate-500" },
];

interface TimelineResp { events: TimelineEvent[]; count: number; doctors: string[]; hospitals: string[]; shared_scopes: string[] }

export function TimelineView({ patientId, limit }: { patientId: string; limit?: number }) {
  const [types, setTypes] = useState<string[]>([]);
  const [doctor, setDoctor] = useState("");
  const [q, setQ] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [viewDoc, setViewDoc] = useState<{ id: string; title?: string | null } | null>(null);

  const path = `/api/patients/${patientId}/timeline${qs({ type: types.join(","), doctor, date_from: from, date_to: to })}`;
  const { data, error, loading, reload } = useApi<TimelineResp>(path);
  const all = useApi<TimelineResp>(`/api/patients/${patientId}/timeline`);

  const events = useMemo(() => {
    let ev = data?.events ?? [];
    if (q) {
      const ql = q.toLowerCase();
      ev = ev.filter((e) => [e.title, e.summary, e.doctor, e.hospital, ...(e.diagnoses ?? []), ...(e.medications ?? [])].join(" ").toLowerCase().includes(ql));
    }
    return limit ? ev.slice(0, limit) : ev;
  }, [data, q, limit]);

  const byYear = useMemo(() => {
    const g: Record<string, TimelineEvent[]> = {};
    events.forEach((e) => { (g[e.date.slice(0, 4)] ||= []).push(e); });
    return Object.entries(g).sort((a, b) => b[0].localeCompare(a[0]));
  }, [events]);

  const filtersActive = types.length || doctor || q || from || to;
  const canViewDocs = data?.shared_scopes.includes("documents");

  return (
    <div className="space-y-4">
      {!limit && (
        <Card className="p-4">
          <div className="flex flex-wrap gap-2">
            {TYPES.map((t) => {
              const on = types.includes(t.value);
              return (
                <button key={t.value} onClick={() => setTypes(on ? types.filter((x) => x !== t.value) : [...types, t.value])}
                  className={cx("inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition",
                    on ? "border-teal-300 bg-teal-50 text-teal-800" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300")}>
                  <t.icon className="h-3.5 w-3.5" /> {t.label}
                </button>
              );
            })}
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input className={cx(inputCls, "pl-9")} placeholder="Search diagnosis, medicine, note…" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <select className={inputCls} value={doctor} onChange={(e) => setDoctor(e.target.value)} aria-label="Filter by doctor">
              <option value="">All doctors</option>
              {(all.data?.doctors ?? []).map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <input type="date" className={inputCls} value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From date" />
            <input type="date" className={inputCls} value={to} onChange={(e) => setTo(e.target.value)} aria-label="To date" />
          </div>
          {filtersActive ? (
            <button onClick={() => { setTypes([]); setDoctor(""); setQ(""); setFrom(""); setTo(""); }} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-teal-700">
              <X className="h-3 w-3" /> Clear filters · {events.length} events
            </button>
          ) : null}
        </Card>
      )}

      {loading && !data && <Spinner />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && events.length === 0 && <Card><Empty icon={<CalendarDays className="h-5 w-5" />} title="No events match">Try clearing filters.</Empty></Card>}

      {byYear.map(([year, evs]) => (
        <div key={year}>
          {!limit && <p className="mb-2 ml-1 text-sm font-semibold text-navy-800">{year}</p>}
          <ol className="relative space-y-3 border-l-2 border-slate-200 pl-6">
            {evs.map((e) => {
              const t = TYPES.find((x) => x.value === e.type) ?? TYPES[5];
              return (
                <li key={e.id} className="relative">
                  <span className={cx("absolute -left-[35px] top-3 grid h-6 w-6 place-items-center rounded-full text-white ring-4 ring-slate-50", t.color)}>
                    <t.icon className="h-3 w-3" />
                  </span>
                  <Card className="p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="font-medium text-navy-700">{fmtDate(e.date)}</span>
                      <Badge tone="slate">{e.type_label}</Badge>
                      {e.created_via === "doctor_portal" && <Badge tone="amber">Demo record · doctor portal</Badge>}
                      {e.status === "proposed_demo" && <Badge tone="amber">Proposed (demo)</Badge>}
                      {e.doctor && <span>· {e.doctor}</span>}
                      {e.hospital && <span className="hidden sm:inline">· {e.hospital}</span>}
                    </div>
                    <p className="mt-1.5 font-medium text-navy-900">{e.title}</p>
                    {e.summary && e.summary !== e.title && <p className="mt-1 line-clamp-3 text-sm text-slate-600">{e.summary}</p>}
                    {!!e.diagnoses?.length && (
                      <div className="mt-2 flex flex-wrap gap-1.5">{e.diagnoses.map((d) => <Badge key={d} tone="navy">{d}</Badge>)}</div>
                    )}
                    {!!e.flags?.length && (
                      <div className="mt-2 space-y-1">{e.flags.map((f) => (
                        <p key={f} className="flex items-center gap-1.5 text-xs text-amber-800"><AlertTriangle className="h-3.5 w-3.5" />{f}</p>
                      ))}</div>
                    )}
                    {e.follow_up && <p className="mt-2 text-xs text-slate-500"><span className="font-medium">Follow-up:</span> {e.follow_up}</p>}
                    {e.source_document_id && (
                      canViewDocs ? (
                        <button onClick={() => setViewDoc({ id: e.source_document_id!, title: e.source_document_title })}
                          className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-teal-700 hover:underline">
                          <FileText className="h-3.5 w-3.5" /> Source: {e.source_document_title || "document"}
                        </button>
                      ) : <p className="mt-2 text-xs text-slate-400">Source document not shared</p>
                    )}
                  </Card>
                </li>
              );
            })}
          </ol>
        </div>
      ))}
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </div>
  );
}
