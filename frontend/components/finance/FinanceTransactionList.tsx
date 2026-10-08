"use client";

import { useState, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  ChevronDown,
  CircleDot,
  Flower,
  Package,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Link } from "@/i18n/navigation";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, formatCrmCompactDate, formatCrmDate, formatCrmDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment"] as const;
const ACCOUNT_KINDS = ["bank", "cash", "crypto", "virtual"] as const;

type FinanceRow =
  | { type: "single"; tx: FinanceTransaction }
  | { type: "group"; orderNumber: number; items: FinanceTransaction[] };

type CrmOrderLink = FinanceTransaction["crm_orders"][number];

type Tone = {
  card: string;
  media: string;
  chip: string;
  amount: string;
};

const INCOME_TONE: Tone = {
  card: "border-emerald-300 bg-emerald-100",
  media: "border-emerald-200 bg-white text-emerald-700",
  chip: "bg-emerald-600 text-white",
  amount: "text-emerald-800",
};

const EXPENSE_TONE: Tone = {
  card: "border-rose-300 bg-rose-100",
  media: "border-rose-200 bg-white text-rose-700",
  chip: "bg-rose-600 text-white",
  amount: "text-rose-800",
};

const TRANSFER_TONE: Tone = {
  card: "border-sky-300 bg-sky-100",
  media: "border-sky-200 bg-white text-sky-700",
  chip: "bg-sky-600 text-white",
  amount: "text-sky-800",
};

const NEUTRAL_TONE: Tone = {
  card: "border-[var(--line)] bg-white",
  media: "border-[var(--line)] bg-[var(--cream)] text-[var(--muted-2)]",
  chip: "bg-[var(--cream)] text-[var(--ink)]",
  amount: "text-[var(--ink)]",
};

const NEUTRAL_ACTIVE = "bg-[var(--ink)] text-white";

const KIND_ORDER: FinanceTransaction["kind"][] = [
  "income",
  "expense",
  "transfer",
  "withdrawal",
  "investment",
  "correction",
  "other",
];

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

function isAccountKind(value: string): value is (typeof ACCOUNT_KINDS)[number] {
  return ACCOUNT_KINDS.some((item) => item === value);
}

function kindTone(kind: FinanceTransaction["kind"]): Tone {
  if (kind === "income") return INCOME_TONE;
  if (kind === "expense") return EXPENSE_TONE;
  if (kind === "transfer") return TRANSFER_TONE;
  return NEUTRAL_TONE;
}

function amountTone(amount: number): Tone {
  if (amount > 0) return INCOME_TONE;
  if (amount < 0) return EXPENSE_TONE;
  return NEUTRAL_TONE;
}

function KindIcon({ kind }: { kind: FinanceTransaction["kind"] }) {
  if (kind === "income") return <ArrowDownLeft className="h-4 w-4" />;
  if (kind === "expense") return <ArrowUpRight className="h-4 w-4" />;
  if (kind === "transfer") return <ArrowLeftRight className="h-4 w-4" />;
  return <CircleDot className="h-4 w-4" />;
}

function isIncomingTransfer(tx: FinanceTransaction): boolean {
  return Number.parseFloat(tx.amount) > 0;
}

