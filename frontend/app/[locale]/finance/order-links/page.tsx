"use client";

import { FinanceShell } from "@/components/finance/FinanceBoard";
import { FinanceOrderLinks } from "@/components/finance/FinanceOrderLinks";

export default function FinanceOrderLinksPage() {
  return (
    <FinanceShell section="orderLinks">
      {(period) => <FinanceOrderLinks month={period.month} />}
    </FinanceShell>
  );
}
