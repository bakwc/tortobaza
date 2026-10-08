"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";
import { Link } from "@/i18n/navigation";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, formatCrmCompactDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment"] as const;

type FinanceRow =
  | { type: "single"; tx: FinanceTransaction }
  | { type: "group"; orderNumber: number; items: FinanceTransaction[] };

type CrmOrderLink = FinanceTransaction["crm_orders"][number];

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

function kindTone(kind: FinanceTransaction["kind"]): string {
  if (kind === "income") return "bg-green-50";
  if (kind === "expense") return "bg-red-50";
  if (kind === "transfer") return "bg-blue-50";
  return "bg-white";
}

function amountTone(amount: number): string {
  if (amount > 0) return "bg-green-50";
  if (amount < 0) return "bg-red-50";
  return "bg-white";
}

function sumAmounts(items: FinanceTransaction[]): number {
  const cents = items.reduce((sum, tx) => sum + Math.round(Number.parseFloat(tx.amount) * 100), 0);
  return cents / 100;
}

function linkedOrders(items: FinanceTransaction[]): CrmOrderLink[] {
  const byId = new Map<number, CrmOrderLink>();
  for (const tx of items) {
    for (const order of tx.crm_orders) {
      byId.set(order.id, order);
    }
  }
  return [...byId.values()];
}

function groupFlowwow(transactions: FinanceTransaction[]): FinanceRow[] {
  const seen = new Set<number>();
  const rows: FinanceRow[] = [];
  for (const tx of transactions) {
    const orderNumber = tx.flowwow_order_number;
    if (orderNumber === null) {
      rows.push({ type: "single", tx });
      continue;
    }
    if (seen.has(orderNumber)) continue;
    seen.add(orderNumber);
    const items = transactions.filter((item) => item.flowwow_order_number === orderNumber);
    if (items.length === 1) {
      rows.push({ type: "single", tx });
    } else {
      rows.push({ type: "group", orderNumber, items });
    }
  }
  return rows;
}

export function FinanceTransactionList({ transactions }: { transactions: FinanceTransaction[] }) {
  const t = useTranslations("finance");
  const locale = useLocale();
  const [openGroups, setOpenGroups] = useState<ReadonlySet<number>>(new Set());

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  function toggleGroup(orderNumber: number) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(orderNumber)) {
        next.delete(orderNumber);
      } else {
        next.add(orderNumber);
      }
      return next;
    });
  }

  return (
    <ul className="grid gap-1.5">
      {groupFlowwow(transactions).map((row) => {
        if (row.type === "single") {
          return (
            <li key={row.tx.id}>
              <TransactionRow tx={row.tx} locale={locale} t={t} showOrders />
            </li>
          );
        }
        const open = openGroups.has(row.orderNumber);
        const total = sumAmounts(row.items);
        return (
          <li key={`flowwow-${row.orderNumber}`} className="grid gap-1">
            <div
              className={cn(
                "flex items-center gap-3 rounded-2xl border border-[var(--line)] px-3 py-1.5",
                amountTone(total),
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 items-baseline gap-2 text-sm">
                  <span className="shrink-0 font-medium text-[var(--ink)]">
                    {formatCrmCompactDate(row.items[0].date, locale)}
                  </span>
                  <span className="truncate text-[var(--muted-2)]">
                    {t("flowwowOrder", { id: row.orderNumber })}
                    {" · "}
                    {t("operationCount", { count: row.items.length })}
                  </span>
                </div>
                <CrmOrderLinks orders={linkedOrders(row.items)} locale={locale} />
              </div>
              <div className="shrink-0 text-sm font-semibold text-[var(--ink)]">{formatAed(total)}</div>
              <button
                type="button"
                aria-expanded={open}
                aria-label={t("flowwowOrder", { id: row.orderNumber })}
                onClick={() => toggleGroup(row.orderNumber)}
                className="shrink-0 rounded-md p-1 text-[var(--ink)]"
              >
                <ChevronDown className={cn("h-4 w-4", open && "rotate-180")} />
              </button>
            </div>
            {open
              ? row.items.map((tx) => (
                  <div key={tx.id} className="ml-4">
                    <TransactionRow tx={tx} locale={locale} t={t} showOrders={false} />
                  </div>
                ))
              : null}
          </li>
        );
      })}
    </ul>
  );
}

function TransactionRow({
  tx,
  locale,
  t,
  showOrders,
}: {
  tx: FinanceTransaction;
  locale: string;
  t: ReturnType<typeof useTranslations<"finance">>;
  showOrders: boolean;
}) {
  const typeLabel = operationTypeLabel(tx, t);
  const meta = [
    t(`kinds.${tx.kind}`),
    tx.account.name,
    typeLabel,
    tx.counterparty_name,
  ]
    .filter((part) => part !== "")
    .join(" · ");

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-2xl border border-[var(--line)] px-3 py-1.5",
        kindTone(tx.kind),
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-baseline gap-2 text-sm">
          <span className="shrink-0 font-medium text-[var(--ink)]">
            {formatCrmCompactDate(tx.date, locale)}
          </span>
          <span className="truncate text-[var(--muted-2)]">{meta}</span>
        </div>
        {tx.description ? (
          <div className="truncate text-xs text-[var(--muted-2)]">{tx.description}</div>
        ) : null}
        {showOrders ? <CrmOrderLinks orders={tx.crm_orders} locale={locale} /> : null}
      </div>
      <div className="shrink-0 text-sm font-semibold text-[var(--ink)]">{formatAed(tx.amount)}</div>
    </div>
  );
}

function CrmOrderLinks({ orders, locale }: { orders: CrmOrderLink[]; locale: string }) {
  if (orders.length === 0) return null;
  return (
    <div className="grid">
      {orders.map((order) => (
        <Link
          key={order.id}
          href={`/crm?date=${order.date}&order=${order.id}`}
          className="truncate text-xs font-medium text-[var(--brand)]"
        >
          #{order.id}
          {" · "}
          {formatCrmCompactDate(order.date, locale)}
          {" · "}
          {order.contact}
          {" · "}
          {order.weight}
          {" · "}
          {order.filling}
          {" · "}
          {formatAed(order.cake_price)}
        </Link>
      ))}
    </div>
  );
}

function operationTypeLabel(
  tx: FinanceTransaction,
  t: ReturnType<typeof useTranslations<"finance">>,
): string {
  if (tx.kind === "income" && tx.income_type) {
    if (isIncomeType(tx.income_type)) {
      return t(`incomeTypes.${tx.income_type}`);
    }
    return tx.income_type;
  }
  if (tx.kind === "expense" && tx.expense_type) {
    if (isExpenseType(tx.expense_type)) {
      return t(`expenseTypes.${tx.expense_type}`);
    }
    return tx.expense_type;
  }
  return "";
}