function TxIcon({ tx }: { tx: FinanceTransaction }) {
  if (tx.kind === "transfer") {
    return isIncomingTransfer(tx) ? (
      <ArrowDownLeft className="h-4 w-4" />
    ) : (
      <ArrowUpRight className="h-4 w-4" />
    );
  }
  return <KindIcon kind={tx.kind} />;
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

function groupByDate(transactions: FinanceTransaction[]): { date: string; items: FinanceTransaction[] }[] {
  const groups: { date: string; items: FinanceTransaction[] }[] = [];
  for (const tx of transactions) {
    const last = groups[groups.length - 1];
    if (last && last.date === tx.date) {
      last.items.push(tx);
    } else {
      groups.push({ date: tx.date, items: [tx] });
    }
  }
  return groups;
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
  const [accountFilter, setAccountFilter] = useState<number | null>(null);
  const [kindFilter, setKindFilter] = useState<FinanceTransaction["kind"] | null>(null);
  const [selected, setSelected] = useState<FinanceTransaction | null>(null);

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

  const accounts = [
    ...new Map(transactions.map((tx) => [tx.account.id, tx.account.name])).entries(),
  ].sort((left, right) => left[1].localeCompare(right[1]));
  const kinds = KIND_ORDER.filter((kind) => transactions.some((tx) => tx.kind === kind));
  const visible = transactions.filter(
    (tx) =>
      (accountFilter === null || tx.account.id === accountFilter) &&
      (kindFilter === null || tx.kind === kindFilter),
  );

  return (
    <div className="grid gap-6">
      <div className="grid gap-2 rounded-2xl border border-[var(--line)] bg-white px-3 py-2.5 shadow-sm">
        <FilterRow label={t("filterAccount")}>
          <FilterPill active={accountFilter === null} activeClass={NEUTRAL_ACTIVE} onClick={() => setAccountFilter(null)}>
            {t("filterAll")}
          </FilterPill>
          {accounts.map(([id, name]) => (
            <FilterPill
              key={id}
              active={accountFilter === id}
              activeClass={NEUTRAL_ACTIVE}
              onClick={() => setAccountFilter(id)}
            >
              {name}
            </FilterPill>
          ))}
        </FilterRow>
        <FilterRow label={t("filterKind")}>
          <FilterPill active={kindFilter === null} activeClass={NEUTRAL_ACTIVE} onClick={() => setKindFilter(null)}>
            {t("filterAll")}
          </FilterPill>
          {kinds.map((kind) => (
            <FilterPill
              key={kind}
              active={kindFilter === kind}
              activeClass={kindTone(kind) === NEUTRAL_TONE ? NEUTRAL_ACTIVE : kindTone(kind).chip}
              onClick={() => setKindFilter(kind)}
            >
              <KindIcon kind={kind} />
              {t(`kinds.${kind}`)}
            </FilterPill>
          ))}
        </FilterRow>
      </div>
      {visible.length === 0 ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
          {t("empty")}
        </div>
      ) : null}
      {groupByDate(visible).map((day) => {
        const income = sumAmounts(day.items.filter((tx) => tx.kind === "income"));
        const expense = sumAmounts(day.items.filter((tx) => tx.kind === "expense"));
        return (
          <section key={day.date} className="grid gap-2">
            <div className="flex items-baseline justify-between gap-3 px-1 text-[var(--ink)]">
              <span className="min-w-0 truncate text-sm font-semibold md:text-base">
                <span className="md:hidden">{formatCrmCompactDate(day.date, locale)}</span>
                <span className="hidden md:inline">{formatCrmDate(day.date, locale)}</span>
              </span>
              <span className="flex shrink-0 items-baseline gap-2 text-xs font-medium text-[var(--muted-2)]">
                <span>{day.items.length}</span>
                {income !== 0 ? <span className="text-emerald-700">+{formatAed(income)}</span> : null}
                {expense !== 0 ? <span className="text-rose-700">{formatAed(expense)}</span> : null}
              </span>
            </div>
            {groupFlowwow(day.items).map((row) => {
              if (row.type === "single") {
                return (
                  <TransactionRow key={row.tx.id} tx={row.tx} onSelect={() => setSelected(row.tx)} t={t} />
                );
              }
              const open = openGroups.has(row.orderNumber);
              return (
                <FlowwowGroupRow
                  key={`flowwow-${row.orderNumber}`}
                  orderNumber={row.orderNumber}
                  items={row.items}
                  open={open}
                  onToggle={() => toggleGroup(row.orderNumber)}
                  onSelect={setSelected}
                  t={t}
                />
              );
            })}
          </section>
        );
      })}
      <TransactionDetailPanel tx={selected} onClose={() => setSelected(null)} t={t} />
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      <span className="mr-1 w-16 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
        {label}
      </span>
      {children}
    </div>
  );
}

function FilterPill({
  active,
  activeClass,
  onClick,
  children,
}: {
  active: boolean;
  activeClass: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors [&_svg]:h-3 [&_svg]:w-3",
        active
          ? cn("border-transparent", activeClass)
          : "border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
      )}
    >
      {children}
    </button>
  );
}

