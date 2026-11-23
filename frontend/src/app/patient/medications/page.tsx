"use client";

import { PageHeader } from "@/components/ui";
import { MedicationsView } from "@/components/MedicationsView";

export default function MedicationsPage() {
  return (
    <div>
      <PageHeader eyebrow="Medications" title="Medication intelligence"
        subtitle="Every medicine with its source prescription, status and your reported adherence. Flags are for your doctor to review — MyKshema never changes your medicines." />
      <MedicationsView canEdit />
    </div>
  );
}
