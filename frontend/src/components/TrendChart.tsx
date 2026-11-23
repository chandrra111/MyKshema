"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Trend } from "@/lib/types";
import { fmtDate } from "@/lib/format";

const TEAL = "#12AB98";
const NAVY = "#1E3F72";

/** Line chart for one or two series. Reference band only when a range is documented. */
export function TrendChart({ series, height = 260 }: { series: Trend[]; height?: number }) {
  const map = new Map<string, Record<string, number | string>>();
  series.forEach((s) => s.points.forEach((p) => {
    const row = map.get(p.date) ?? { date: p.date };
    row[s.code] = p.value;
    map.set(p.date, row);
  }));
  const data = Array.from(map.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const primary = series[0];
  const ref = primary?.reference;
  const values = series.flatMap((s) => s.points.map((p) => p.value));
  const lo = Math.min(...values, ref?.low ?? Infinity);
  const hi = Math.max(...values, ref?.high ?? -Infinity);
  const pad = (hi - lo) * 0.15 || 1;
  const domain: [number, number] = [Math.max(0, Math.floor(lo - pad)), Math.ceil(hi + pad)];

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="date" tickFormatter={(d) => fmtDate(d, { month: "short", year: "2-digit" })} minTickGap={24} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis domain={domain} tickLine={false} axisLine={false} width={48} />
          {series.length === 1 && ref && (ref.low != null || ref.high != null) && (
            <ReferenceArea y1={ref.low ?? domain[0]} y2={ref.high ?? domain[1]} fill={TEAL} fillOpacity={0.07} stroke="none" ifOverflow="hidden" />
          )}
          {series.length > 1 && series.map((s, i) => s.reference?.high != null && (
            <ReferenceLine key={s.code} y={s.reference.high} stroke={i === 0 ? TEAL : NAVY} strokeDasharray="4 4" strokeOpacity={0.6} />
          ))}
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
            labelFormatter={(d) => fmtDate(String(d))}
            formatter={(v: number, k: string) => {
              const s = series.find((x) => x.code === k);
              return [`${v} ${s?.unit ?? ""}`, s?.name ?? k];
            }} />
          {series.length > 1 && <Legend formatter={(k) => series.find((s) => s.code === k)?.name ?? k} wrapperStyle={{ fontSize: 12 }} />}
          {series.map((s, i) => (
            <Line key={s.code} type="monotone" dataKey={s.code} stroke={i === 0 ? TEAL : NAVY} strokeWidth={2.25}
              dot={{ r: 3, strokeWidth: 0, fill: i === 0 ? TEAL : NAVY }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Sparkline({ trend, height = 44 }: { trend: Trend; height?: number }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={trend.points} margin={{ top: 4, right: 2, bottom: 4, left: 2 }}>
          <YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
          <Line type="monotone" dataKey="value" stroke={TEAL} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