function RowShell({
  tone,
  icon,
  title,
  subtitle,
  amount,
  chips,
  action,
  onClick,
}: {
  tone: Tone;
  icon: ReactNode;
  title: string;
  subtitle: string;
  amount: string;
  chips: ReactNode;
  action: ReactNode;
  onClick: (() => void) | null;
}) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ?? undefined}
      onKeyDown={
        onClick
          ? (event) => {
              if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      className={cn(
        "flex min-w-0 items-center gap-1.5 rounded-xl border px-1.5 py-1.5 shadow-sm md:gap-3 md:rounded-2xl md:px-3 md:py-2",
        tone.card,
        onClick && "cursor-pointer transition hover:brightness-[0.97] focus-visible:outline-2 focus-visible:outline-[var(--ink)]",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border md:h-10 md:w-10 md:rounded-lg",
          tone.media,
        )}
      >
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <p className="min-w-0 flex-1 truncate text-xs text-[var(--muted-2)] md:text-sm">
            <span className="font-semibold text-[var(--ink)]">{title}</span>
            {subtitle ? (
              <>
                <span className="mx-1">·</span>
                <span>{subtitle}</span>
              </>
            ) : null}
          </p>
          <span className={cn("shrink-0 text-sm font-bold", tone.amount)}>{amount}</span>
        </div>
        <div className="mt-0.5 flex min-w-0 flex-wrap items-center gap-1.5">{chips}</div>
      </div>
      {action}
    </div>
  );
}

function Chip({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span
      className={cn(
        "flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
        className,
      )}
    >
      {children}
    </span>
  );
}

function TransactionRow({
  tx,
  onSelect,
  t,
}: {
  tx: FinanceTransaction;
  onSelect: () => void;
  t: ReturnType<typeof useTranslations<"finance">>;
}) {
  const tone = kindTone(tx.kind);
  const typeLabel = operationTypeLabel(tx, t);
  return (
    <RowShell
      tone={tone}
      icon={<TxIcon tx={tx} />}
      title={tx.counterparty_name || t(`kinds.${tx.kind}`)}
      subtitle={tx.description}
      amount={formatAed(tx.amount)}
      chips={
        <>
          <Chip className={tone.chip}>
            {tx.kind === "transfer"
              ? t(isIncomingTransfer(tx) ? "transferIncoming" : "transferOutgoing")
              : t(`kinds.${tx.kind}`)}
          </Chip>
          {typeLabel ? <Chip className="bg-white/80 text-[var(--ink)]">{typeLabel}</Chip> : null}
          <Chip className="bg-white/80 text-[var(--muted-2)]">{tx.account.name}</Chip>
          {tx.kind === "transfer" && tx.matched_account ? (
            <Chip className="bg-white/80 text-sky-800">
              {isIncomingTransfer(tx) ? (
                <ArrowDownLeft className="h-3 w-3" />
              ) : (
                <ArrowUpRight className="h-3 w-3" />
              )}
              {t(isIncomingTransfer(tx) ? "transferFrom" : "transferTo", {
                account: tx.matched_account.name,
              })}
            </Chip>
          ) : null}
          <CrmOrderChips orders={tx.crm_orders} />
        </>
      }
      action={null}
      onClick={onSelect}
    />
  );
}

