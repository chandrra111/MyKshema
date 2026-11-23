"use client";

import { useState } from "react";
import { Ban, Check, Clock, History, Search, Share2, ShieldCheck, Stethoscope, X } from "lucide-react";
import { api, qs } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { ALL_SCOPES, SCOPE_LABEL, type AccessRequest, type AuditLog, type DoctorProfile, type Grant, type Scope } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Field, inputCls, Modal, Notice, PageHeader, Spinner, Tabs } from "@/components/ui";
import { cx, fmtDateTime, initials, relTime } from "@/lib/format";

const DURATIONS = [
  { h: 2, l: "2 hours" }, { h: 24, l: "24 hours" }, { h: 72, l: "3 days" }, { h: 168, l: "7 days" }, { h: 720, l: "30 days" },
];

function ScopePicker({ value, onChange }: { value: Scope[]; onChange: (s: Scope[]) => void }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {ALL_SCOPES.map((s) => {
        const on = value.includes(s);
        return (
          <label key={s} className={cx("flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition",
            on ? "border-teal-300 bg-teal-50 text-teal-900" : "border-slate-200 text-slate-600 hover:border-slate-300")}>
            <input type="checkbox" className="h-4 w-4 accent-teal-600" checked={on} onChange={() => onChange(on ? value.filter((x) => x !== s) : [...value, s])} />
            {SCOPE_LABEL[s]}
          </label>
        );
      })}
    </div>
  );
}

const ACTION_LABEL: Record<string, string> = {
  "access.granted": "Shared records", "access.request_approved": "Approved request", "access.request_denied": "Denied request",
  "access.revoked": "Revoked access", "access.requested": "Access requested", "access.denied": "Access blocked",
  "patient.history_viewed": "Viewed history", "document.viewed": "Viewed document", "document.downloaded": "Downloaded document",
  "document.uploaded": "Uploaded document", "document.deleted": "Deleted document", "extraction.confirmed": "Confirmed extraction",
  "consultation.created": "Added consultation", "auth.login": "Signed in", "patient.lookup": "Looked you up",
};

