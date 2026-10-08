"use client";

import { FinanceBoard } from "@/components/finance/FinanceBoard";
import { FinanceBreakdown } from "@/components/finance/FinanceBreakdown";

export default function FinanceIncomePage() {
  return (
    <FinanceBoard section="income">
      {(transactions, period) => (
        <FinanceBreakdown
          transactions={transactions.filter((tx) => tx.kind === "income")}
          mode={period.mode}
          month={period.month}
          typeField="income_type"
        />
      )}
    </FinanceBoard>
  );
}
