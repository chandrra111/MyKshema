"use client";

import { PageHeader } from "@/components/ui";
import { AnalyticsView } from "@/components/AnalyticsView";

export default function AnalyticsPage() {
  return (
    <div>
      <PageHeader eyebrow="Health Analytics" title="Trends & indicators"
        subtitle="Recorded lab results and home measurements over time. Reference ranges appear only where they are documented on your reports." />
      <AnalyticsView canLog />
    </div>
  );
}
