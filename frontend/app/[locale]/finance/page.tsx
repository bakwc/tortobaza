"use client";

import { FinanceBoard } from "@/components/finance/FinanceBoard";
import { FinanceTransactionList } from "@/components/finance/FinanceTransactionList";

export default function FinanceOperationsPage() {
  return (
    <FinanceBoard section="operations">
      {(transactions, _period, rates) => (
        <FinanceTransactionList transactions={transactions} rates={rates} />
      )}
    </FinanceBoard>
  );
}
