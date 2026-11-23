"use client";

import { PageHeader } from "@/components/ui";
import { ConsultationsList } from "@/components/ConsultationsList";

export default function ConsultationsPage() {
  return (
    <div>
      <PageHeader eyebrow="Consultations" title="Consultation history"
        subtitle="Visits, notes, diagnoses, doctor-authored prescriptions and follow-up instructions." />
      <ConsultationsList />
    </div>
  );
}
