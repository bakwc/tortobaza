"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { CogsPanel } from "@/components/analytics/CogsPanel";

export default function AnalyticsCogsPage() {
  return (
    <AnalyticsShell section="cogs">
      <CogsPanel />
    </AnalyticsShell>
  );
}
