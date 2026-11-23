"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, ShieldAlert, UserRound } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { PatientProfile } from "@/lib/types";
import { Button, Card, CardHeader, ErrorBox, Field, inputCls, PageHeader, Spinner } from "@/components/ui";
import { fmtDate } from "@/lib/format";
import { DemoSystemCard } from "@/components/DemoSystemCard";

export default function SettingsPage() {
  const me = useApi<PatientProfile & { email: string }>("/api/patients/me");
  const [form, setForm] = useState({ phone: "", city: "", emergency_contact: "", blood_group: "", height_cm: "" });
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [alg, setAlg] = useState({ substance: "", reaction: "", severity: "unknown" });
  const [algMsg, setAlgMsg] = useState<string | null>(null);

  useEffect(() => {
    if (me.data) setForm({ phone: me.data.phone ?? "", city: me.data.city ?? "", emergency_contact: me.data.emergency_contact ?? "", blood_group: me.data.blood_group ?? "", height_cm: me.data.height_cm ? String(me.data.height_cm) : "" });
  }, [me.data]);

  async function save() {
    setErr(null); setSaved(false);
    try {
      await api("/api/patients/me", { method: "PATCH", body: { ...form, height_cm: form.height_cm ? Number(form.height_cm) : null } });
      setSaved(true); me.reload();
    } catch (e) { setErr((e as Error).message); }
  }

  async function addAllergy() {
    setAlgMsg(null);
    try {
      await api("/api/patients/me/allergies", { body: { ...alg, reaction: alg.reaction || null } });
      setAlg({ substance: "", reaction: "", severity: "unknown" });
      setAlgMsg("Allergy added. It will be used in medication review flags.");
    } catch (e) { setAlgMsg((e as Error).message); }
  }

  if (me.loading && !me.data) return <Spinner />;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Profile & Settings" title="Your profile" subtitle="Fictional demo profile. Do not enter real personal information." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader icon={<UserRound className="h-4 w-4" />} title={me.data?.full_name ?? "Profile"} subtitle={`${me.data?.email} · born ${fmtDate(me.data?.date_of_birth)} (${me.data?.age} y) · ${me.data?.sex}`} />
          <div className="grid gap-3 p-5 sm:grid-cols-2">
            <Field label="Phone"><input className={inputCls} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="City"><input className={inputCls} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
            <Field label="Blood group"><input className={inputCls} value={form.blood_group} onChange={(e) => setForm({ ...form, blood_group: e.target.value })} maxLength={5} /></Field>
            <Field label="Height (cm)"><input type="number" className={inputCls} value={form.height_cm} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} /></Field>
            <div className="sm:col-span-2"><Field label="Emergency contact"><input className={inputCls} value={form.emergency_contact} onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })} /></Field></div>
            <div className="flex items-center gap-3 sm:col-span-2">
              <Button onClick={save}>Save profile</Button>
              {saved && <span className="flex items-center gap-1 text-sm text-emerald-700"><CheckCircle2 className="h-4 w-4" /> Saved</span>}
            </div>
            {err && <div className="sm:col-span-2"><ErrorBox message={err} /></div>}
          </div>
        </Card>

        <Card>
          <CardHeader icon={<ShieldAlert className="h-4 w-4" />} title="Report an allergy" subtitle="Used to check documented allergy conflicts" />
          <div className="space-y-3 p-5">
            <Field label="Substance or medicine"><input className={inputCls} value={alg.substance} onChange={(e) => setAlg({ ...alg, substance: e.target.value })} placeholder="e.g. Sulfonamides" /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Reaction"><input className={inputCls} value={alg.reaction} onChange={(e) => setAlg({ ...alg, reaction: e.target.value })} placeholder="Rash" /></Field>
              <Field label="Severity">
                <select className={inputCls} value={alg.severity} onChange={(e) => setAlg({ ...alg, severity: e.target.value })}>
                  {["unknown", "mild", "moderate", "severe"].map((s) => <option key={s}>{s}</option>)}
                </select>
              </Field>
            </div>
            <Button variant="secondary" onClick={addAllergy} disabled={alg.substance.trim().length < 2}>Add allergy</Button>
            {algMsg && <p className="text-sm text-slate-600">{algMsg}</p>}
          </div>
        </Card>

        <DemoSystemCard />
      </div>
    </div>
  );
}

