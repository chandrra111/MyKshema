"use client";

import { Activity, Bot, CalendarClock, FolderLock, HeartPulse, LayoutDashboard, Pill, Settings, Stethoscope } from "lucide-react";
import { AppShell, type NavItem } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useRequireRole } from "@/lib/auth";

const NAV: NavItem[] = [
  { href: "/patient", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/patient/vault", label: "My Health Vault", icon: FolderLock },
  { href: "/patient/history", label: "Medical History", icon: CalendarClock },
  { href: "/patient/medications", label: "Medications", icon: Pill },
  { href: "/patient/analytics", label: "Health Analytics", icon: Activity },
  { href: "/patient/assistant", label: "AI Health Assistant", icon: Bot },
  { href: "/patient/doctors", label: "Doctor Connect", icon: Stethoscope },
  { href: "/patient/consultations", label: "Consultations", icon: HeartPulse },
  { href: "/patient/settings", label: "Profile & Settings", icon: Settings },
];

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  const { user } = useRequireRole("patient");
  if (!user) return <div className="grid min-h-screen place-items-center"><Spinner label="Opening your health record…" /></div>;
  return <AppShell nav={NAV} portal="Patient">{children}</AppShell>;
}
