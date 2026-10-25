"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { OverviewPanel } from "@/components/analytics/OverviewPanel";

export default function AnalyticsOverviewPage() {
  return (
    <AnalyticsShell section="overview">
      <OverviewPanel />
    </AnalyticsShell>
  );
}
