"use client";

import { Stethoscope } from "lucide-react";
import { useApi } from "@/lib/hooks";
import type { DoctorProfile } from "@/lib/types";
import { Card, CardHeader, Notice, PageHeader, Spinner } from "@/components/ui";
import { DemoSystemCard } from "@/components/DemoSystemCard";

export default function DoctorProfilePage() {
  const me = useApi<DoctorProfile>("/api/doctor/me");
  if (!me.data) return <Spinner />;
  const d = me.data;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Profile & Settings" title={d.full_name} subtitle={`${d.specialty} · ${d.hospital}`} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader icon={<Stethoscope className="h-4 w-4" />} title="Professional details" />
          <dl className="grid grid-cols-2 gap-4 p-5 text-sm">
            <div><dt className="text-xs text-slate-500">Specialty</dt><dd className="font-medium text-navy-900">{d.specialty}</dd></div>
            <div><dt className="text-xs text-slate-500">Hospital</dt><dd className="font-medium text-navy-900">{d.hospital}</dd></div>
            <div><dt className="text-xs text-slate-500">City</dt><dd className="font-medium text-navy-900">{d.city}</dd></div>
            <div><dt className="text-xs text-slate-500">Experience</dt><dd className="font-medium text-navy-900">{d.years_experience} years</dd></div>
            <div className="col-span-2"><dt className="text-xs text-slate-500">Registration no.</dt><dd className="font-medium text-navy-900">{d.registration_no} <span className="text-xs font-normal text-slate-500">(fictional)</span></dd></div>
          </dl>
        </Card>
        <Card className="p-5">
          <Notice tone="warn">Demo doctor identity is <b>not verified</b>. A production system must verify medical registration against the official medical register before granting any clinical access.</Notice>
        </Card>
        <DemoSystemCard />
      </div>
    </div>
  );
}
