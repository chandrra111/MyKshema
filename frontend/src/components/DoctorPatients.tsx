"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronRight, Clock, KeyRound, Search, Send, Users } from "lucide-react";
import { api } from "@/lib/api";
import { SCOPE_LABEL, ALL_SCOPES, type AccessRequest, type Scope } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Field, inputCls, Notice, Spinner } from "./ui";
import { cx, fmtDate, initials, relTime } from "@/lib/format";

export interface DoctorPatient {
  patient_id: string; full_name: string; age: number; sex: string; city?: string | null; scopes: Scope[];
  expires_at: string; active_conditions: string[]; last_consultation?: string | null;
}
export interface DoctorPatientsResp { patients: DoctorPatient[]; pending_requests: (AccessRequest & { patient_name?: string })[]; note: string }

export function PatientCards({ data, loading, error, reload, filter = "" }: { data: DoctorPatientsResp | null; loading: boolean; error: string | null; reload: () => void; filter?: string }) {
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const list = (data?.patients ?? []).filter((p) => p.full_name.toLowerCase().includes(filter.toLowerCase()));
  if (!list.length) return <Card><Empty icon={<Users className="h-5 w-5" />} title="No patients are sharing records with you">Request access below, or ask a patient to share from their Doctor Connect page.</Empty></Card>;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {list.map((p) => (
        <Link key={p.patient_id} href={`/doctor/patients/${p.patient_id}`} className="group">
          <Card className="h-full p-5 transition group-hover:border-teal-300 group-hover:shadow-lift">
            <div className="flex items-start gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-teal-700 font-semibold text-white">{initials(p.full_name)}</div>
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-navy-900">{p.full_name}</p>
                <p className="text-sm text-slate-500">{p.age} y · <span className="capitalize">{p.sex}</span>{p.city ? ` · ${p.city}` : ""}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-teal-600" />
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">{p.active_conditions.map((c) => <Badge key={c} tone="navy">{c}</Badge>)}</div>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> Access expires {relTime(p.expires_at)}</span>
              {p.last_consultation && <span>Last visit {fmtDate(p.last_consultation)}</span>}
            </div>
            <p className="mt-2 text-[11px] text-slate-400">Shared: {p.scopes.map((s) => SCOPE_LABEL[s]).join(" · ")}</p>
          </Card>
        </Link>
      ))}
    </div>
  );
}

export function PatientSearch({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="relative max-w-sm">
      <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
      <input className={cx(inputCls, "pl-9")} placeholder="Filter patients" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

export function RequestAccessCard({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  const [found, setFound] = useState<{ patient_id: string; full_name: string; city?: string } | null>(null);
  const [scopes, setScopes] = useState<Scope[]>(["history", "medications", "allergies", "labs", "consultations"]);
  const [reason, setReason] = useState("");
  const [hours, setHours] = useState(72);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function lookup() {
    setErr(null); setFound(null); setOk(null);
    try { setFound(await api(`/api/doctor/patient-lookup?email=${encodeURIComponent(email)}`)); }
    catch (e) { setErr((e as Error).message); }
  }
  async function send() {
    if (!found) return;
    setBusy(true); setErr(null);
    try {
      await api("/api/access-requests", { body: { patient_id: found.patient_id, scopes, reason: reason || null, duration_hours: hours } });
      setOk(`Request sent to ${found.full_name}. They can approve, narrow or deny it from their Doctor Connect page.`);
      setFound(null); setEmail(""); setReason(""); onDone();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeader icon={<KeyRound className="h-4 w-4" />} title="Request patient access" subtitle="Patients approve, narrow or deny every request" />
      <div className="space-y-3 p-5">
        <div className="flex gap-2">
          <input className={inputCls} placeholder="Patient's MyKshema demo email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button variant="secondary" onClick={lookup} disabled={!email.includes("@")}>Find</Button>
        </div>
        <p className="text-xs text-slate-500">Try <button className="underline" onClick={() => setEmail("rahul.menon@demo.mykshema.test")}>rahul.menon@demo.mykshema.test</button> — lookup reveals name and city only.</p>
        {found && (
          <div className="space-y-3 rounded-xl border border-slate-200 p-3">
            <p className="text-sm"><b>{found.full_name}</b> <span className="text-slate-500">· {found.city}</span></p>
            <div className="flex flex-wrap gap-1.5">
              {ALL_SCOPES.map((s) => {
                const on = scopes.includes(s);
                return <button key={s} onClick={() => setScopes(on ? scopes.filter((x) => x !== s) : [...scopes, s])}
                  className={cx("rounded-full border px-2.5 py-1 text-xs", on ? "border-teal-300 bg-teal-50 text-teal-800" : "border-slate-200 text-slate-500")}>{SCOPE_LABEL[s]}</button>;
              })}
            </div>
            <div className="grid gap-2 sm:grid-cols-[1fr_140px]">
              <Field label="Reason"><input className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Pre-consultation review" /></Field>
              <Field label="Duration">
                <select className={inputCls} value={hours} onChange={(e) => setHours(Number(e.target.value))}>
                  <option value={24}>24 hours</option><option value={72}>3 days</option><option value={168}>7 days</option><option value={720}>30 days</option>
                </select>
              </Field>
            </div>
            <Button variant="teal" onClick={send} loading={busy} disabled={!scopes.length}><Send className="h-4 w-4" /> Send request</Button>
          </div>
        )}
        {err && <ErrorBox message={err} />}
        {ok && <Notice>{ok}</Notice>}
      </div>
    </Card>
  );
}