export default function DoctorConnectPage() {
  const [tab, setTab] = useState<"sharing" | "directory" | "log">("sharing");
  const [q, setQ] = useState("");
  const reqs = useApi<{ requests: AccessRequest[]; note: string }>("/api/access-requests");
  const grants = useApi<{ grants: Grant[] }>("/api/access-grants");
  const dir = useApi<{ doctors: DoctorProfile[]; note: string }>(`/api/doctors${qs({ q })}`);
  const logs = useApi<{ logs: AuditLog[] }>("/api/audit-logs?limit=150");
  const [approve, setApprove] = useState<{ req: AccessRequest; scopes: Scope[]; hours: number } | null>(null);
  const [share, setShare] = useState<{ doc: DoctorProfile; scopes: Scope[]; hours: number } | null>(null);
  const [revoke, setRevoke] = useState<Grant | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const pending = (reqs.data?.requests ?? []).filter((r) => r.status === "pending");
  const active = (grants.data?.grants ?? []).filter((g) => g.state === "active");
  const past = (grants.data?.grants ?? []).filter((g) => g.state !== "active");
  const reloadAll = () => { reqs.reload(); grants.reload(); dir.reload(); logs.reload(); };

  async function run(fn: () => Promise<unknown>, close: () => void) {
    setBusy(true); setErr(null);
    try { await fn(); close(); reloadAll(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Doctor Connect" title="Share your records, on your terms"
        subtitle="Approve requests, choose exactly what each doctor can see and for how long, and revoke access at any time." />
      <Notice tone="warn"><b>Prototype simulation.</b> {reqs.data?.note ?? "Not production identity verification or legally validated consent."} Doctors are fictional.</Notice>

      <Tabs value={tab} onChange={setTab} tabs={[
        { value: "sharing", label: "Requests & access", count: pending.length + active.length },
        { value: "directory", label: "Doctor directory" },
        { value: "log", label: "Access history" },
      ]} />

      {tab === "sharing" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader icon={<Clock className="h-4 w-4" />} title="Pending requests" subtitle="Doctors asking to see your records" />
            {reqs.loading && !reqs.data ? <Spinner /> : pending.length === 0 ? <Empty title="No pending requests" /> : (
              <ul className="divide-y divide-slate-100">
                {pending.map((r) => (
                  <li key={r.id} className="p-5">
                    <div className="flex items-start gap-3">
                      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-navy-100 text-sm font-semibold text-navy-700">{initials(r.doctor?.full_name ?? "Dr")}</div>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-navy-900">{r.doctor?.full_name}</p>
                        <p className="text-xs text-slate-500">{r.doctor?.specialty} · {r.doctor?.hospital} · requested {relTime(r.created_at)}</p>
                        {r.reason && <p className="mt-1 text-sm text-slate-600">“{r.reason}”</p>}
                        <div className="mt-2 flex flex-wrap gap-1">{r.requested_scopes.map((s) => <Badge key={s} tone="navy">{SCOPE_LABEL[s]}</Badge>)}</div>
                        <p className="mt-1 text-xs text-slate-500">For {DURATIONS.find((d) => d.h === r.duration_hours)?.l ?? `${r.duration_hours} hours`}</p>
                        <div className="mt-3 flex gap-2">
                          <Button size="sm" variant="teal" onClick={() => setApprove({ req: r, scopes: r.requested_scopes, hours: r.duration_hours })}><Check className="h-4 w-4" /> Review & approve</Button>
                          <Button size="sm" variant="danger" onClick={() => run(() => api(`/api/access-requests/${r.id}/deny`, { method: "POST" }), () => {})}><X className="h-4 w-4" /> Deny</Button>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader icon={<ShieldCheck className="h-4 w-4" />} title="Doctors with access" subtitle="Active, time-limited grants"
              action={<Button size="sm" variant="secondary" onClick={() => setTab("directory")}><Share2 className="h-4 w-4" /> Share</Button>} />
            {active.length === 0 ? <Empty title="No one has access right now" /> : (
              <ul className="divide-y divide-slate-100">
                {active.map((g) => (
                  <li key={g.id} className="flex items-start gap-3 p-5">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-teal-100 text-sm font-semibold text-teal-800">{initials(g.doctor?.full_name ?? "Dr")}</div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-navy-900">{g.doctor?.full_name}</p>
                      <p className="text-xs text-slate-500">{g.doctor?.specialty} · expires {relTime(g.expires_at)} ({fmtDateTime(g.expires_at)})</p>
                      <div className="mt-2 flex flex-wrap gap-1">{g.scopes.map((s) => <Badge key={s} tone="teal">{SCOPE_LABEL[s]}</Badge>)}</div>
                    </div>
                    <Button size="sm" variant="danger" onClick={() => setRevoke(g)}><Ban className="h-4 w-4" /> Revoke</Button>
                  </li>
                ))}
              </ul>
            )}
            {past.length > 0 && (
              <details className="border-t border-slate-100">
                <summary className="cursor-pointer px-5 py-3 text-sm text-slate-600">Past grants ({past.length})</summary>
                <ul className="divide-y divide-slate-50 px-5 pb-3">
                  {past.map((g) => (
                    <li key={g.id} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-navy-800">{g.doctor?.full_name}</span>
                      <span className="flex items-center gap-2 text-xs text-slate-500"><Badge tone={g.state === "revoked" ? "rose" : "slate"}>{g.state}</Badge>{fmtDateTime(g.revoked_at || g.expires_at)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </Card>
        </div>
      )}

      {tab === "directory" && (
        <Card>
          <div className="border-b border-slate-100 p-4">
            <div className="relative max-w-md">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input className={cx(inputCls, "pl-9")} placeholder="Search name, specialty, hospital, city" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
          </div>
          {dir.loading && !dir.data ? <Spinner /> : (
            <div className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
              {(dir.data?.doctors ?? []).map((d) => (
                <div key={d.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-start gap-3">
                    <div className="grid h-11 w-11 place-items-center rounded-full bg-navy-100 font-semibold text-navy-700">{initials(d.full_name)}</div>
                    <div className="min-w-0">
                      <p className="font-medium text-navy-900">{d.full_name}</p>
                      <p className="text-sm text-teal-700">{d.specialty}</p>
                      <p className="text-xs text-slate-500">{d.hospital} · {d.city}</p>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{d.bio}</p>
                  <p className="mt-1 text-[11px] text-slate-400">Reg. {d.registration_no} (fictional) · {d.years_experience} yrs</p>
                  <div className="mt-3 flex items-center justify-between">
                    {d.active_grant ? <Badge tone="teal">Has access · expires {relTime(d.active_grant.expires_at)}</Badge> : <span />}
                    <Button size="sm" variant={d.active_grant ? "secondary" : "primary"} onClick={() => setShare({ doc: d, scopes: d.active_grant?.scopes ?? ["history", "medications", "allergies"], hours: 72 })}>
                      <Share2 className="h-4 w-4" /> {d.active_grant ? "Change" : "Share"}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "log" && (
        <Card>
          <CardHeader icon={<History className="h-4 w-4" />} title="Access & change history" subtitle="Every view, share, revoke and blocked attempt on your record (demo audit log)" />
          {logs.loading && !logs.data ? <Spinner /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr><th className="px-5 py-2">When</th><th className="px-5 py-2">Who</th><th className="px-5 py-2">Action</th><th className="px-5 py-2">Detail</th></tr></thead>
                <tbody>
                  {(logs.data?.logs ?? []).map((l) => (
                    <tr key={l.id} className="border-t border-slate-100">
                      <td className="whitespace-nowrap px-5 py-2 text-xs text-slate-500">{fmtDateTime(l.timestamp)}</td>
                      <td className="whitespace-nowrap px-5 py-2"><span className="text-navy-900">{l.actor_name ?? "system"}</span> <span className="text-xs capitalize text-slate-400">{l.actor_role}</span></td>
                      <td className="whitespace-nowrap px-5 py-2"><Badge tone={l.outcome === "denied" ? "rose" : l.action.startsWith("access") ? "teal" : "slate"}>{ACTION_LABEL[l.action] ?? l.action}</Badge></td>
                      <td className="px-5 py-2 text-xs text-slate-600">{l.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <Modal open={!!approve} onClose={() => setApprove(null)} title={`Approve ${approve?.req.doctor?.full_name ?? ""}`}
        footer={<><Button variant="secondary" onClick={() => setApprove(null)}>Cancel</Button>
          <Button variant="teal" loading={busy} disabled={!approve?.scopes.length}
            onClick={() => approve && run(() => api(`/api/access-requests/${approve.req.id}/approve`, { body: { scopes: approve.scopes, duration_hours: approve.hours } }), () => setApprove(null))}>
            <Check className="h-4 w-4" /> Approve access</Button></>}>
        {approve && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">You can narrow what is shared. Untick anything you don&apos;t want this doctor to see.</p>
            <ScopePicker value={approve.scopes} onChange={(s) => setApprove({ ...approve, scopes: s })} />
            <Field label="Access duration">
              <select className={inputCls} value={approve.hours} onChange={(e) => setApprove({ ...approve, hours: Number(e.target.value) })}>
                {DURATIONS.map((d) => <option key={d.h} value={d.h}>{d.l}</option>)}
              </select>
            </Field>
            {err && <ErrorBox message={err} />}
          </div>
        )}
      </Modal>

      <Modal open={!!share} onClose={() => setShare(null)} title={`Share with ${share?.doc.full_name ?? ""}`}
        footer={<><Button variant="secondary" onClick={() => setShare(null)}>Cancel</Button>
          <Button variant="teal" loading={busy} disabled={!share?.scopes.length}
            onClick={() => share && run(() => api("/api/access-grants", { body: { doctor_id: share.doc.id, scopes: share.scopes, duration_hours: share.hours } }), () => { setShare(null); setTab("sharing"); })}>
            <Share2 className="h-4 w-4" /> Share records</Button></>}>
        {share && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3"><Stethoscope className="h-5 w-5 text-teal-700" /><div className="text-sm"><p className="font-medium text-navy-900">{share.doc.full_name}</p><p className="text-slate-500">{share.doc.specialty} · {share.doc.hospital}</p></div></div>
            {!share.doc.has_portal_login && <Notice>This directory-only demo doctor has no portal login, so the grant is recorded but no one will view it.</Notice>}
            <ScopePicker value={share.scopes} onChange={(s) => setShare({ ...share, scopes: s })} />
            <Field label="Access duration">
              <select className={inputCls} value={share.hours} onChange={(e) => setShare({ ...share, hours: Number(e.target.value) })}>
                {DURATIONS.map((d) => <option key={d.h} value={d.h}>{d.l}</option>)}
              </select>
            </Field>
            {share.doc.active_grant && <Notice>Sharing again replaces the doctor&apos;s current access.</Notice>}
            {err && <ErrorBox message={err} />}
          </div>
        )}
      </Modal>

      <Modal open={!!revoke} onClose={() => setRevoke(null)} title="Revoke access?"
        footer={<><Button variant="secondary" onClick={() => setRevoke(null)}>Cancel</Button>
          <Button variant="danger" loading={busy} onClick={() => revoke && run(() => api(`/api/access-grants/${revoke.id}/revoke`, { method: "POST" }), () => setRevoke(null))}><Ban className="h-4 w-4" /> Revoke now</Button></>}>
        <p className="text-sm text-slate-700"><b>{revoke?.doctor?.full_name}</b> will immediately lose access to your records in MyKshema. Information they already saw cannot be un-seen.</p>
        {err && <div className="mt-3"><ErrorBox message={err} /></div>}
      </Modal>
    </div>
  );
}
