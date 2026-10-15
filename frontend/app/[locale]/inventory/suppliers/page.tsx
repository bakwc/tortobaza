"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { SuppliersPanel } from "@/components/inventory/SuppliersPanel";

export default function InventorySuppliersPage() {
  return (
    <InventoryShell section="suppliers">
      <SuppliersPanel />
    </InventoryShell>
  );
}
