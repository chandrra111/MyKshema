"use client";

import { useEffect, useState } from "react";
import { Database, RotateCcw } from "lucide-react";
import { api, API_URL, storage } from "@/lib/api";
import { Badge, Button, Card, CardHeader, Modal, Notice } from "./ui";

interface Health { storage: string; database: string; live_ai: boolean; ai_mode: string }

/** Shows how the demo is running and offers a demo-data reset. */
export function DemoSystemCard() {
  const [h, setH] = useState<Health | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => { api<Health>("/health").then(setH).catch(() => setH(null)); }, []);

  async function reset() {
    setBusy(true);
    try {
      await api("/api/demo/reset", { method: "POST" });
      Object.keys(window.localStorage).filter((k) => k.startsWith("mykshema.chat.")).forEach((k) => storage.remove(k));
      setMsg("Demo data restored. Reloading…");
      setTimeout(() => window.location.reload(), 800);
    } catch (e) { setMsg((e as Error).message); setBusy(false); }
  }

  return (
    <Card className="lg:col-span-2">
      <CardHeader icon={<Database className="h-4 w-4" />} title="Demo system" subtitle="How this prototype is running" />
      <div className="grid gap-4 p-5 sm:grid-cols-4">
        <div><p className="text-xs text-slate-500">API</p><p className="truncate text-sm font-medium text-navy-900">{API_URL}</p></div>
        <div><p className="text-xs text-slate-500">Storage</p><p className="text-sm font-medium text-navy-900">{h?.storage ?? "—"}</p><p className="text-xs text-slate-500">Database: {h?.database ?? "—"}</p></div>
        <div><p className="text-xs text-slate-500">AI</p>{h ? (h.live_ai ? <Badge tone="teal">Live AI</Badge> : <Badge tone="amber">DEMO MODE – NOT LIVE AI</Badge>) : "—"}</div>
        <div className="flex items-start sm:justify-end"><Button variant="danger" size="sm" onClick={() => setConfirm(true)}><RotateCcw className="h-4 w-4" /> Reset demo data</Button></div>
      </div>
      <div className="px-5 pb-5"><Notice>Local JSON files and browser storage are for hackathon demonstration only — not secure or scalable enough for real patient data. Session token and assistant chat history are kept in this browser&apos;s localStorage.</Notice></div>
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Reset all demo data?"
        footer={<><Button variant="secondary" onClick={() => setConfirm(false)}>Cancel</Button><Button variant="danger" loading={busy} onClick={reset}>Reset</Button></>}>
        <p className="text-sm text-slate-700">This restores the original synthetic dataset for <b>every</b> demo account: uploads, confirmed extractions, consent changes and consultations made during the demo are removed.</p>
        {msg && <p className="mt-3 text-sm text-slate-600">{msg}</p>}
      </Modal>
    </Card>
  );
}
