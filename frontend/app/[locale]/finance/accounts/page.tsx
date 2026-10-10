"use client";

import { FinanceAccountList } from "@/components/finance/FinanceAccountList";
import { FinanceBoard } from "@/components/finance/FinanceBoard";

export default function FinanceAccountsPage() {
  return (
    <FinanceBoard section="accounts">
      {(transactions, period) => (
        <FinanceAccountList transactions={transactions} periodQuery={period.query} />
      )}
    </FinanceBoard>
  );
}
