"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Doc, ELab, EMed, Extraction } from "@/lib/types";
import { Badge, Button, ErrorBox, Field, inputCls, Modal, Notice } from "./ui";
import { CATEGORY_LABEL, cx } from "@/lib/format";

function Conf({ c }: { c: number }) {
  if (!c) return <Badge tone="slate">not found</Badge>;
  const tone = c >= 0.8 ? "emerald" : c >= 0.5 ? "amber" : "rose";
  return <Badge tone={tone}>{Math.round(c * 100)}% confidence</Badge>;
}

export function ExtractionReview({ doc, extraction, onClose, onSaved }: { doc: Doc | null; extraction: Extraction | null; onClose: () => void; onSaved: (msg: string) => void }) {
  const [f, setF] = useState({ category: "", consultation_date: "", doctor_name: "", hospital: "", diagnosis: "", allergies: "" });
  const [meds, setMeds] = useState<EMed[]>([]);
  const [labs, setLabs] = useState<ELab[]>([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ack, setAck] = useState(false);

  useEffect(() => {
    if (!extraction || !doc) return;
    const x = extraction.fields;
    setF({
      category: x.category.value || doc.category, consultation_date: x.consultation_date.value || doc.document_date || "",
      doctor_name: x.doctor_name.value || doc.doctor_name || "", hospital: x.hospital.value || doc.hospital || "",
      diagnosis: x.diagnosis.value || "", allergies: x.allergies.value || "",
    });
    setMeds(x.medications.map((m) => ({ ...m })));
    setLabs(x.labs.map((l) => ({ ...l })));
    setAck(false); setErr(null);
  }, [extraction, doc]);

  if (!doc || !extraction) return null;
  const x = extraction.fields;

  async function confirm() {
    setSaving(true); setErr(null);
    try {
      const r = await api<{ created: Record<string, number | string | null> }>(`/api/documents/${doc!.id}/confirm-extraction`, {
        body: {
          ...f, consultation_date: f.consultation_date || null, category: f.category || null,
          medications: meds.filter((m) => m.name.trim()),
          labs: labs.filter((l) => l.test_name.trim()).map((l) => ({ ...l, value: l.value === null || l.value === undefined || (l.value as unknown) === "" ? null : Number(l.value) })),
        },
      });
      const c = r.created;
      onSaved(`Saved to your record: ${c.observations} lab values, ${c.medications} medicines, ${c.allergies} allergies, ${c.conditions} diagnoses.`);
    } catch (e) { setErr((e as Error).message); } finally { setSaving(false); }
  }

  async function skip() {
    await api(`/api/documents/${doc!.id}/skip-extraction`, { method: "POST" });
    onSaved("Document kept in your vault without adding extracted data.");
  }

  const methodTone = extraction.method === "demo_template" ? "warn" : "info";
  return (
    <Modal open onClose={onClose} title={`Review extracted information · ${doc.title}`} wide
      footer={<>
        <Button variant="ghost" onClick={skip}>Keep file only</Button>
        <Button variant="secondary" onClick={onClose}>Later</Button>
        <Button variant="teal" onClick={confirm} loading={saving} disabled={!ack}><CheckCircle2 className="h-4 w-4" /> Confirm & save</Button>
      </>}>
      <div className="space-y-5">
        <Notice tone={methodTone}>
          <b>{extraction.method_label}</b>. Overall confidence {Math.round(extraction.overall_confidence * 100)}%.
          Nothing is added to your health record until you review and confirm. Correct anything that is wrong.
          {extraction.warnings.map((w) => <span key={w} className="mt-1 block">• {w}</span>)}
        </Notice>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Category" hint={<Conf c={x.category.confidence} />}>
            <select className={inputCls} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
              {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="Date" hint={<Conf c={x.consultation_date.confidence} />}><input type="date" className={inputCls} value={f.consultation_date} onChange={(e) => setF({ ...f, consultation_date: e.target.value })} /></Field>
          <Field label="Doctor" hint={<Conf c={x.doctor_name.confidence} />}><input className={inputCls} value={f.doctor_name} onChange={(e) => setF({ ...f, doctor_name: e.target.value })} /></Field>
          <Field label="Hospital / lab" hint={<Conf c={x.hospital.confidence} />}><input className={inputCls} value={f.hospital} onChange={(e) => setF({ ...f, hospital: e.target.value })} /></Field>
          <Field label="Diagnosis (separate with ;)" hint={<Conf c={x.diagnosis.confidence} />}><input className={inputCls} value={f.diagnosis} onChange={(e) => setF({ ...f, diagnosis: e.target.value })} /></Field>
          <Field label="Allergies (separate with ;)" hint={<Conf c={x.allergies.confidence} />}><input className={inputCls} value={f.allergies} onChange={(e) => setF({ ...f, allergies: e.target.value })} /></Field>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-navy-900">Medications ({meds.length})</p>
            <Button size="sm" variant="ghost" onClick={() => setMeds([...meds, { name: "", dosage: "", frequency: "", duration: "" }])}><Plus className="h-4 w-4" /> Add</Button>
          </div>
          {meds.length === 0 && <p className="text-sm text-slate-500">No medications detected.</p>}
          <div className="space-y-2">
            {meds.map((m, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-2 sm:grid-cols-[1.3fr_0.8fr_1.2fr_0.8fr_auto]">
                {(["name", "dosage", "frequency", "duration"] as const).map((k) => (
                  <input key={k} className={inputCls} placeholder={k} value={m[k] ?? ""} onChange={(e) => setMeds(meds.map((x, j) => j === i ? { ...x, [k]: e.target.value } : x))} aria-label={`Medication ${k}`} />
                ))}
                <button onClick={() => setMeds(meds.filter((_, j) => j !== i))} className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-rose-600" aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-navy-900">Lab results ({labs.length})</p>
            <Button size="sm" variant="ghost" onClick={() => setLabs([...labs, { test_name: "", value: null, unit: "", reference_range: "" }])}><Plus className="h-4 w-4" /> Add</Button>
          </div>
          {labs.length === 0 && <p className="text-sm text-slate-500">No lab values detected.</p>}
          <div className="space-y-2">
            {labs.map((l, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-2 sm:grid-cols-[1.4fr_0.7fr_0.7fr_1.2fr_auto]">
                <input className={inputCls} placeholder="test name" value={l.test_name} onChange={(e) => setLabs(labs.map((x, j) => j === i ? { ...x, test_name: e.target.value } : x))} aria-label="Test name" />
                <input className={cx(inputCls)} placeholder="value" type="number" step="any" value={l.value ?? ""} onChange={(e) => setLabs(labs.map((x, j) => j === i ? { ...x, value: e.target.value === "" ? null : Number(e.target.value) } : x))} aria-label="Value" />
                <input className={inputCls} placeholder="unit" value={l.unit ?? ""} onChange={(e) => setLabs(labs.map((x, j) => j === i ? { ...x, unit: e.target.value } : x))} aria-label="Unit" />
                <input className={inputCls} placeholder="reference range as printed" value={l.reference_range ?? ""} onChange={(e) => setLabs(labs.map((x, j) => j === i ? { ...x, reference_range: e.target.value } : x))} aria-label="Reference range" />
                <button onClick={() => setLabs(labs.filter((_, j) => j !== i))} className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-rose-600" aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </div>

        {extraction.raw_text_excerpt && (
          <details className="rounded-xl border border-slate-200">
            <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-navy-800">Text read from the document</summary>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap px-4 pb-3 text-xs text-slate-600">{extraction.raw_text_excerpt}</pre>
          </details>
        )}

        <label className="flex items-start gap-2 rounded-xl border border-teal-200 bg-teal-50/50 p-3 text-sm text-navy-800">
          <input type="checkbox" className="mt-0.5 h-4 w-4 accent-teal-600" checked={ack} onChange={(e) => setAck(e.target.checked)} />
          I have checked these values against the original document. Saved values keep a link to this source document.
        </label>
        {err && <ErrorBox message={err} />}
      </div>
    </Modal>
  );
}
