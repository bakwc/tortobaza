"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { PulsePanel } from "@/components/analytics/PulsePanel";

export default function AnalyticsPulsePage() {
  return (
    <AnalyticsShell section="pulse">
      <PulsePanel />
    </AnalyticsShell>
  );
}
