"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Clock, Eye, FileText, Lock, Plus, ShieldAlert, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import { SCOPE_LABEL, type AIResult, type Doc, type Flag, type Medication, type PatientProfile, type Scope, type Trend } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, PageHeader, Spinner, Tabs } from "@/components/ui";
import { TimelineView } from "@/components/TimelineView";
import { MedicationsView } from "@/components/MedicationsView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { AssistantView, AnswerCard } from "@/components/AssistantView";
import { ConsultationsList } from "@/components/ConsultationsList";
import { ConsultationForm } from "@/components/ConsultationForm";
import { ConditionsAllergies } from "@/components/ConditionsAllergies";
import { DocumentViewer } from "@/components/DocumentViewer";
import { FlagList } from "@/components/FlagList";
import { TrendChart } from "@/components/TrendChart";
import { CATEGORY_LABEL, fmtDate, initials, relTime } from "@/lib/format";

type Tab = "summary" | "timeline" | "medications" | "labs" | "documents" | "consultations" | "assistant";

function Locked({ scope }: { scope: string }) {
  return <Card><Empty icon={<Lock className="h-5 w-5" />} title={`${scope} not shared`}>The patient has not included this in your access. Request a wider scope if clinically needed.</Empty></Card>;
}

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const profile = useApi<PatientProfile>(`/api/patients/${id}`);
  const [tab, setTab] = useState<Tab>("summary");
  const [summary, setSummary] = useState<AIResult | null>(null);
  const [sumBusy, setSumBusy] = useState(false);
  const [sumErr, setSumErr] = useState<string | null>(null);
  const [consultOpen, setConsultOpen] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [viewDoc, setViewDoc] = useState<{ id: string; title?: string | null } | null>(null);
  const scopes: Scope[] = profile.data?.shared_scopes ?? [];
  const has = (s: Scope) => scopes.includes(s);
  const meds = useApi<{ medications: Medication[]; flags: Flag[] }>(profile.data && has("medications") ? `/api/medications?patient_id=${id}` : null);
  const trends = useApi<{ trends: Trend[] }>(profile.data && has("labs") ? `/api/analytics/health-trends?patient_id=${id}` : null);
  const docs = useApi<{ documents: Doc[] }>(profile.data && has("documents") ? `/api/documents?patient_id=${id}` : null);
  const grants = useApi<{ grants: { patient_id: string; expires_at: string; state: string }[] }>("/api/access-grants");
  const grant = grants.data?.grants.find((g) => g.patient_id === id && g.state === "active");

  async function summarise() {
    setSumBusy(true); setSumErr(null);
    try { setSummary(await api<AIResult>("/api/ai/summarize-history", { body: { patient_id: id } })); }
    catch (e) { setSumErr((e as Error).message); } finally { setSumBusy(false); }
  }

  if (profile.loading && !profile.data) return <Spinner label="Checking consent and loading record…" />;
  if (profile.error) return (
    <div className="space-y-4">
      <Link href="/doctor/patients" className="inline-flex items-center gap-1 text-sm text-teal-700"><ArrowLeft className="h-4 w-4" /> My patients</Link>
      <Card><Empty icon={<Lock className="h-5 w-5" />} title="Access not available">{profile.error}. The patient may have revoked access, or the grant expired. This attempt has been recorded in the audit log.</Empty></Card>
    </div>
  );
  const p = profile.data!;
  const t = Object.fromEntries((trends.data?.trends ?? []).map((x) => [x.code, x]));
  const flags = (meds.data?.flags ?? []).filter((f) => f.severity !== "info");
  const current = (meds.data?.medications ?? []).filter((m) => ["active", "patient_reported", "proposed"].includes(m.status));

  return (
    <div className="space-y-5">
      <Link href="/doctor/patients" className="inline-flex items-center gap-1 text-sm text-teal-700"><ArrowLeft className="h-4 w-4" /> My patients</Link>
      <Card className="p-5">
        <div className="flex flex-wrap items-start gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-teal-700 text-lg font-semibold text-white">{initials(p.full_name)}</div>
          <div className="min-w-0 flex-1">
            <PageHeader title={p.full_name} subtitle={`${p.age} y · ${p.sex} · blood group ${p.blood_group ?? "—"} · ${p.city ?? ""} · DOB ${fmtDate(p.date_of_birth)}`} />
            <div className="-mt-3 flex flex-wrap gap-1.5">{scopes.map((s) => <Badge key={s} tone="teal">{SCOPE_LABEL[s]}</Badge>)}</div>
            {grant && <p className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3.5 w-3.5" /> Consent expires {relTime(grant.expires_at)} · synthetic patient</p>}
          </div>
          <div className="flex flex-wrap gap-2">
            {has("consultations") && <Button variant="secondary" onClick={() => setConsultOpen(true)}><Plus className="h-4 w-4" /> New consultation</Button>}
            <Button variant="teal" onClick={summarise} loading={sumBusy} disabled={!has("history")}><Sparkles className="h-4 w-4" /> AI clinical summary</Button>
          </div>
        </div>
      </Card>

      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "summary", label: "Summary" }, { value: "timeline", label: "Timeline" }, { value: "medications", label: "Medications" },
        { value: "labs", label: "Labs & vitals" }, { value: "documents", label: "Documents" }, { value: "consultations", label: "Consultations" },
        { value: "assistant", label: "Ask AI" },
      ]} />

      {tab === "summary" && (
        <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
          <div className="space-y-6">
            <Card>
              <CardHeader icon={<Sparkles className="h-4 w-4" />} title="AI-assisted clinical summary" subtitle="Generated only from records this patient shared with you, with sources" />
              <div className="p-5">
                {sumErr && <ErrorBox message={sumErr} />}
                {summary ? <AnswerCard result={summary} onCite={has("documents") ? (cid, label) => cid.startsWith("doc") && setViewDoc({ id: cid, title: label }) : undefined} />
                  : <div className="flex flex-col items-start gap-3"><p className="text-sm text-slate-600">Generate a summary of history, current medicines, allergies, key lab trends and the latest consultation.</p><Button variant="teal" onClick={summarise} loading={sumBusy} disabled={!has("history")}><Sparkles className="h-4 w-4" /> Generate summary</Button></div>}
              </div>
            </Card>
            {has("labs") && t.hba1c && (
              <div className="grid gap-4 md:grid-cols-2">
                <Card><CardHeader title="HbA1c" subtitle={`Latest ${t.hba1c.latest.value}% · ${fmtDate(t.hba1c.latest.date)}`} /><div className="p-3"><TrendChart series={[t.hba1c]} height={180} /></div></Card>
                {t.bp_systolic && <Card><CardHeader title="Blood pressure" subtitle={`Latest ${t.bp_systolic.latest.value}/${t.bp_diastolic?.latest.value} mmHg`} /><div className="p-3"><TrendChart series={[t.bp_systolic, t.bp_diastolic].filter(Boolean)} height={180} /></div></Card>}
              </div>
            )}
            {has("medications") && (
              <Card>
                <CardHeader icon={<ShieldAlert className="h-4 w-4" />} title="Medication review" subtitle={`${current.length} current medicines · flags require your clinical judgement`} />
                <div className="p-4"><FlagList flags={flags} /></div>
              </Card>
            )}
          </div>
          <div className="space-y-4">
            {has("history") || has("allergies") ? <ConditionsAllergies patientId={id} /> : <Locked scope="History" />}
            {has("medications") && (
              <Card>
                <CardHeader title="Current medicines" />
                <ul className="divide-y divide-slate-100">
                  {current.map((m) => (
                    <li key={m.id} className="px-5 py-2.5 text-sm">
                      <p className="font-medium text-navy-900">{m.name}</p>
                      <p className="text-xs text-slate-500">{m.frequency || "frequency not recorded"} · {m.prescribed_by || "patient-reported"}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
        </div>
      )}
      {tab === "timeline" && (has("history") ? <TimelineView patientId={id} /> : <Locked scope="History" />)}
      {tab === "medications" && (has("medications") ? <MedicationsView patientId={id} /> : <Locked scope="Medications" />)}
      {tab === "labs" && (has("labs") ? <AnalyticsView patientId={id} /> : <Locked scope="Lab results" />)}
      {tab === "documents" && (has("documents") ? (
        <Card>
          {docs.loading && !docs.data ? <Spinner /> : (
            <ul className="divide-y divide-slate-100">
              {(docs.data?.documents ?? []).map((d) => (
                <li key={d.id} className="flex items-center gap-3 px-5 py-3">
                  <FileText className="h-5 w-5 text-navy-600" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-navy-900">{d.title}</p>
                    <p className="text-xs text-slate-500">{CATEGORY_LABEL[d.category]} · {fmtDate(d.document_date)}{d.doctor_name ? ` · ${d.doctor_name}` : ""}</p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => setViewDoc({ id: d.id, title: d.title })}><Eye className="h-4 w-4" /> View</Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      ) : <Locked scope="Documents" />)}
      {tab === "consultations" && (has("consultations") ? (
        <div className="space-y-3">
          <div className="flex justify-end"><Button onClick={() => setConsultOpen(true)}><Plus className="h-4 w-4" /> New consultation</Button></div>
          <ConsultationsList patientId={id} canViewDocs={has("documents")} refreshKey={refresh} />
        </div>
      ) : <Locked scope="Consultations" />)}
      {tab === "assistant" && <AssistantView patientId={id} role="doctor" storageKey={`doctor.${user!.id}.${id}`} canViewDocs={has("documents")} />}

      <ConsultationForm open={consultOpen} patientId={id} patientName={p.full_name} onClose={() => setConsultOpen(false)}
        onSaved={() => { setConsultOpen(false); setRefresh((r) => r + 1); setTab("consultations"); meds.reload(); }} />
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </div>
  );
}
