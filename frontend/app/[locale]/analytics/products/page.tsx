"use client";

import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";
import { ProductsPanel } from "@/components/analytics/ProductsPanel";

export default function AnalyticsProductsPage() {
  return (
    <AnalyticsShell section="products">
      <ProductsPanel />
    </AnalyticsShell>
  );
}
