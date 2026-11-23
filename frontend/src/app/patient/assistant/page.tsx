"use client";

import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/ui";
import { AssistantView } from "@/components/AssistantView";

export default function AssistantPage() {
  const { user } = useAuth();
  return (
    <div>
      <PageHeader eyebrow="AI Health Assistant" title="Ask about your records"
        subtitle="Grounded in your own records with sources. If something is not recorded, the assistant says so." />
      <AssistantView role="patient" storageKey={`patient.${user!.id}`} />
    </div>
  );
}
