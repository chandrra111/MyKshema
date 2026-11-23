import { AlertOctagon, AlertTriangle, Info, ShieldAlert } from "lucide-react";
import type { Flag } from "@/lib/types";
import { Badge } from "./ui";
import { cx } from "@/lib/format";

const SEV = {
  high: { tone: "rose" as const, icon: AlertOctagon, ring: "border-rose-200 bg-rose-50/60" },
  moderate: { tone: "amber" as const, icon: AlertTriangle, ring: "border-amber-200 bg-amber-50/50" },
  low: { tone: "sky" as const, icon: ShieldAlert, ring: "border-sky-200 bg-sky-50/50" },
  info: { tone: "slate" as const, icon: Info, ring: "border-slate-200 bg-slate-50" },
};

const TYPE_LABEL: Record<string, string> = {
  duplicate: "Duplicate", duplicate_class: "Duplicate therapy", interaction: "Interaction", allergy_conflict: "Allergy",
  missing_details: "Missing details", unverified: "Unverified",
};

export function FlagList({ flags, compact }: { flags: Flag[]; compact?: boolean }) {
  if (!flags.length) return <p className="text-sm text-slate-500">No flags raised from the recorded data.</p>;
  return (
    <ul className="space-y-2">
      {flags.map((f) => {
        const s = SEV[f.severity] ?? SEV.info;
        const Icon = s.icon;
        return (
          <li key={f.id} className={cx("rounded-xl border p-3", s.ring)}>
            <div className="flex items-start gap-2.5">
              <Icon className={cx("mt-0.5 h-4 w-4 shrink-0", { rose: "text-rose-600", amber: "text-amber-600", sky: "text-sky-600", slate: "text-slate-500" }[s.tone])} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <p className="text-sm font-medium text-navy-900">{f.title}</p>
                  <Badge tone={s.tone}>{f.severity}</Badge>
                  <Badge tone="slate">{TYPE_LABEL[f.type] ?? f.type}</Badge>
                </div>
                {!compact && <p className="mt-1 text-sm text-slate-600">{f.detail}</p>}
                {!compact && <p className="mt-1 text-xs text-slate-500">Basis: {f.evidence}</p>}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
