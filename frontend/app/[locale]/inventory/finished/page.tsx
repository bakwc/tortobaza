"use client";

import { FinishedProductionsPanel } from "@/components/inventory/FinishedProductionsPanel";
import { InventoryShell } from "@/components/inventory/InventoryShell";

export default function InventoryFinishedPage() {
  return (
    <InventoryShell section="finished">
      <FinishedProductionsPanel />
    </InventoryShell>
  );
}
