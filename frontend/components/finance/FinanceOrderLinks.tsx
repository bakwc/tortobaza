"use client";

import { type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Spinner } from "@/components/ui/spinner";
import { useFinanceOrderLinks } from "@/hooks/useFinanceTransactions";
import { useFinanceScope } from "@/hooks/useFinanceScope";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import type { FinanceOrderLink } from "@/lib/api/types";
import { crmOrderTotal, formatAed, formatCrmCompactDate, formatTimeSlot } from "@/lib/format";
import { cn } from "@/lib/utils";

const PAYMENT_TYPES = [
  "unknown",
  "cash",
  "terminal",
  "tbc",
  "bog",
  "tbank",
  "flowwow",
  "crypto",
  "paypal",
  "online",
] as const;

const PAYMENT_TYPE_MESSAGE_KEYS = {
  unknown: "paymentUnknown",
  cash: "paymentCash",
  terminal: "paymentTerminal",
  tbc: "paymentTbc",
  bog: "paymentBog",
  tbank: "paymentTbank",
  flowwow: "paymentFlowwow",
  crypto: "paymentCrypto",
  paypal: "paymentPaypal",
  online: "paymentOnline",
} as const;

const LINKED_CARD = "border-emerald-300 bg-emerald-100";
const UNLINKED_CARD = "border-rose-300 bg-rose-100";
const LINKED_BADGE = "bg-emerald-600 text-white";
const UNLINKED_BADGE = "bg-rose-600 text-white";
const NEUTRAL_ACTIVE = "bg-[var(--ink)] text-white";

type PaymentType = (typeof PAYMENT_TYPES)[number];
type LinkFilter = "linked" | "unlinked";
type PaidFilter = "yes" | "no";

function isPaymentType(value: string): value is PaymentType {
  return PAYMENT_TYPES.some((item) => item === value);
}

function readLink(value: string | null): LinkFilter | null {
  if (value === "linked" || value === "unlinked") return value;
  return null;
}

function readPayment(value: string | null): PaymentType | null {
  if (value !== null && isPaymentType(value)) return value;
  return null;
}

function readPaid(value: string | null): PaidFilter | null {
  if (value === "yes" || value === "no") return value;
  return null;
}

function recipientLine(contact: string): string {
  const line = contact.split("\n")[0] ?? "";
  return line.trim();
}

function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      <span className="mr-1 w-28 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
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
        "flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors",
        active
          ? cn("border-transparent", activeClass)
          : "border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
      )}
    >
      {children}
    </button>
  );
}

