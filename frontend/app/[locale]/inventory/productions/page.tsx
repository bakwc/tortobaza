"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { ProductionsPanel } from "@/components/inventory/ProductionsPanel";

export default function InventoryProductionsPage() {
  return (
    <InventoryShell section="productions">
      <ProductionsPanel />
    </InventoryShell>
  );
}
