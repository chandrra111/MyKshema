"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, FileText, Lock, ShieldCheck, Sparkles, Stethoscope, User } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button, ErrorBox, Field, inputCls, Notice } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const DEMO = [
  { email: "ananya.rao@demo.mykshema.test", role: "Patient", name: "Ananya Rao", note: "2 years of synthetic history", icon: User },
  { email: "meera.iyer@demo.mykshema.test", role: "Doctor", name: "Dr. Meera Iyer", note: "Endocrinology · has consent", icon: Stethoscope },
  { email: "arjun.shah@demo.mykshema.test", role: "Doctor", name: "Dr. Arjun Shah", note: "Cardiology · request pending", icon: Stethoscope },
  { email: "rahul.menon@demo.mykshema.test", role: "Patient", name: "Rahul Menon", note: "Second patient", icon: User },
];
const PASSWORD = "Demo@2036";

function LoginInner() {
  const { login, user, ready } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(DEMO[0].email);
  const [password, setPassword] = useState(PASSWORD);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (ready && user) router.replace(user.role === "doctor" ? "/doctor" : "/patient");
  }, [ready, user, router]);

  async function go(e?: React.FormEvent, em = email, pw = password) {
    e?.preventDefault();
    setError(null);
    setBusy(em);
    try {
      const u = await login(em, pw);
      router.push(u.role === "doctor" ? "/doctor" : "/patient");
    } catch (err) {
      setError((err as Error).message);
      setBusy(null);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-navy-900 p-12 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-teal-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-10 h-96 w-96 rounded-full bg-navy-500/30 blur-3xl" />
        <Logo light tagline />
        <div className="relative mt-auto max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-wider text-teal-300">AI-Powered Personal Health Intelligence</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight tracking-tight">
            One lifelong, connected health record — shared only with the doctors you choose.
          </h1>
          <p className="mt-4 text-navy-200">
            Upload prescriptions, lab reports and scans. MyKshema turns them into a structured timeline, tracks trends,
            and flags medication issues for your clinician to review.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 text-sm">
            {[
              { icon: FileText, t: "Health Vault", d: "PDF & image records, organised" },
              { icon: Sparkles, t: "Document intelligence", d: "Extract, review, confirm" },
              { icon: Activity, t: "Health analytics", d: "HbA1c, BP, lipids, trends" },
              { icon: ShieldCheck, t: "Consent-based sharing", d: "Scoped, time-limited, revocable" },
            ].map((f) => (
              <div key={f.t} className="rounded-xl bg-white/5 p-4 ring-1 ring-white/10">
                <f.icon className="h-5 w-5 text-teal-300" />
                <p className="mt-2 font-medium">{f.t}</p>
                <p className="text-navy-200">{f.d}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative mt-10 text-xs text-navy-300">BUILD 2036 · Health, Longevity & Biotechnology · Hackathon prototype</p>
      </section>

      <section className="flex items-center justify-center p-4 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden"><Logo tagline /></div>
          <h2 className="text-2xl font-semibold tracking-tight text-navy-900">Sign in to the demo</h2>
          <p className="mt-1 text-sm text-slate-500">Fictional accounts with synthetic data. Choose one to explore.</p>

          {params.get("expired") && <div className="mt-4"><Notice tone="warn">Your session expired. Please sign in again.</Notice></div>}

          <div className="mt-6 grid gap-2">
            {DEMO.map((d) => (
              <button key={d.email} onClick={() => go(undefined, d.email, PASSWORD)} disabled={!!busy}
                className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left shadow-sm transition hover:border-teal-300 hover:shadow-card disabled:opacity-60">
                <div className={`grid h-10 w-10 place-items-center rounded-xl ${d.role === "Doctor" ? "bg-navy-50 text-navy-700" : "bg-teal-50 text-teal-700"}`}>
                  <d.icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-navy-900">{d.name} <span className="ml-1 text-xs font-normal text-slate-500">· {d.role}</span></p>
                  <p className="truncate text-xs text-slate-500">{d.note}</p>
                </div>
                <span className="text-xs font-medium text-teal-700 opacity-0 transition group-hover:opacity-100">{busy === d.email ? "Signing in…" : "Continue →"}</span>
              </button>
            ))}
          </div>

          <div className="my-6 flex items-center gap-3 text-xs text-slate-400"><div className="h-px flex-1 bg-slate-200" />or sign in manually<div className="h-px flex-1 bg-slate-200" /></div>

          <form onSubmit={go} className="space-y-3">
            <Field label="Demo email"><input className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></Field>
            <Field label="Password" hint={<>All demo accounts use <code className="rounded bg-slate-100 px-1">{PASSWORD}</code></>}>
              <input type="password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </Field>
            {error && <ErrorBox message={error} />}
            <Button type="submit" className="w-full" loading={busy === email}><Lock className="h-4 w-4" /> Sign in</Button>
          </form>

          <p className="mt-6 text-xs leading-relaxed text-slate-500">
            Prototype authentication — not production identity verification. Do not enter real health information.
            MyKshema is not a medical device and does not replace professional medical advice.
          </p>
        </div>
      </section>
    </div>
  );
}

export default function LoginPage() {
  return <Suspense><LoginInner /></Suspense>;
}