export function FinanceOrderLinks({ month }: { month: string }) {
  const t = useTranslations("finance");
  const crm = useTranslations("crm");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { scope } = useFinanceScope();
  const query = useFinanceOrderLinks(month, scope);
  const linkFilter = readLink(searchParams.get("link"));
  const paymentFilter = readPayment(searchParams.get("payment"));
  const paidFilter = readPaid(searchParams.get("paid"));

  function replaceFilters(next: { link: LinkFilter | null; payment: PaymentType | null; paid: PaidFilter | null }) {
    const params = new URLSearchParams(searchParams.toString());
    if (next.link === null) params.delete("link");
    else params.set("link", next.link);
    if (next.payment === null) params.delete("payment");
    else params.set("payment", next.payment);
    if (next.paid === null) params.delete("paid");
    else params.set("paid", next.paid);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  if (query.isError) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }
  if (!query.data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  const orders = query.data.orders;
  const paymentTypes = PAYMENT_TYPES.filter((type) => orders.some((order) => order.payment_type === type));
  const scoped = orders.filter(
    (order) =>
      (paymentFilter === null || order.payment_type === paymentFilter) &&
      (paidFilter === null || order.is_paid === (paidFilter === "yes")),
  );
  const linkedCount = scoped.filter((order) => order.transactions.length > 0).length;
  const unlinkedCount = scoped.length - linkedCount;
  const visible = scoped.filter((order) => {
    if (linkFilter === "linked") return order.transactions.length > 0;
    if (linkFilter === "unlinked") return order.transactions.length === 0;
    return true;
  });

  return (
    <div className="grid gap-4">
      <div className="grid gap-2 rounded-2xl border border-[var(--line)] bg-white px-3 py-2.5 shadow-sm">
        <FilterRow label={t("orderLinksFilterLink")}>
          <FilterPill
            active={linkFilter === null}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ link: null, payment: paymentFilter, paid: paidFilter })}
          >
            {t("filterAll")}
          </FilterPill>
          <FilterPill
            active={linkFilter === "linked"}
            activeClass={LINKED_BADGE}
            onClick={() => replaceFilters({ link: "linked", payment: paymentFilter, paid: paidFilter })}
          >
            {t("orderLinksLinked")}
          </FilterPill>
          <FilterPill
            active={linkFilter === "unlinked"}
            activeClass={UNLINKED_BADGE}
            onClick={() => replaceFilters({ link: "unlinked", payment: paymentFilter, paid: paidFilter })}
          >
            {t("orderLinksUnlinked")}
          </FilterPill>
        </FilterRow>
        <FilterRow label={t("orderLinksFilterPayment")}>
          <FilterPill
            active={paymentFilter === null}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ link: linkFilter, payment: null, paid: paidFilter })}
          >
            {t("filterAll")}
          </FilterPill>
          {paymentTypes.map((type) => (
            <FilterPill
              key={type}
              active={paymentFilter === type}
              activeClass={NEUTRAL_ACTIVE}
              onClick={() => replaceFilters({ link: linkFilter, payment: type, paid: paidFilter })}
            >
              {crm(PAYMENT_TYPE_MESSAGE_KEYS[type])}
            </FilterPill>
          ))}
        </FilterRow>
        <FilterRow label={t("orderLinksFilterPaid")}>
          <FilterPill
            active={paidFilter === null}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ link: linkFilter, payment: paymentFilter, paid: null })}
          >
            {t("filterAll")}
          </FilterPill>
          <FilterPill
            active={paidFilter === "yes"}
            activeClass={LINKED_BADGE}
            onClick={() => replaceFilters({ link: linkFilter, payment: paymentFilter, paid: "yes" })}
          >
            {crm("paid")}
          </FilterPill>
          <FilterPill
            active={paidFilter === "no"}
            activeClass={UNLINKED_BADGE}
            onClick={() => replaceFilters({ link: linkFilter, payment: paymentFilter, paid: "no" })}
          >
            {crm("notPaid")}
          </FilterPill>
        </FilterRow>
      </div>

      {orders.length > 0 ? (
        <p className="text-sm font-semibold text-[var(--ink)]">
          {t("orderLinksCount", { linked: linkedCount, unlinked: unlinkedCount })}
        </p>
      ) : null}

      {visible.length === 0 ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
          {orders.length === 0 ? t("orderLinksEmpty") : t("orderLinksFilterEmpty")}
        </div>
      ) : (
        <div className="grid gap-2">
          {visible.map((order) => (
            <OrderRow
              key={order.id}
              order={order}
              scope={scope}
              locale={locale}
              linkedLabel={t("orderLinksLinked")}
              unlinkedLabel={t("orderLinksUnlinked")}
              prepaymentLabel={t("orderLinksPrepayment", {
                amount: formatAed(order.prepayment),
              })}
              paymentDateLabel={
                order.payment_date === null
                  ? ""
                  : t("orderLinksPaymentDate", {
                      date: formatCrmCompactDate(order.payment_date, locale),
                    })
              }
              paymentLabel={crm(PAYMENT_TYPE_MESSAGE_KEYS[order.payment_type])}
              paidLabel={order.is_paid ? crm("paid") : crm("notPaid")}
              timeLabel={formatTimeSlot(
                order.time_start,
                order.time_end,
                order.when_ready,
                crm("timeUnknown"),
                crm("timeWhenReady"),
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function OrderRow({
  order,
  scope,
  locale,
  linkedLabel,
  unlinkedLabel,
  prepaymentLabel,
  paymentDateLabel,
  paymentLabel,
  paidLabel,
  timeLabel,
}: {
  order: FinanceOrderLink;
  scope: string;
  locale: string;
  linkedLabel: string;
  unlinkedLabel: string;
  prepaymentLabel: string;
  paymentDateLabel: string;
  paymentLabel: string;
  paidLabel: string;
  timeLabel: string;
}) {
  const linked = order.transactions.length > 0;
  const recipient = recipientLine(order.contact);
  const prepayment = Number.parseFloat(order.prepayment);
  return (
    <div
      className={cn(
        "grid min-w-0 gap-1.5 rounded-xl border px-3 py-2 shadow-sm md:rounded-2xl",
        linked ? LINKED_CARD : UNLINKED_CARD,
      )}
    >
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-semibold",
            linked ? LINKED_BADGE : UNLINKED_BADGE,
          )}
        >
          {linked ? linkedLabel : unlinkedLabel}
        </span>
        <Link
          href={`/crm?date=${order.date}&order=${order.id}`}
          className="text-sm font-semibold text-[var(--ink)] underline-offset-2 hover:underline"
        >
          #{order.id}
        </Link>
        <span className="text-sm font-semibold text-[var(--ink)]">
          {formatCrmCompactDate(order.date, locale)}
        </span>
        <span className="text-sm text-[var(--ink)]">{timeLabel}</span>
        <span className={cn("text-sm font-bold", linked ? "text-emerald-800" : "text-rose-800")}>
          {formatAed(crmOrderTotal(order))}
        </span>
        {prepayment > 0 ? (
          <span className="text-xs font-medium text-[var(--ink)]">{prepaymentLabel}</span>
        ) : null}
        <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-[var(--ink)]">
          {paymentLabel}
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-semibold",
            order.is_paid ? "bg-emerald-600 text-white" : "bg-white text-[var(--ink)]",
          )}
        >
          {paidLabel}
        </span>
        {recipient !== "" ? (
          <span className="min-w-0 truncate text-sm font-medium text-[var(--ink)]">{recipient}</span>
        ) : null}
        {paymentDateLabel !== "" ? (
          <span className="text-xs font-medium text-[var(--ink)]">{paymentDateLabel}</span>
        ) : null}
      </div>
      {linked ? (
        <div className="flex min-w-0 flex-wrap gap-1.5">
          {order.transactions.map((tx) => (
            <Link
              key={tx.id}
              href={`/finance?month=${tx.date.slice(0, 7)}&transaction=${tx.id}&scope=${scope}`}
              className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-[var(--ink)] underline-offset-2 hover:underline"
            >
              {formatCrmCompactDate(tx.date, locale)} · {formatAed(tx.amount)} · {tx.account_name}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
