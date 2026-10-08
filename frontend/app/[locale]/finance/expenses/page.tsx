"use client";

import { FinanceBoard } from "@/components/finance/FinanceBoard";
import { FinanceBreakdown } from "@/components/finance/FinanceBreakdown";

export default function FinanceExpensesPage() {
  return (
    <FinanceBoard section="expenses">
      {(transactions, period) => (
        <FinanceBreakdown
          transactions={transactions.filter((tx) => tx.kind === "expense")}
          mode={period.mode}
          month={period.month}
          typeField="expense_type"
        />
      )}
    </FinanceBoard>
  );
}
