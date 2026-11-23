"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, FileText, Send, Sparkles, Trash2, User } from "lucide-react";
import { api, storage } from "@/lib/api";
import type { AIResult } from "@/lib/types";
import { Badge, Button, Card, DemoBadge } from "./ui";
import { FlagList } from "./FlagList";
import { DocumentViewer } from "./DocumentViewer";
import { cx, fmtDate } from "@/lib/format";

type Msg = { role: "user"; text: string } | { role: "assistant"; result: AIResult } | { role: "error"; text: string };

const PATIENT_PROMPTS = ["Summarise my history", "List my recorded medications", "Compare my last three reports",
  "Show my HbA1c trend", "List my previous doctors", "Summarise my latest consultation"];
const DOCTOR_PROMPTS = ["Summarise this patient's history", "Show medication changes", "Compare the last three lab reports",
  "Identify possible duplicate therapies for review", "Summarise consultations", "Show blood pressure trend"];

export function AnswerCard({ result, onCite }: { result: AIResult; onCite?: (id: string, label: string) => void }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {result.mode === "demo" ? <DemoBadge /> : <Badge tone="teal">{result.label}</Badge>}
      </div>
      {result.table ? (
        <>
          <p className="text-sm text-navy-900">{result.answer.split("\n")[0]}</p>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{result.table.columns.map((c) => <th key={c} className="px-3 py-2 font-medium">{c.includes("-") && c.length === 10 ? fmtDate(c) : c}</th>)}</tr></thead>
              <tbody>{result.table.rows.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">{r.map((c, j) => (
                  <td key={j} className={cx("px-3 py-2", j === 0 ? "text-slate-700" : "font-medium text-navy-900", /\((H|L)\)/.test(c) && "text-amber-700")}>{c}</td>
                ))}</tr>
              ))}</tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">(H)/(L) = above/below the reference range printed on that report.</p>
        </>
      ) : result.flags?.length ? (
        <>
          <p className="text-sm text-navy-900">{result.answer.split("\n")[0]}</p>
          <FlagList flags={result.flags} />
        </>
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-navy-900">{result.answer}</p>
      )}
      {!!result.citations.length && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate-500">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {result.citations.slice(0, 10).map((c) => (
              <button key={c.id} onClick={() => onCite?.(c.id, c.label)}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-teal-800 hover:border-teal-300">
                <FileText className="h-3 w-3" />{c.label}{c.date ? ` · ${fmtDate(c.date, { month: "short", year: "2-digit" })}` : ""}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="text-[11px] leading-relaxed text-slate-400">{result.disclaimer}</p>
    </div>
  );
}

export function AssistantView({ patientId, role, storageKey, canViewDocs = true }: { patientId?: string; role: "patient" | "doctor"; storageKey: string; canViewDocs?: boolean }) {
  const key = `mykshema.chat.${storageKey}`;
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [viewDoc, setViewDoc] = useState<{ id: string; title: string } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const prompts = role === "patient" ? PATIENT_PROMPTS : DOCTOR_PROMPTS;

  useEffect(() => { setMsgs(storage.getJSON<Msg[]>(key, [])); }, [key]);
  useEffect(() => { storage.setJSON(key, msgs.slice(-30)); endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, key]);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api<AIResult>("/api/ai/ask", { body: { question: q, patient_id: patientId } });
      setMsgs((m) => [...m, { role: "assistant", result: r }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "error", text: (e as Error).message }]);
    } finally { setBusy(false); }
  }

  return (
    <Card className="flex h-[calc(100vh-15rem)] min-h-[520px] flex-col">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-teal-50 text-teal-700"><Sparkles className="h-4 w-4" /></div>
          <div>
            <p className="text-sm font-semibold text-navy-900">MyKshema Health Assistant</p>
            <p className="text-xs text-slate-500">Answers only from {role === "patient" ? "your" : "this authorised patient's"} records</p>
          </div>
        </div>
        {msgs.length > 0 && <Button variant="ghost" size="sm" onClick={() => setMsgs([])}><Trash2 className="h-4 w-4" /> Clear</Button>}
      </div>
      <div className="scrollbar-thin flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {msgs.length === 0 && (
          <div className="mx-auto max-w-xl py-6 text-center">
            <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-navy-50 text-navy-700"><Bot className="h-6 w-6" /></div>
            <p className="font-medium text-navy-900">Ask about {role === "patient" ? "your" : "the patient's"} health record</p>
            <p className="mt-1 text-sm text-slate-500">Without an OpenAI key, answers are generated deterministically from the records and labelled DEMO MODE – NOT LIVE AI. Missing data is reported as missing — never invented.</p>
          </div>
        )}
        {msgs.map((m, i) => m.role === "user" ? (
          <div key={i} className="flex justify-end gap-2">
            <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-navy-800 px-4 py-2.5 text-sm text-white">{m.text}</div>
            <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-slate-200 text-slate-600"><User className="h-4 w-4" /></div>
          </div>
        ) : m.role === "assistant" ? (
          <div key={i} className="flex gap-2">
            <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-teal-100 text-teal-700"><Bot className="h-4 w-4" /></div>
            <div className="max-w-[92%] flex-1 rounded-2xl rounded-tl-md border border-slate-200 bg-slate-50/60 px-4 py-3">
              <AnswerCard result={m.result} onCite={canViewDocs ? (id, label) => id.startsWith("doc") && setViewDoc({ id, title: label }) : undefined} />
            </div>
          </div>
        ) : (
          <div key={i} className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-800">{m.text}</div>
        ))}
        {busy && <div className="flex gap-2 text-sm text-slate-500"><Bot className="h-4 w-4 animate-pulse text-teal-600" /> Reading the records…</div>}
        <div ref={endRef} />
      </div>
      <div className="border-t border-slate-100 p-3">
        <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1">
          {prompts.map((p) => (
            <button key={p} onClick={() => ask(p)} disabled={busy}
              className="whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-navy-700 hover:border-teal-300 hover:bg-teal-50 disabled:opacity-50">{p}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={500}
            placeholder={role === "patient" ? "Ask about your records…" : "Ask about this patient's records…"}
            className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100" />
          <Button type="submit" variant="teal" loading={busy} disabled={!input.trim()} aria-label="Send"><Send className="h-4 w-4" /></Button>
        </form>
      </div>
      <DocumentViewer docId={viewDoc?.id ?? null} title={viewDoc?.title} onClose={() => setViewDoc(null)} />
    </Card>
  );
}
