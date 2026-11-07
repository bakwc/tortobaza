"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { PacePanel } from "@/components/analytics/PacePanel";

export default function AnalyticsPacePage() {
  return (
    <AnalyticsShell section="pace">
      <PacePanel />
    </AnalyticsShell>
  );
}
