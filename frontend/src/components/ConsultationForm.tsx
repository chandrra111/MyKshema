"use client";

import { useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { RxItem } from "@/lib/types";
import { Button, ErrorBox, Field, inputCls, Modal, Notice } from "./ui";

export function ConsultationForm({ open, patientId, patientName, onClose, onSaved }: { open: boolean; patientId: string; patientName: string; onClose: () => void; onSaved: () => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({ consultation_date: today, reason: "", notes: "", diagnoses: "", follow_up: "", follow_up_date: "" });
  const [rx, setRx] = useState<RxItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setBusy(true); setErr(null);
    try {
      await api("/api/consultations", {
        body: {
          patient_id: patientId, consultation_date: f.consultation_date, reason: f.reason || null, notes: f.notes,
          diagnoses: f.diagnoses.split(";").map((d) => d.trim()).filter(Boolean),
          follow_up: f.follow_up || null, follow_up_date: f.follow_up_date || null,
          prescription_items: rx.filter((r) => r.name.trim()).map((r) => ({ ...r, duration: r.duration || null })),
        },
      });
      setF({ consultation_date: today, reason: "", notes: "", diagnoses: "", follow_up: "", follow_up_date: "" });
      setRx([]);
      onSaved();
    } catch (e) {
      const ex = e as { message: string; details?: { field: string; message: string }[] };
      setErr(ex.details?.length ? ex.details.map((d) => `${d.field}: ${d.message}`).join("; ") : ex.message);
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title={`New consultation · ${patientName}`} wide
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button variant="teal" onClick={save} loading={busy} disabled={f.notes.trim().length < 3}><Save className="h-4 w-4" /> Save demo consultation</Button></>}>
      <div className="space-y-4">
        <Notice tone="warn">Demo record. Prescriptions here are <b>authored by you</b>, saved as <b>proposed (demo)</b> and are not legal prescriptions. MyKshema&apos;s AI never generates or issues prescriptions.</Notice>
        <div className="grid gap-3 sm:grid-cols-[160px_1fr]">
          <Field label="Date"><input type="date" className={inputCls} value={f.consultation_date} onChange={(e) => setF({ ...f, consultation_date: e.target.value })} /></Field>
          <Field label="Reason for visit"><input className={inputCls} value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} placeholder="e.g. Quarterly diabetes review" /></Field>
        </div>
        <Field label="Clinical notes *"><textarea rows={5} className={inputCls} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} placeholder="History, examination, assessment, plan…" /></Field>
        <Field label="Diagnoses" hint="Separate multiple diagnoses with ;"><input className={inputCls} value={f.diagnoses} onChange={(e) => setF({ ...f, diagnoses: e.target.value })} /></Field>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-navy-800">Proposed prescription (doctor-authored)</p>
            <Button size="sm" variant="ghost" onClick={() => setRx([...rx, { name: "", dosage: "", frequency: "", duration: "" }])}><Plus className="h-4 w-4" /> Add medicine</Button>
          </div>
          {rx.length === 0 && <p className="text-sm text-slate-500">No medicines proposed.</p>}
          <div className="space-y-2">
            {rx.map((r, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-2 sm:grid-cols-[1.3fr_0.8fr_1.2fr_0.8fr_auto]">
                {(["name", "dosage", "frequency", "duration"] as const).map((k) => (
                  <input key={k} className={inputCls} placeholder={k + (k === "duration" ? "" : " *")} value={r[k] ?? ""} aria-label={`Prescription ${k}`}
                    onChange={(e) => setRx(rx.map((x, j) => j === i ? { ...x, [k]: e.target.value } : x))} />
                ))}
                <button onClick={() => setRx(rx.filter((_, j) => j !== i))} className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-rose-600" aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
          <Field label="Follow-up instructions"><input className={inputCls} value={f.follow_up} onChange={(e) => setF({ ...f, follow_up: e.target.value })} placeholder="e.g. Review in 3 months with HbA1c" /></Field>
          <Field label="Follow-up date"><input type="date" className={inputCls} value={f.follow_up_date} onChange={(e) => setF({ ...f, follow_up_date: e.target.value })} /></Field>
        </div>
        {err && <ErrorBox message={err} />}
      </div>
    </Modal>
  );
}
