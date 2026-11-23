"use client";

import { useMemo, useState } from "react";
import { Activity, ArrowDownRight, ArrowUpRight, BellRing, CalendarClock, Minus, Plus } from "lucide-react";
import { api, qs } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Reminder, Trend } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Field, inputCls, Modal, Notice, Spinner } from "./ui";
import { Sparkline, TrendChart } from "./TrendChart";
import { cx, fmtDate } from "@/lib/format";

const STATUS: Record<string, { label: string; tone: "rose" | "amber" | "emerald" | "slate" }> = {
  above_range: { label: "Above documented range", tone: "amber" },
  below_range: { label: "Below documented range", tone: "amber" },
  within_range: { label: "Within documented range", tone: "emerald" },
  no_documented_range: { label: "No documented range", tone: "slate" },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.no_documented_range;
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

function Delta({ t }: { t: Trend }) {
  if (t.change == null) return <span className="text-xs text-slate-400">single value</span>;
  const Icon = t.change > 0 ? ArrowUpRight : t.change < 0 ? ArrowDownRight : Minus;
  return <span className="inline-flex items-center gap-0.5 text-xs text-slate-600"><Icon className="h-3.5 w-3.5" />{t.change > 0 ? "+" : ""}{t.change} {t.unit} vs {fmtDate(t.previous!.date, { month: "short", year: "2-digit" })}</span>;
}

export function AnalyticsView({ patientId, canLog }: { patientId?: string; canLog?: boolean }) {
  const q = qs({ patient_id: patientId });
  const { data, error, loading, reload } = useApi<{ trends: Trend[]; note: string }>(`/api/analytics/health-trends${q}`);
  const rem = useApi<{ reminders: Reminder[]; note: string }>(`/api/analytics/reminders${q}`);
  const [selected, setSelected] = useState("hba1c");
  const [logOpen, setLogOpen] = useState(false);
  const [log, setLog] = useState({ code: "bp_systolic", value: "", value2: "", observed_on: new Date().toISOString().slice(0, 10) });
  const [saving, setSaving] = useState(false);
  const [logErr, setLogErr] = useState<string | null>(null);

  const trends = data?.trends ?? [];
  const byCode = useMemo(() => Object.fromEntries(trends.map((t) => [t.code, t])), [trends]);
  const sel = selected === "bp" ? [byCode.bp_systolic, byCode.bp_diastolic].filter(Boolean) : [byCode[selected]].filter(Boolean);
  const cards = trends.filter((t) => t.code !== "bp_diastolic");

  async function saveLog() {
    setSaving(true); setLogErr(null);
    try {
      if (log.code === "bp") {
        await api("/api/analytics/observations", { body: { code: "bp_systolic", value: Number(log.value), observed_on: log.observed_on } });
        await api("/api/analytics/observations", { body: { code: "bp_diastolic", value: Number(log.value2), observed_on: log.observed_on } });
      } else {
        await api("/api/analytics/observations", { body: { code: log.code, value: Number(log.value), observed_on: log.observed_on } });
      }
      setLogOpen(false); setLog({ ...log, value: "", value2: "" }); reload(); rem.reload();
    } catch (e) { setLogErr((e as Error).message); } finally { setSaving(false); }
  }

  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!trends.length) return <Card><Empty icon={<Activity className="h-5 w-5" />} title="No measurements recorded yet">Upload a lab report or log a home measurement.</Empty></Card>;

  const main = sel[0];
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {cards.slice(0, 10).map((t) => {
          const code = t.code === "bp_systolic" ? "bp" : t.code;
          const dia = t.code === "bp_systolic" ? byCode.bp_diastolic : null;
          return (
            <button key={t.code} onClick={() => setSelected(code)}
              className={cx("rounded-2xl border bg-white p-4 text-left shadow-card transition hover:border-teal-300",
                selected === code ? "border-teal-400 ring-2 ring-teal-100" : "border-slate-200/80")}>
              <p className="truncate text-xs text-slate-500">{t.code === "bp_systolic" ? "Blood pressure" : t.name}</p>
              <p className="mt-1 text-xl font-semibold text-navy-900">
                {t.latest.value}{dia ? `/${dia.latest.value}` : ""} <span className="text-xs font-normal text-slate-500">{t.unit}</span>
              </p>
              <Sparkline trend={t} />
              <Delta t={t} />
            </button>
          );
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader icon={<Activity className="h-4 w-4" />}
            title={selected === "bp" ? "Blood pressure" : main?.name}
            subtitle={main ? `${main.points.length} recorded values · ${main.panel ?? ""}` : undefined}
            action={canLog && <Button size="sm" variant="secondary" onClick={() => setLogOpen(true)}><Plus className="h-4 w-4" /> Log measurement</Button>} />
          {main ? (
            <div className="p-5">
              <TrendChart series={sel as Trend[]} height={300} />
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Latest</p>
                  <p className="font-semibold text-navy-900">{sel.map((s) => s!.latest.value).join("/")} {main.unit}</p>
                  <p className="text-xs text-slate-500">{fmtDate(main.latest.date)}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Documented reference</p>
                  <p className="text-sm font-medium text-navy-900">{main.reference?.text ?? "Not documented"}</p>
                  <div className="mt-1"><StatusBadge status={main.latest.status} /></div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Descriptive trend (per 3 months)</p>
                  {main.trend ? (
                    <>
                      <p className="font-semibold text-navy-900">{main.trend.per_month * 3 > 0 ? "+" : ""}{(main.trend.per_month * 3).toFixed(2)} {main.unit}</p>
                      <p className="text-xs text-slate-500">95% CI {(main.trend.ci95_low * 3).toFixed(2)} to {(main.trend.ci95_high * 3).toFixed(2)} · n={main.trend.n_points}</p>
                    </>
                  ) : <p className="text-sm text-slate-500">Needs ≥ 5 values</p>}
                </div>
              </div>
              <div className="mt-4"><Notice>{data?.note} No disease predictions are made.</Notice></div>
              <details className="mt-4 rounded-xl border border-slate-200">
                <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-navy-800">Date comparison table</summary>
                <div className="max-h-72 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-left text-xs text-slate-500"><tr><th className="px-4 py-2">Date</th>{sel.map((s) => <th key={s!.code} className="px-4 py-2">{s!.name}</th>)}<th className="px-4 py-2">Source</th></tr></thead>
                    <tbody>
                      {[...main.points].reverse().map((p, i) => (
                        <tr key={p.date + i} className="border-t border-slate-100">
                          <td className="px-4 py-2 text-slate-600">{fmtDate(p.date)}</td>
                          {sel.map((s) => { const pt = s!.points.find((x) => x.date === p.date); return <td key={s!.code} className="px-4 py-2 font-medium text-navy-900">{pt ? `${pt.value} ${s!.unit}` : "—"}{pt && pt.status !== "within_range" && pt.status !== "no_documented_range" && <span className="ml-1 text-xs text-amber-700">●</span>}</td>; })}
                          <td className="px-4 py-2 text-xs text-slate-500">{p.source_label}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </div>
          ) : <Empty title="Select a measure" />}
        </Card>

        <Card>
          <CardHeader icon={<BellRing className="h-4 w-4" />} title="Reminders & preventive care" subtitle="Based only on recorded data" />
          <ul className="divide-y divide-slate-100">
            {(rem.data?.reminders ?? []).map((r, i) => (
              <li key={i} className="flex gap-3 px-5 py-3">
                <CalendarClock className={cx("mt-0.5 h-4 w-4 shrink-0", r.priority === "high" ? "text-teal-600" : r.priority === "medium" ? "text-amber-600" : "text-slate-400")} />
                <div>
                  <p className="text-sm font-medium text-navy-900">{r.title}</p>
                  <p className="text-xs text-slate-600">{r.detail}</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">{r.kind === "follow_up" ? `Due ${fmtDate(r.due)} · ` : ""}{r.basis}</p>
                </div>
              </li>
            ))}
            {rem.data && !rem.data.reminders.length && <li className="px-5 py-6 text-sm text-slate-500">Nothing due.</li>}
          </ul>
          <p className="px-5 pb-4 text-xs text-slate-400">{rem.data?.note}</p>
        </Card>
      </div>

      <Modal open={logOpen} onClose={() => setLogOpen(false)} title="Log a home measurement"
        footer={<><Button variant="secondary" onClick={() => setLogOpen(false)}>Cancel</Button><Button onClick={saveLog} loading={saving} disabled={!log.value || (log.code === "bp" && !log.value2)}>Save</Button></>}>
        <div className="space-y-3">
          <Field label="Measurement">
            <select className={inputCls} value={log.code} onChange={(e) => setLog({ ...log, code: e.target.value })}>
              <option value="bp">Blood pressure (mmHg)</option>
              <option value="heart_rate">Resting heart rate (bpm)</option>
              <option value="weight">Weight (kg)</option>
              <option value="fasting_glucose_home">Home fasting glucose (mg/dL)</option>
            </select>
          </Field>
          {log.code === "bp" ? (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Systolic"><input type="number" className={inputCls} value={log.value} onChange={(e) => setLog({ ...log, value: e.target.value })} /></Field>
              <Field label="Diastolic"><input type="number" className={inputCls} value={log.value2} onChange={(e) => setLog({ ...log, value2: e.target.value })} /></Field>
            </div>
          ) : <Field label="Value"><input type="number" step="0.1" className={inputCls} value={log.value} onChange={(e) => setLog({ ...log, value: e.target.value })} /></Field>}
          <Field label="Date"><input type="date" className={inputCls} value={log.observed_on} onChange={(e) => setLog({ ...log, observed_on: e.target.value })} /></Field>
          {logErr && <ErrorBox message={logErr} />}
        </div>
      </Modal>
    </div>
  );
}