function FlowwowGroupRow({
  orderNumber,
  items,
  open,
  onToggle,
  onSelect,
  t,
}: {
  orderNumber: number;
  items: FinanceTransaction[];
  open: boolean;
  onToggle: () => void;
  onSelect: (tx: FinanceTransaction) => void;
  t: ReturnType<typeof useTranslations<"finance">>;
}) {
  const total = sumAmounts(items);
  const tone = amountTone(total);
  return (
    <div className="grid gap-1">
      <RowShell
        tone={tone}
        icon={<Flower className="h-4 w-4" />}
        title={t("flowwowOrder", { id: orderNumber })}
        subtitle={t("operationCount", { count: items.length })}
        amount={formatAed(total)}
        chips={
          <>
            <Chip className="bg-white/80 text-[var(--muted-2)]">{items[0].account.name}</Chip>
            <CrmOrderChips orders={linkedOrders(items)} />
          </>
        }
        action={
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-expanded={open}
            aria-label={t("flowwowOrder", { id: orderNumber })}
            onClick={onToggle}
            className="h-8 w-8 shrink-0 px-0"
          >
            <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
          </Button>
        }
        onClick={null}
      />
      {open ? (
        <div className="ml-5 grid gap-1 border-l-2 border-[var(--line)] pl-2 md:ml-8 md:pl-3">
          {items.map((tx) => {
            const childTone = kindTone(tx.kind);
            return (
              <button
                key={tx.id}
                type="button"
                onClick={() => onSelect(tx)}
                className={cn(
                  "flex min-w-0 cursor-pointer items-center gap-2 rounded-lg border px-2 py-1 text-left text-xs transition hover:brightness-[0.97] md:text-sm",
                  childTone.card,
                )}
              >
                <span className={cn("flex h-5 w-5 shrink-0 items-center justify-center", childTone.amount)}>
                  <TxIcon tx={tx} />
                </span>
                <span className="min-w-0 flex-1 truncate text-[var(--ink)]">
                  {tx.description || t(`kinds.${tx.kind}`)}
                </span>
                <span className={cn("shrink-0 font-semibold", childTone.amount)}>{formatAed(tx.amount)}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function CrmOrderChips({ orders }: { orders: CrmOrderLink[] }) {
  return (
    <>
      {orders.map((order) => (
        <Link
          key={order.id}
          href={`/crm?date=${order.date}&order=${order.id}`}
          onClick={(event) => event.stopPropagation()}
          className="flex min-w-0 max-w-full items-center gap-1 rounded-full bg-[var(--brand)] px-1.5 py-0.5 text-[10px] font-semibold text-white hover:opacity-90"
        >
          <Package className="h-3 w-3 shrink-0" />
          <span className="shrink-0">#{order.id}</span>
          <span className="min-w-0 truncate font-medium">
            {order.weight} · {order.filling} · {order.contact}
          </span>
          <span className="shrink-0">{formatAed(order.cake_price)}</span>
        </Link>
      ))}
    </>
  );
}

function TransactionDetailPanel({
  tx,
  onClose,
  t,
}: {
  tx: FinanceTransaction | null;
  onClose: () => void;
  t: ReturnType<typeof useTranslations<"finance">>;
}) {
  return (
    <Dialog open={tx !== null} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent className="left-auto right-0 top-0 h-dvh max-h-dvh w-[min(480px,100vw)] translate-x-0 translate-y-0 overflow-y-auto rounded-none rounded-l-3xl">
        {tx ? <TransactionDetail tx={tx} t={t} /> : null}
      </DialogContent>
    </Dialog>
  );
}

function TransactionDetail({
  tx,
  t,
}: {
  tx: FinanceTransaction;
  t: ReturnType<typeof useTranslations<"finance">>;
}) {
  const locale = useLocale();
  const tone = kindTone(tx.kind);
  const kindLabel =
    tx.kind === "transfer"
      ? t(isIncomingTransfer(tx) ? "transferIncoming" : "transferOutgoing")
      : t(`kinds.${tx.kind}`);
  const typeLabel = operationTypeLabel(tx, t);
  const matched = tx.matched_transaction;
  return (
    <div className="grid gap-4 pb-6">
      <div className={cn("grid gap-2 border-b px-5 pb-4 pt-5 pr-16", tone.card)}>
        <div className="flex items-center gap-2">
          <div
            className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border", tone.media)}
          >
            <TxIcon tx={tx} />
          </div>
          <Chip className={tone.chip}>{kindLabel}</Chip>
          {typeLabel ? <Chip className="bg-white/80 text-[var(--ink)]">{typeLabel}</Chip> : null}
        </div>
        <DialogTitle className="text-lg font-semibold text-[var(--ink)]">
          {tx.counterparty_name || t(`kinds.${tx.kind}`)}
        </DialogTitle>
        <DialogDescription className="text-sm text-[var(--muted-2)]">
          {formatCrmDate(tx.date, locale)}
        </DialogDescription>
        <span className={cn("text-2xl font-bold", tone.amount)}>{formatAed(tx.amount)}</span>
      </div>

      <DetailSection title={t("detail.sectionMain")}>
        <DetailField label={t("detail.date")} value={formatCrmDate(tx.date, locale)} variant="text" />
        <DetailField
          label={t("detail.amount")}
          value={`${formatAed(tx.amount)} · ${tx.account.currency}`}
          variant="text"
        />
        <DetailField label={t("detail.kind")} value={kindLabel} variant="text" />
        <DetailField label={t("detail.operationType")} value={typeLabel} variant="text" />
        <DetailField label={t("detail.description")} value={tx.description} variant="multiline" />
      </DetailSection>

      <DetailSection title={t("detail.sectionAccount")}>
        <DetailField label={t("detail.account")} value={tx.account.name} variant="text" />
        <DetailField
          label={t("detail.accountKind")}
          value={isAccountKind(tx.account.kind) ? t(`accountKinds.${tx.account.kind}`) : tx.account.kind}
          variant="text"
        />
        <DetailField label={t("detail.bankName")} value={tx.account.bank_name} variant="text" />
        <DetailField label={t("detail.iban")} value={tx.account.iban} variant="mono" />
        <DetailField label={t("detail.currency")} value={tx.account.currency} variant="text" />
      </DetailSection>

      <DetailSection title={t("detail.sectionCounterparty")}>
        <DetailField label={t("detail.counterparty")} value={tx.counterparty_name} variant="text" />
        <DetailField label={t("detail.counterpartyIban")} value={tx.counterparty_iban} variant="mono" />
      </DetailSection>

      <DetailSection title={t("detail.sectionLinks")}>
        <DetailField
          label={t("detail.flowwowOrder")}
          value={tx.flowwow_order_number === null ? "" : t("flowwowOrder", { id: tx.flowwow_order_number })}
          variant="text"
        />
        <div className="grid gap-1">
          <span className="text-xs font-medium text-[var(--muted-2)]">{t("detail.crmOrders")}</span>
          {tx.crm_orders.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              <CrmOrderChips orders={tx.crm_orders} />
            </div>
          ) : (
            <span className="text-sm text-[var(--muted-2)]">—</span>
          )}
        </div>
        <div className="grid gap-1">
          <span className="text-xs font-medium text-[var(--muted-2)]">{t("detail.matchedTransaction")}</span>
          {matched ? (
            <div
              className={cn(
                "grid gap-0.5 rounded-xl border px-3 py-2 text-sm",
                amountTone(Number.parseFloat(matched.amount)).card,
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="min-w-0 truncate font-semibold text-[var(--ink)]">{matched.account.name}</span>
                <span
                  className={cn("shrink-0 font-bold", amountTone(Number.parseFloat(matched.amount)).amount)}
                >
                  {formatAed(matched.amount)}
                </span>
              </div>
              <span className="text-xs text-[var(--muted-2)]">
                {formatCrmDate(matched.date, locale)} · #{matched.id}
              </span>
              {matched.counterparty_name ? (
                <span className="text-xs text-[var(--ink)]">{matched.counterparty_name}</span>
              ) : null}
              {matched.description ? (
                <span className="whitespace-pre-wrap break-words text-xs text-[var(--muted-2)]">
                  {matched.description}
                </span>
              ) : null}
            </div>
          ) : (
            <span className="text-sm text-[var(--muted-2)]">—</span>
          )}
        </div>
      </DetailSection>

      <DetailSection title={t("detail.sectionTechnical")}>
        <DetailField label={t("detail.id")} value={`#${tx.id}`} variant="mono" />
        <DetailField label={t("detail.transferId")} value={tx.transfer_id ?? ""} variant="mono" />
        <DetailField label={t("detail.externalId")} value={tx.external_id} variant="mono" />
        <DetailField
          label={t("detail.createdAt")}
          value={formatCrmDateTime(tx.created_at, locale)}
          variant="text"
        />
        <DetailField
          label={t("detail.updatedAt")}
          value={formatCrmDateTime(tx.updated_at, locale)}
          variant="text"
        />
      </DetailSection>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3 px-5">
      <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">{title}</h3>
      <div className="grid gap-3 rounded-2xl border border-[var(--line)] bg-white p-3">{children}</div>
    </section>
  );
}

function DetailField({
  label,
  value,
  variant,
}: {
  label: string;
  value: string;
  variant: "text" | "mono" | "multiline";
}) {
  return (
    <div className="grid gap-0.5">
      <span className="text-xs font-medium text-[var(--muted-2)]">{label}</span>
      {value ? (
        <span
          className={cn(
            "break-words text-sm text-[var(--ink)]",
            variant === "mono" && "break-all font-mono text-xs",
            variant === "multiline" && "whitespace-pre-wrap",
          )}
        >
          {value}
        </span>
      ) : (
        <span className="text-sm text-[var(--muted-2)]">—</span>
      )}
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
