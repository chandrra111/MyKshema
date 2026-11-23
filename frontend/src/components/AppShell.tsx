"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { FlaskConical, LogOut, Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { cx, initials } from "@/lib/format";

export interface NavItem { href: string; label: string; icon: React.ComponentType<{ className?: string }>; exact?: boolean }

export function AppShell({ nav, children, portal }: { nav: NavItem[]; children: React.ReactNode; portal: "Patient" | "Doctor" }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [aiLive, setAiLive] = useState<boolean | null>(null);

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    api<{ live_ai: boolean }>("/api/ai/status").then((s) => setAiLive(s.live_ai)).catch(() => setAiLive(null));
  }, []);

  const isActive = (n: NavItem) => (n.exact ? pathname === n.href : pathname === n.href || pathname.startsWith(n.href + "/"));

  const sidebar = (
    <div className="flex h-full flex-col bg-navy-900 text-navy-100">
      <div className="flex items-center justify-between px-5 py-5">
        <Link href={nav[0].href}><Logo light /></Link>
        <button className="rounded-lg p-1 text-navy-200 hover:bg-navy-800 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
      </div>
      <p className="px-5 pb-2 text-[11px] font-semibold uppercase tracking-wider text-navy-300">{portal} portal</p>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
        {nav.map((n, i) => {
          const Icon = n.icon;
          const active = isActive(n);
          return (
            <Link key={n.href} href={n.href}
              className={cx("group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                active ? "bg-teal-500/15 font-medium text-white" : "text-navy-200 hover:bg-navy-800 hover:text-white")}>
              <Icon className={cx("h-[18px] w-[18px]", active ? "text-teal-300" : "text-navy-300 group-hover:text-teal-300")} />
              <span className="flex-1">{n.label}</span>
              {portal === "Patient" && <span className="text-[10px] text-navy-400">{i + 1}</span>}
            </Link>
          );
        })}
      </nav>
      <div className="m-3 rounded-xl bg-navy-800/70 p-3 text-xs text-navy-200">
        <div className="mb-1 flex items-center gap-1.5 font-semibold text-amber-300"><FlaskConical className="h-3.5 w-3.5" /> Hackathon prototype</div>
        Synthetic data only. Not a medical device or a substitute for professional medical advice.
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-navy-950/50" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 shadow-lift">{sidebar}</div>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/85 backdrop-blur">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
            <button className="rounded-lg p-1.5 text-navy-700 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
            <div className="hidden text-sm text-slate-500 md:block">AI-Powered Personal Health Intelligence</div>
            <div className="ml-auto flex items-center gap-2 sm:gap-3">
              {aiLive === false && <span className="hidden rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-800 ring-1 ring-amber-200 sm:inline">AI: DEMO MODE – NOT LIVE AI</span>}
              {aiLive === true && <span className="hidden rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-800 ring-1 ring-teal-200 sm:inline">Live AI enabled</span>}
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">Synthetic data</span>
              {user && (
                <div className="flex items-center gap-2">
                  <div className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-teal-700 text-xs font-semibold text-white">{initials(user.display_name)}</div>
                  <div className="hidden leading-tight sm:block">
                    <p className="text-sm font-medium text-navy-900">{user.display_name}</p>
                    <p className="text-[11px] capitalize text-slate-500">{user.role} · demo</p>
                  </div>
                </div>
              )}
              <button onClick={logout} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-navy-800" title="Sign out" aria-label="Sign out"><LogOut className="h-4 w-4" /></button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
