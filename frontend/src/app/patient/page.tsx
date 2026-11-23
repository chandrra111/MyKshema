"use client";

import Link from "next/link";
import { useState } from "react";
import { Activity, ArrowRight, BellRing, CalendarClock, FileText, Pill, ShieldAlert, Sparkles, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { AccessRequest, AIResult, Flag, Medication, Reminder, Trend } from "@/lib/types";
import { Button, Card, CardHeader, ErrorBox, Modal, PageHeader, Spinner, Stat } from "@/components/ui";
import { TimelineView } from "@/components/TimelineView";
import { TrendChart } from "@/components/TrendChart";
import { FlagList } from "@/components/FlagList";
import { AnswerCard } from "@/components/AssistantView";
import { DocumentViewer } from "@/components/DocumentViewer";
import { fmtDate } from "@/lib/format";

export default function Overview() {
  const { user } = useAuth();
  const pid = user!.patient_id!;
  const trends = useApi<{ trends: Trend[] }>("/api/analytics/health-trends");
  const meds = useApi<{ medications: Medication[]; flags: Flag[] }>("/api/medications");
  const docs = useApi<{ count: number }>("/api/documents");
  const rem = useApi<{ reminders: Reminder[] }>("/api/analytics/reminders");
  const reqs = useApi<{ requests: AccessRequest[] }>("/api/access-requests?status_filter=pending");
  const [summary, setSummary] = useState<AIResult | null>(null);
  const [summarising, setSummarising] = useState(false);
  const [sumErr, setSumErr] = useState<string | null>(null);
  const [viewDoc, setViewDoc] = useState<{ id: string; title: string } | null>(null);

  const t = Object.fromEntries((trends.data?.trends ?? []).map((x) => [x.code, x]));
  const current = (meds.data?.medications ?? []).filter((m) => ["active", "patient_reported", "proposed"].includes(m.status));
  const flags = (meds.data?.flags ?? []).filter((f) => f.severity === "high" || f.severity === "moderate");
  const nextFollow = (rem.data?.reminders ?? []).find((r) => r.kind === "follow_up");
  const pending = reqs.data?.requests ?? [];

  async function summarise() {
    setSummarising(true); setSumErr(null);
    try { setSummary(await api<AIResult>("/api/ai/summarize-history", { body: {} })); }
    catch (e) { setSumErr((e as Error).message); } finally { setSummarising(false); }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Overview" title={`Hello, ${user!.display_name.split(" ")[0]}`}
        subtitle="Your unified health record — built from your prescriptions, lab reports and consultations."
        actions={<Button variant="teal" onClick={summarise} loading={summarising}><Sparkles className="h-4 w-4" /> Summarise my history</Button>} />

      {pending.length > 0 && (
        <Card className="flex flex-wrap items-center gap-3 border-amber-200 bg-amber-50/60 p-4">
          <ShieldAlert className="h-5 w-5 text-amber-700" />
          <p className="flex-1 text-sm text-amber-900"><b>{pending.length} doctor access request{pending.length > 1 ? "s" : ""}</b> waiting for your decision — {pending.map((p) => p.doctor?.full_name).join(", ")}.</p>
          <Link href="/patient/doctors"><Button size="sm" variant="secondary">Review <ArrowRight className="h-4 w-4" /></Button></Link>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Latest HbA1c" icon={<Activity className="h-4 w-4" />}
          value={t.hba1c ? `${t.hba1c.latest.value}%` : "—"}
          sub={t.hba1c ? `${fmtDate(t.hba1c.latest.date)} · ref ${t.hba1c.reference?.text ?? "n/a"}` : "No result recorded"} />
        <Stat label="Blood pressure" icon={<Activity className="h-4 w-4" />} tone="navy"
          value={t.bp_systolic ? `${t.bp_systolic.latest.value}/${t.bp_diastolic?.latest.value ?? "–"}` : "—"}
          sub={t.bp_systolic ? `${fmtDate(t.bp_systolic.latest.date)} · home log` : "No readings"} />
        <Stat label="Current medicines" icon={<Pill className="h-4 w-4" />} tone="teal" value={current.length}
          sub={`${flags.length} item${flags.length === 1 ? "" : "s"} for clinician review`} />
        <Stat label="Next follow-up" icon={<CalendarClock className="h-4 w-4" />} tone="amber"
          value={nextFollow ? fmtDate(nextFollow.due, { day: "numeric", month: "short" }) : "None"}
          sub={nextFollow?.title ?? `${docs.data?.count ?? 0} documents in vault`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <Card>
            <CardHeader icon={<Activity className="h-4 w-4" />} title="HbA1c trend" subtitle="Shaded band = reference range printed on your lab reports"
              action={<Link href="/patient/analytics" className="text-sm font-medium text-teal-700">All analytics →</Link>} />
            <div className="p-4">{trends.loading && !trends.data ? <Spinner /> : t.hba1c ? <TrendChart series={[t.hba1c]} height={220} /> : <p className="p-6 text-sm text-slate-500">No HbA1c results recorded.</p>}</div>
          </Card>
          <Card>
            <CardHeader icon={<CalendarClock className="h-4 w-4" />} title="Recent activity" action={<Link href="/patient/history" className="text-sm font-medium text-teal-700">Full timeline →</Link>} />
            <div className="p-4"><TimelineView patientId={pid} limit={5} /></div>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader icon={<ShieldAlert className="h-4 w-4" />} title="Medication review" subtitle="Flags for your doctor to review" />
            <div className="p-4">{meds.data ? <FlagList flags={flags} compact /> : <Spinner />}
              <Link href="/patient/medications" className="mt-3 inline-block text-sm font-medium text-teal-700">Open medications →</Link>
            </div>
          </Card>
          <Card>
            <CardHeader icon={<BellRing className="h-4 w-4" />} title="Reminders" />
            <ul className="divide-y divide-slate-100">
              {(rem.data?.reminders ?? []).slice(0, 4).map((r, i) => (
                <li key={i} className="px-5 py-3"><p className="text-sm font-medium text-navy-900">{r.title}</p><p className="text-xs text-slate-500">{r.detail}</p></li>
              ))}
            </ul>
          </Card>
          <Card className="bg-gradient-to-br from-navy-800 to-navy-900 p-5 text-white">
            <Stethoscope className="h-6 w-6 text-teal-300" />
            <p className="mt-2 font-semibold">Share with a doctor</p>
            <p className="mt-1 text-sm text-navy-200">Choose exactly what to share and for how long. Revoke any time.</p>
            <Link href="/patient/doctors"><Button variant="teal" size="sm" className="mt-3">Doctor Connect <ArrowRight className="h-4 w-4" /></Button></Link>
          </Card>
          <Card className="p-5">
            <FileText className="h-6 w-6 text-teal-600" />
            <p className="mt-2 font-semibold text-navy-900">Add a document</p>
            <p className="mt-1 text-sm text-slate-500">Upload a prescription or report and review the extracted values.</p>
            <Link href="/patient/vault"><Button variant="secondary" size="sm" className="mt-3">Open vault</Button></Link>
          </Card>
        </div>
      </div>

      <Modal open={!!summary || !!sumErr} onClose={() => { setSummary(null); setSumErr(null); }} title="Your health summary" wide>
        {sumErr && <ErrorBox message={sumErr} />}
        {summary && <AnswerCard result={summary} onCite={(id, label) => id.startsWith("doc") && setViewDoc({ id, title: label })} />}
      </Modal>
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </div>
  );
}
