"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { PnlPanel } from "@/components/analytics/PnlPanel";

export default function AnalyticsPnlPage() {
  return (
    <AnalyticsShell section="pnl">
      <PnlPanel />
    </AnalyticsShell>
  );
}
