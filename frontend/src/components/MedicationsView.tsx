"use client";

import { useMemo, useState } from "react";
import { FileText, History, Pill, Plus, ShieldCheck } from "lucide-react";
import { api, qs } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Flag, MedEvent, Medication } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Field, inputCls, Modal, Notice, Spinner, Tabs } from "./ui";
import { FlagList } from "./FlagList";
import { DocumentViewer } from "./DocumentViewer";
import { fmtDate, STATUS_LABEL } from "@/lib/format";

type Tab = "current" | "past" | "all";
const STATUS_TONE: Record<string, "teal" | "violet" | "slate" | "amber" | "sky"> = {
  active: "teal", patient_reported: "violet", discontinued: "slate", completed: "sky", proposed: "amber",
};
const ADHERENCE = [
  { v: "taking_as_prescribed", l: "Taking as prescribed" },
  { v: "sometimes_missed", l: "Sometimes missed" },
  { v: "often_missed", l: "Often missed" },
  { v: "stopped_on_own", l: "Stopped on my own" },
];

export function MedicationsView({ patientId, canEdit }: { patientId?: string; canEdit?: boolean }) {
  const q = qs({ patient_id: patientId });
  const { data, error, loading, reload } = useApi<{ medications: Medication[]; flags: Flag[]; flags_note: string }>(`/api/medications${q}`);
  const hist = useApi<{ events: MedEvent[] }>(`/api/medications/history${q}`);
  const [tab, setTab] = useState<Tab>("current");
  const [adding, setAdding] = useState(false);
  const [viewDoc, setViewDoc] = useState<{ id: string; title?: string | null } | null>(null);
  const [form, setForm] = useState({ name: "", dosage: "", frequency: "", start_date: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  const meds = data?.medications ?? [];
  const current = meds.filter((m) => ["active", "patient_reported", "proposed"].includes(m.status));
  const past = meds.filter((m) => ["discontinued", "completed"].includes(m.status));
  const shown = tab === "current" ? current : tab === "past" ? past : meds;
  const flagCount = useMemo(() => (data?.flags ?? []).filter((f) => f.severity === "high" || f.severity === "moderate").length, [data]);

  async function setAdherence(id: string, adherence: string) {
    await api(`/api/medications/${id}/adherence`, { method: "PATCH", body: { adherence } });
    reload();
  }

  async function save() {
    setSaving(true); setFormErr(null);
    try {
      await api("/api/medications", { body: { ...form, start_date: form.start_date || undefined, dosage: form.dosage || undefined, frequency: form.frequency || undefined, notes: form.notes || undefined } });
      setAdding(false); setForm({ name: "", dosage: "", frequency: "", start_date: "", notes: "" });
      reload(); hist.reload();
    } catch (e) { setFormErr((e as Error).message); } finally { setSaving(false); }
  }

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { l: "Prescribed · current", v: meds.filter((m) => m.status === "active").length },
            { l: "Patient-reported", v: meds.filter((m) => m.status === "patient_reported").length },
            { l: "Past / completed", v: past.length },
            { l: "Flags to review", v: flagCount },
          ].map((s) => (
            <Card key={s.l} className="p-4"><p className="text-xs text-slate-500">{s.l}</p><p className="mt-1 text-2xl font-semibold text-navy-900">{s.v}</p></Card>
          ))}
        </div>

        <Card>
          <CardHeader icon={<Pill className="h-4 w-4" />} title="Medication list"
            subtitle="Prescribed, patient-reported, discontinued and historical medicines with their sources."
            action={canEdit && <Button size="sm" variant="secondary" onClick={() => setAdding(true)}><Plus className="h-4 w-4" /> Add self-reported</Button>} />
          <div className="px-5 pt-4">
            <Tabs value={tab} onChange={setTab} tabs={[
              { value: "current", label: "Current", count: current.length },
              { value: "past", label: "Past", count: past.length },
              { value: "all", label: "All", count: meds.length },
            ]} />
          </div>
          {shown.length === 0 ? <Empty icon={<Pill className="h-5 w-5" />} title="No medicines in this view" /> : (
            <ul className="divide-y divide-slate-100">
              {shown.map((m) => (
                <li key={m.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-start gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-700"><Pill className="h-5 w-5" /></div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-navy-900">{m.name}</p>
                        <Badge tone={STATUS_TONE[m.status]}>{STATUS_LABEL[m.status]}</Badge>
                        {!m.verified && <Badge tone="amber">Unverified</Badge>}
                        {m.drug_class && <span className="text-xs text-slate-500">{m.drug_class}</span>}
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {m.dosage || <span className="text-amber-700">dose not recorded</span>} · {m.frequency || <span className="text-amber-700">frequency not recorded</span>}
                        {m.duration && <> · {m.duration}</>}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {m.start_date ? `Started ${fmtDate(m.start_date)}` : "Start date unknown"}
                        {m.end_date && ` · Ended ${fmtDate(m.end_date)}`}
                        {m.prescribed_by ? ` · ${m.prescribed_by}` : " · self-reported"}
                        {m.brand_name && ` · ${m.brand_name}`}
                      </p>
                      {m.notes && <p className="mt-1 text-xs italic text-slate-500">{m.notes}</p>}
                      {m.source_document_id && (
                        <button onClick={() => setViewDoc({ id: m.source_document_id!, title: m.source_document_title })} className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-teal-700 hover:underline">
                          <FileText className="h-3.5 w-3.5" /> {m.source_document_title || "Source prescription"}
                        </button>
                      )}
                    </div>
                    {canEdit && ["active", "patient_reported"].includes(m.status) ? (
                      <select className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-navy-800" value={m.adherence || ""}
                        onChange={(e) => setAdherence(m.id, e.target.value)} aria-label={`Adherence for ${m.name}`}>
                        <option value="" disabled>Report adherence…</option>
                        {ADHERENCE.map((a) => <option key={a.v} value={a.v}>{a.l}</option>)}
                      </select>
                    ) : m.adherence ? <Badge tone="slate">{ADHERENCE.find((a) => a.v === m.adherence)?.l}</Badge> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader icon={<History className="h-4 w-4" />} title="Medication history" subtitle="Starts, dose changes and stops, newest first." />
          <ol className="max-h-96 space-y-0 overflow-y-auto px-5 py-3">
            {(hist.data?.events ?? []).map((e) => (
              <li key={e.id} className="flex gap-3 border-b border-slate-50 py-2 text-sm last:border-0">
                <span className="w-24 shrink-0 text-xs text-slate-500">{fmtDate(e.event_date)}</span>
                <Badge tone={e.event_type === "stopped" ? "rose" : e.event_type === "dose_changed" ? "amber" : e.event_type === "proposed" ? "amber" : "teal"}>{e.event_type.replace("_", " ")}</Badge>
                <span className="text-navy-800">{e.description}</span>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader icon={<ShieldCheck className="h-4 w-4" />} title="Medication review flags" subtitle="For qualified clinician review" />
          <div className="space-y-3 p-4">
            <FlagList flags={data?.flags ?? []} />
            <Notice>{data?.flags_note}</Notice>
          </div>
        </Card>
      </div>

      <Modal open={adding} onClose={() => setAdding(false)} title="Add a self-reported medicine"
        footer={<><Button variant="secondary" onClick={() => setAdding(false)}>Cancel</Button><Button onClick={save} loading={saving} disabled={form.name.trim().length < 2}>Save</Button></>}>
        <div className="space-y-3">
          <Notice>Use this for over-the-counter medicines or supplements you take. It is saved as <b>patient-reported, unverified</b> and does not change any prescription.</Notice>
          <Field label="Medicine name *"><input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Pantoprazole" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Dose"><input className={inputCls} value={form.dosage} onChange={(e) => setForm({ ...form, dosage: e.target.value })} placeholder="40 mg" /></Field>
            <Field label="How often"><input className={inputCls} value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} placeholder="Once daily" /></Field>
          </div>
          <Field label="Started on"><input type="date" className={inputCls} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></Field>
          <Field label="Notes"><input className={inputCls} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          {formErr && <ErrorBox message={formErr} />}
        </div>
      </Modal>
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </div>
  );
}
