"use client";

import { InventoryBlank } from "@/components/inventory/InventoryBlank";
import { InventoryShell } from "@/components/inventory/InventoryShell";

export default function InventoryBlankPage() {
  return (
    <InventoryShell section="blank">
      <InventoryBlank />
    </InventoryShell>
  );
}
