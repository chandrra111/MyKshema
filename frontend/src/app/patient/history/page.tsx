"use client";

import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/ui";
import { TimelineView } from "@/components/TimelineView";
import { ConditionsAllergies } from "@/components/ConditionsAllergies";

export default function HistoryPage() {
  const { user } = useAuth();
  const pid = user!.patient_id!;
  return (
    <div>
      <PageHeader eyebrow="Medical History" title="Your health timeline"
        subtitle="Consultations, prescriptions, lab reports, medication changes and documents in one chronological view, each linked to its source." />
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <TimelineView patientId={pid} />
        <ConditionsAllergies patientId={pid} />
      </div>
    </div>
  );
}
