"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { InventoryCountsPanel } from "@/components/inventory/InventoryCountsPanel";

export default function InventoryCountsPage() {
  return (
    <InventoryShell section="inventory-counts">
      <InventoryCountsPanel />
    </InventoryShell>
  );
}
