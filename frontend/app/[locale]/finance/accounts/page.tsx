"use client";

import { FinanceAccountList } from "@/components/finance/FinanceAccountList";
import { FinanceBoard } from "@/components/finance/FinanceBoard";

export default function FinanceAccountsPage() {
  return (
    <FinanceBoard section="accounts">
      {(transactions, period, rates) => (
        <FinanceAccountList transactions={transactions} periodQuery={period.query} rates={rates} />
      )}
    </FinanceBoard>
  );
}
