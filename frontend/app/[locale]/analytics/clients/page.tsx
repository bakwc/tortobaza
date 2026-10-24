"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { ClientsPanel } from "@/components/analytics/ClientsPanel";

export default function AnalyticsClientsPage() {
  return (
    <AnalyticsShell section="clients">
      <ClientsPanel />
    </AnalyticsShell>
  );
}
