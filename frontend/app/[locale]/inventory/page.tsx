"use client";

import { InventoryShell } from "@/components/inventory/InventoryShell";
import { StockPanel } from "@/components/inventory/StockPanel";

export default function InventoryStockPage() {
  return (
    <InventoryShell section="stock">
      <StockPanel />
    </InventoryShell>
  );
}
