"use client";

import { AlertTriangle, Info, Loader2, X } from "lucide-react";
import { useEffect } from "react";
import { cx } from "@/lib/format";

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx("rounded-2xl border border-slate-200/80 bg-white shadow-card", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, icon, action }: { title: React.ReactNode; subtitle?: React.ReactNode; icon?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
      <div className="flex min-w-0 items-start gap-3">
        {icon && <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-700">{icon}</div>}
        <div className="min-w-0">
          <h3 className="font-semibold text-navy-900">{title}</h3>
          {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "teal";
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: "sm" | "md"; loading?: boolean }) {
  const v: Record<BtnVariant, string> = {
    primary: "bg-navy-800 text-white hover:bg-navy-700 shadow-sm",
    teal: "bg-teal-600 text-white hover:bg-teal-700 shadow-sm",
    secondary: "border border-slate-200 bg-white text-navy-800 hover:bg-slate-50",
    ghost: "text-navy-700 hover:bg-navy-50",
    danger: "border border-rose-200 bg-white text-rose-700 hover:bg-rose-50",
  };
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2.5 text-sm",
        v[variant], className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

type Tone = "slate" | "teal" | "navy" | "amber" | "rose" | "emerald" | "violet" | "sky";
export function Badge({ tone = "slate", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  const t: Record<Tone, string> = {
    slate: "bg-slate-100 text-slate-700 ring-slate-200",
    teal: "bg-teal-50 text-teal-800 ring-teal-200",
    navy: "bg-navy-50 text-navy-700 ring-navy-200",
    amber: "bg-amber-50 text-amber-800 ring-amber-200",
    rose: "bg-rose-50 text-rose-700 ring-rose-200",
    emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    violet: "bg-violet-50 text-violet-700 ring-violet-200",
    sky: "bg-sky-50 text-sky-700 ring-sky-200",
  };
  return <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", t[tone], className)}>{children}</span>;
}

export function DemoBadge({ label = "DEMO MODE – NOT LIVE AI" }: { label?: string }) {
  return <Badge tone="amber" className="font-semibold tracking-wide">{label}</Badge>;
}

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: string; subtitle?: React.ReactNode; actions?: React.ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin text-teal-600" /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && <button onClick={onRetry} className="font-medium underline">Retry</button>}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: React.ReactNode; tone?: "info" | "warn" }) {
  return (
    <div className={cx("flex items-start gap-2.5 rounded-xl border p-3 text-sm",
      tone === "warn" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-navy-100 bg-navy-50/60 text-navy-800")}>
      {tone === "warn" ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> : <Info className="mt-0.5 h-4 w-4 shrink-0" />}
      <div>{children}</div>
    </div>
  );
}

export function Empty({ icon, title, children }: { icon?: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      {icon && <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-500">{icon}</div>}
      <p className="font-medium text-navy-900">{title}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Stat({ label, value, sub, icon, tone = "teal" }: { label: string; value: React.ReactNode; sub?: React.ReactNode; icon?: React.ReactNode; tone?: "teal" | "navy" | "amber" | "rose" }) {
  const t = { teal: "bg-teal-50 text-teal-700", navy: "bg-navy-50 text-navy-700", amber: "bg-amber-50 text-amber-700", rose: "bg-rose-50 text-rose-700" }[tone];
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        {icon && <div className={cx("grid h-9 w-9 place-items-center rounded-xl", t)}>{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-navy-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </Card>
  );
}

export function Modal({ open, onClose, title, children, wide, footer }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; wide?: boolean; footer?: React.ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-950/40 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title}
        className={cx("flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-white shadow-lift sm:rounded-2xl", wide ? "sm:max-w-4xl" : "sm:max-w-lg")}
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-navy-900">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-navy-800">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export const inputCls = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-navy-900 placeholder:text-slate-400 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-100";

export function Tabs<T extends string>({ value, onChange, tabs }: { value: T; onChange: (v: T) => void; tabs: { value: T; label: string; count?: number }[] }) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
      {tabs.map((t) => (
        <button key={t.value} onClick={() => onChange(t.value)}
          className={cx("whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition",
            value === t.value ? "bg-white text-navy-900 shadow-sm" : "text-slate-600 hover:text-navy-800")}>
          {t.label}{t.count !== undefined && <span className="ml-1.5 text-xs text-slate-400">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

