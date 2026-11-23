"use client";

import { useRef, useState } from "react";
import { CheckCircle2, Download, Eye, FileImage, FileText, FolderLock, Search, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { api, fileObjectUrl, qs } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Doc, Extraction } from "@/lib/types";
import { Badge, Button, Card, Empty, ErrorBox, Field, inputCls, Modal, Notice, PageHeader, Spinner } from "@/components/ui";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ExtractionReview } from "@/components/ExtractionReview";
import { CATEGORY_LABEL, cx, fmtBytes, fmtDate } from "@/lib/format";

const ACCEPT = ".pdf,.jpg,.jpeg,.png";
const EXT_STATUS: Record<string, { l: string; tone: "slate" | "amber" | "emerald" }> = {
  not_started: { l: "Not analysed", tone: "slate" }, pending_review: { l: "Needs review", tone: "amber" },
  confirmed: { l: "Confirmed", tone: "emerald" }, skipped: { l: "File only", tone: "slate" },
};

export default function VaultPage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, error, loading, reload } = useApi<{ documents: Doc[]; count: number; max_upload_mb: number }>(`/api/documents${qs({ q, category, date_from: from, date_to: to })}`);
  const [file, setFile] = useState<File | null>(null);
  const [meta, setMeta] = useState({ title: "", category: "blood_report", document_date: "", doctor_name: "", hospital: "", notes: "" });
  const [drag, setDrag] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [upErr, setUpErr] = useState<string | null>(null);
  const [review, setReview] = useState<{ doc: Doc; extraction: Extraction } | null>(null);
  const [viewDoc, setViewDoc] = useState<Doc | null>(null);
  const [toDelete, setToDelete] = useState<Doc | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const maxMb = data?.max_upload_mb ?? 10;

  function pick(f: File | null | undefined) {
    setUpErr(null);
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "jpg", "jpeg", "png"].includes(ext)) { setUpErr("Only PDF, JPG, JPEG and PNG files are allowed."); return; }
    if (f.size > maxMb * 1024 * 1024) { setUpErr(`File is larger than the ${maxMb} MB limit.`); return; }
    setFile(f);
    setMeta((m) => ({ ...m, title: m.title || f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ") }));
  }

  async function upload() {
    if (!file) return;
    setUploading(true); setUpErr(null);
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(meta).forEach(([k, v]) => v && fd.append(k, v));
    fd.append("analyze", "true");
    try {
      const r = await api<{ document: Doc; extraction: Extraction | null }>("/api/documents/upload", { form: fd });
      setFile(null); setMeta({ title: "", category: "blood_report", document_date: "", doctor_name: "", hospital: "", notes: "" });
      if (inputRef.current) inputRef.current.value = "";
      reload();
      if (r.extraction) setReview({ doc: r.document, extraction: r.extraction });
    } catch (e) { setUpErr((e as Error).message); } finally { setUploading(false); }
  }

  async function openReview(d: Doc) {
    const r = await api<{ document: Doc; extraction: Extraction | null }>(`/api/documents/${d.id}`);
    if (r.extraction && r.extraction.status === "pending_review") { setReview({ doc: r.document, extraction: r.extraction }); return; }
    const ext = await api<Extraction>(`/api/documents/${d.id}/analyze`, { method: "POST" });
    setReview({ doc: r.document, extraction: ext });
  }

  async function download(d: Doc) {
    const u = await fileObjectUrl(d.id, true);
    const a = document.createElement("a");
    a.href = u; a.download = d.original_filename; a.click();
    setTimeout(() => URL.revokeObjectURL(u), 2000);
  }

  async function doDelete() {
    if (!toDelete) return;
    await api(`/api/documents/${toDelete.id}`, { method: "DELETE" });
    setToDelete(null); setToast("Document deleted from local demo storage."); reload();
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="My Health Vault" title="Medical documents" subtitle="Prescriptions, reports, scans and summaries — stored privately and served only to you and the doctors you authorise." />

      {toast && <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4" />{toast}<button className="ml-auto text-xs underline" onClick={() => setToast(null)}>Dismiss</button></div>}

      <Card className="p-5">
        <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
            onClick={() => inputRef.current?.click()} role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
            className={cx("flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition",
              drag ? "border-teal-400 bg-teal-50" : "border-slate-200 bg-slate-50/60 hover:border-teal-300 hover:bg-teal-50/40")}>
            <UploadCloud className="h-10 w-10 text-teal-600" />
            {file ? (
              <>
                <p className="mt-3 font-medium text-navy-900">{file.name}</p>
                <p className="text-sm text-slate-500">{fmtBytes(file.size)} · click to change</p>
              </>
            ) : (
              <>
                <p className="mt-3 font-medium text-navy-900">Drag & drop a document, or click to browse</p>
                <p className="text-sm text-slate-500">PDF, JPG, JPEG or PNG · up to {maxMb} MB</p>
              </>
            )}
            <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
          </div>
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Title"><input className={inputCls} value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} placeholder="e.g. Blood report Nov 2026" /></Field>
              <Field label="Category">
                <select className={inputCls} value={meta.category} onChange={(e) => setMeta({ ...meta, category: e.target.value })}>
                  {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </Field>
              <Field label="Document date"><input type="date" className={inputCls} value={meta.document_date} onChange={(e) => setMeta({ ...meta, document_date: e.target.value })} /></Field>
              <Field label="Doctor"><input className={inputCls} value={meta.doctor_name} onChange={(e) => setMeta({ ...meta, doctor_name: e.target.value })} placeholder="Dr. …" /></Field>
              <Field label="Hospital / lab"><input className={inputCls} value={meta.hospital} onChange={(e) => setMeta({ ...meta, hospital: e.target.value })} /></Field>
              <Field label="Notes"><input className={inputCls} value={meta.notes} onChange={(e) => setMeta({ ...meta, notes: e.target.value })} /></Field>
            </div>
            {upErr && <ErrorBox message={upErr} />}
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="teal" onClick={upload} loading={uploading} disabled={!file}><Sparkles className="h-4 w-4" /> Upload & extract</Button>
              <p className="text-xs text-slate-500">Extracted values are shown for your review before anything is saved. Try the files in <code>sample-data/</code>.</p>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <div className="grid gap-2 border-b border-slate-100 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className={cx(inputCls, "pl-9")} placeholder="Search title, doctor, hospital…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className={inputCls} value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category filter">
            <option value="">All categories</option>
            {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input type="date" className={inputCls} value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From date" />
          <input type="date" className={inputCls} value={to} onChange={(e) => setTo(e.target.value)} aria-label="To date" />
        </div>
        {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div> :
          !data?.documents.length ? <Empty icon={<FolderLock className="h-5 w-5" />} title="No documents found">Upload your first document above.</Empty> : (
            <ul className="divide-y divide-slate-100">
              {data.documents.map((d) => {
                const st = EXT_STATUS[d.extraction_status];
                const Icon = d.content_type.startsWith("image") ? FileImage : FileText;
                return (
                  <li key={d.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-navy-50 text-navy-700"><Icon className="h-5 w-5" /></div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <button onClick={() => setViewDoc(d)} className="truncate text-left font-medium text-navy-900 hover:text-teal-700">{d.title}</button>
                        <Badge tone="teal">{CATEGORY_LABEL[d.category] ?? d.category}</Badge>
                        <Badge tone={st.tone}>{st.l}</Badge>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-slate-500">
                        {fmtDate(d.document_date)}{d.doctor_name ? ` · ${d.doctor_name}` : ""}{d.hospital ? ` · ${d.hospital}` : ""} · {fmtBytes(d.size_bytes)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      {d.extraction_status !== "confirmed" && <Button size="sm" variant={d.extraction_status === "pending_review" ? "teal" : "secondary"} onClick={() => openReview(d)}><Sparkles className="h-3.5 w-3.5" />{d.extraction_status === "pending_review" ? "Review" : "Extract"}</Button>}
                      <button onClick={() => setViewDoc(d)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-navy-800" title="Preview" aria-label={`Preview ${d.title}`}><Eye className="h-4 w-4" /></button>
                      <button onClick={() => download(d)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-navy-800" title="Download" aria-label={`Download ${d.title}`}><Download className="h-4 w-4" /></button>
                      <button onClick={() => setToDelete(d)} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-700" title="Delete" aria-label={`Delete ${d.title}`}><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        {data && <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">{data.count} document(s). Demo storage: files are kept in the backend&apos;s local uploads folder, never at a public URL.</p>}
      </Card>

      <ExtractionReview doc={review?.doc ?? null} extraction={review?.extraction ?? null} onClose={() => setReview(null)}
        onSaved={(msg) => { setReview(null); setToast(msg); reload(); }} />
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
      <Modal open={!!toDelete} onClose={() => setToDelete(null)} title="Delete document?"
        footer={<><Button variant="secondary" onClick={() => setToDelete(null)}>Cancel</Button><Button variant="danger" onClick={doDelete}><Trash2 className="h-4 w-4" /> Delete</Button></>}>
        <p className="text-sm text-slate-700">Delete <b>{toDelete?.title}</b> from your vault? The file is removed from demo storage. Values you already confirmed stay in your record with a note that the source was deleted.</p>
        <div className="mt-3"><Notice tone="warn">This cannot be undone (except by resetting the demo data).</Notice></div>
      </Modal>
    </div>
  );
}
