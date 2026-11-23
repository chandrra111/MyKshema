"use client";

import { Bot, ClipboardList, KeyRound, LayoutDashboard, Settings, Users } from "lucide-react";
import { AppShell, type NavItem } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useRequireRole } from "@/lib/auth";

const NAV: NavItem[] = [
  { href: "/doctor", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/doctor/patients", label: "My Patients", icon: Users },
  { href: "/doctor/assistant", label: "AI Clinical Assistant", icon: Bot },
  { href: "/doctor/access", label: "Access Requests", icon: KeyRound },
  { href: "/doctor/activity", label: "Activity Log", icon: ClipboardList },
  { href: "/doctor/profile", label: "Profile & Settings", icon: Settings },
];

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  const { user } = useRequireRole("doctor");
  if (!user) return <div className="grid min-h-screen place-items-center"><Spinner label="Opening doctor portal…" /></div>;
  return <AppShell nav={NAV} portal="Doctor">{children}</AppShell>;
}
