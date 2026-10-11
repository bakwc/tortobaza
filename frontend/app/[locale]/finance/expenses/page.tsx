"use client";

import { FinanceBoard } from "@/components/finance/FinanceBoard";
import { FinanceBreakdown } from "@/components/finance/FinanceBreakdown";

export default function FinanceExpensesPage() {
  return (
    <FinanceBoard section="expenses">
      {(transactions, period, rates) => (
        <FinanceBreakdown
          transactions={transactions.filter((tx) => tx.kind === "expense")}
          month={period.month}
          typeField="expense_type"
          rates={rates}
        />
      )}
    </FinanceBoard>
  );
}
