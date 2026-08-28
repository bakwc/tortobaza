"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  Package,
  Pencil,
  Plus,
  Store,
  Trash2,
  Truck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmDeleteOrderDialog } from "@/components/crm/CrmDeleteOrderDialog";
import { Link, useRouter } from "@/i18n/navigation";
import { useCrmOrdersByMonth, useDeleteCrmOrder } from "@/hooks/useCrmOrders";
import type { CrmOrder } from "@/lib/api/types";
import {
  formatAed,
  formatCrmCompactDate,
  formatCrmDate,
  formatCrmMonth,
  getTbilisiTodayIsoDate,
  sortCrmBoardOrders,
} from "@/lib/format";
import { cn } from "@/lib/utils";

function shiftMonth(yyyyMm: string, delta: number): string {
  const [yearStr, monthStr] = yyyyMm.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${nextYear}-${nextMonth}`;
}

function formatTimeSlot(
  start: string | null,
  end: string | null,
  whenReady: boolean,
  unknownLabel: string,
  whenReadyLabel: string,
): string {
  if (whenReady) return whenReadyLabel;
  if (!start) return unknownLabel;
  const s = start.slice(0, 5);
  if (!end) return s;
  return `${s} – ${end.slice(0, 5)}`;
}

function groupOrdersByDate(orders: CrmOrder[]): { date: string; orders: CrmOrder[] }[] {
  const groups: { date: string; orders: CrmOrder[] }[] = [];
  for (const order of orders) {
    const last = groups[groups.length - 1];
    if (last && last.date === order.date) {
      last.orders.push(order);
    } else {
      groups.push({ date: order.date, orders: [order] });
    }
  }
  return groups;
}

export default function CrmMonthPage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-3 py-6 md:px-4 md:py-12">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-[40vh] items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <CrmMonthBoard />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function CrmMonthBoard() {
  const t = useTranslations("crm");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentMonth = getTbilisiTodayIsoDate().slice(0, 7);
  const selectedMonth = searchParams.get("month") ?? currentMonth;

  const setSelectedMonth = (next: string) => {
    router.replace(`/crm/month?month=${next}`);
  };

  const ordersQuery = useCrmOrdersByMonth(selectedMonth);
  const orders = sortCrmBoardOrders(ordersQuery.data?.orders ?? []);
  const isCurrentMonth = selectedMonth === currentMonth;

  const deliveredCount = orders.filter((o) => o.is_delivered).length;
  const paidCount = orders.filter((o) => o.is_paid).length;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild variant="outline">
          <Link href="/crm">{t("dailyBoard")}</Link>
        </Button>
        <Button asChild>
          <Link
            href={`/crm/new?date=${isCurrentMonth ? getTbilisiTodayIsoDate() : `${selectedMonth}-01`}`}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            {t("createOrder")}
          </Link>
        </Button>
      </div>
      <div className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl md:p-6">
        <div className="flex items-center justify-between gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedMonth(shiftMonth(selectedMonth, -1))}
            className="h-9 w-9 shrink-0 px-0 sm:w-auto sm:px-4"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="hidden sm:inline">{t("prevMonth")}</span>
          </Button>

          <div className="flex min-w-0 flex-1 flex-col items-center gap-1 text-center">
            <div className="flex items-center gap-2 text-base font-semibold text-[var(--ink)] md:text-lg">
              <Calendar className="h-4 w-4 shrink-0 text-[var(--brand)] md:h-5 md:w-5" />
              <span className="truncate">{formatCrmMonth(selectedMonth, locale)}</span>
            </div>
            <div className="flex items-center gap-2">
              {isCurrentMonth ? (
                <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                  {t("thisMonth")}
                </span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedMonth(currentMonth)}
                  className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                >
                  {t("jumpToThisMonth")}
                </Button>
              )}
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedMonth(shiftMonth(selectedMonth, 1))}
            className="h-9 w-9 shrink-0 px-0 sm:w-auto sm:px-4"
          >
            <span className="hidden sm:inline">{t("nextMonth")}</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3 border-t border-[var(--line)] pt-4 text-xs sm:gap-6 sm:text-sm">
          <div className="flex items-center gap-1.5 text-[var(--ink)]">
            <Package className="h-4 w-4 text-[var(--muted-2)]" />
            <span>{t("total")}</span>
            <span className="font-bold">{orders.length}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <Check className="h-4 w-4" />
            <span>{t("deliveredCount")}</span>
            <span className="font-bold">
              {deliveredCount} / {orders.length}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[var(--brand)]">
            <CreditCard className="h-4 w-4" />
            <span>{t("paidCount")}</span>
            <span className="font-bold">
              {paidCount} / {orders.length}
            </span>
          </div>
        </div>
      </div>

      {ordersQuery.isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12">
          <Spinner className="h-8 w-8 text-[var(--brand)]" />
        </div>
      ) : ordersQuery.isError ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
          {t("monthLoadError")}
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
          <Package className="h-12 w-12 text-[var(--muted)]" />
          <p className="mt-4 text-base font-semibold text-[var(--ink)]">
            {t("monthEmptyTitle")}
          </p>
          <p className="mt-1 text-sm text-[var(--muted-2)]">
            {t("monthEmptyHint")}
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {groupOrdersByDate(orders).map((group) => (
            <section key={group.date} className="grid gap-2">
              <Link
                href={`/crm?date=${group.date}`}
                className="flex items-baseline justify-between gap-3 px-1 text-[var(--ink)] hover:text-[var(--brand)]"
              >
                <span className="min-w-0 truncate text-sm font-semibold md:text-base">
                  <span className="md:hidden">{formatCrmCompactDate(group.date, locale)}</span>
                  <span className="hidden md:inline">{formatCrmDate(group.date, locale)}</span>
                </span>
                <span className="shrink-0 text-xs font-medium text-[var(--muted-2)]">
                  {group.orders.length}
                </span>
              </Link>
              {group.orders.map((order) => (
                <CrmMonthOrderRow key={order.id} order={order} />
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function CrmMonthOrderRow({ order }: { order: CrmOrder }) {
  const t = useTranslations("crm");
  const thumb = order.images[0];
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const deleteMutation = useDeleteCrmOrder();

  return (
    <div
      className={cn(
        "flex min-w-0 items-center gap-1.5 rounded-xl border px-1.5 py-1.5 shadow-sm md:gap-3 md:rounded-2xl md:px-3 md:py-2",
        order.is_delivered
          ? "border-sky-300 bg-sky-100"
          : order.taken_by_name
            ? "border-orange-300 bg-orange-100"
            : "border-[var(--line)] bg-white",
      )}
    >
      <div
        className={cn(
          "h-8 w-8 shrink-0 overflow-hidden rounded-md border md:h-12 md:w-12 md:rounded-lg",
          order.is_delivered
            ? "border-sky-200 bg-white"
            : order.taken_by_name
              ? "border-orange-200 bg-white"
              : "border-[var(--line)] bg-[var(--cream)]",
        )}
      >
        {thumb ? (
          <img
            src={thumb.image.src}
            srcSet={thumb.image.srcset}
            sizes="48px"
            alt={t("orderAlt", { id: order.id })}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[var(--muted)]">
            <Package className="h-4 w-4" />
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex min-w-0 items-center gap-1 text-sm font-semibold text-[var(--ink)]">
            <Clock className="h-3.5 w-3.5 shrink-0 text-[var(--brand)]" />
            <span className="truncate">
              {formatTimeSlot(
                order.time_start,
                order.time_end,
                order.when_ready,
                t("timeUnknown"),
                t("timeWhenReady"),
              )}
            </span>
          </div>
          <p className="min-w-0 flex-1 truncate text-xs text-[var(--muted-2)] md:text-sm">
            <span className="font-semibold text-[var(--ink)]">{order.weight}</span>
            <span className="mx-1">·</span>
            <span>{order.filling}</span>
          </p>
          <span className="shrink-0 text-sm font-bold text-[var(--ink)]">
            {formatAed(order.cake_price)}
          </span>
        </div>
        <div className="flex min-w-0 items-center gap-1.5">
          <p className="min-w-0 flex-1 truncate text-xs font-medium text-[var(--ink)] md:text-sm">
            {order.contact}
          </p>
          <span
            className={cn(
              "hidden shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold sm:flex",
              order.fulfillment_type === "delivery"
                ? "bg-amber-100 text-amber-900"
                : "bg-blue-100 text-blue-900",
            )}
          >
            {order.fulfillment_type === "delivery" ? (
              <Truck className="h-3 w-3" />
            ) : (
              <Store className="h-3 w-3" />
            )}
            <span className="hidden md:inline">
              {order.fulfillment_type === "delivery" ? t("delivery") : t("pickup")}
            </span>
          </span>
          <span
            className={cn(
              "flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
              order.is_delivered
                ? "bg-sky-600 text-white"
                : "hidden bg-[var(--cream)] text-[var(--muted-2)] md:flex",
            )}
          >
            <Check className="h-3 w-3 md:hidden" />
            <span className="hidden md:inline">{t("delivered")}</span>
          </span>
          <span
            className={cn(
              "flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
              order.is_paid
                ? "bg-emerald-600 text-white"
                : "hidden bg-[var(--cream)] text-[var(--muted-2)] md:flex",
            )}
          >
            <CreditCard className="h-3 w-3 md:hidden" />
            <span className="hidden md:inline">{t("paid")}</span>
          </span>
        </div>
      </div>

      <Button
        asChild
        variant="outline"
        size="sm"
        className="h-8 w-8 shrink-0 px-0 md:w-auto md:px-3"
      >
        <Link href={`/crm/${order.id}/edit`}>
          <Pencil className="h-3.5 w-3.5 md:mr-1" />
          <span className="hidden md:inline">{t("editOrder")}</span>
        </Link>
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 w-8 shrink-0 px-0 text-[var(--danger)] hover:bg-red-50"
        aria-label={t("deleteOrder")}
        onClick={() => {
          deleteMutation.reset();
          setIsDeleteOpen(true);
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
      <CrmDeleteOrderDialog
        open={isDeleteOpen}
        onOpenChange={setIsDeleteOpen}
        isPending={deleteMutation.isPending}
        isError={deleteMutation.isError}
        onConfirm={() =>
          deleteMutation.mutate(order.id, {
            onSuccess: () => setIsDeleteOpen(false),
          })
        }
      />
    </div>
  );
}
