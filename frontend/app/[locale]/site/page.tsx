"use client";

import { ProductsPanel } from "@/components/site/ProductsPanel";
import { SiteShell } from "@/components/site/SiteShell";

export default function SiteProductsPage() {
  return (
    <SiteShell section="products">
      <ProductsPanel />
    </SiteShell>
  );
}
