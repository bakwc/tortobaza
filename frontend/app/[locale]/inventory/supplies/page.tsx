"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { SuppliesPanel } from "@/components/inventory/SuppliesPanel";

export default function InventorySuppliesPage() {
  return (
    <InventoryShell section="supplies">
      <SuppliesPanel />
    </InventoryShell>
  );
}
