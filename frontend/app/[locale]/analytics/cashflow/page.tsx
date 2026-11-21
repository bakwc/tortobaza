"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { CashflowPanel } from "@/components/analytics/CashflowPanel";

export default function AnalyticsCashflowPage() {
  return (
    <AnalyticsShell section="cashflow">
      <CashflowPanel />
    </AnalyticsShell>
  );
}
