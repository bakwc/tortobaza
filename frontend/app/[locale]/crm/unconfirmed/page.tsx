"use client";

import { Suspense, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { CreditCard, Package, Pencil, Plus, Store, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmDeleteOrderDialog } from "@/components/crm/CrmDeleteOrderDialog";
import { CrmOrderActionsMenu } from "@/components/crm/CrmOrderActionsMenu";
import { CrmOrderTimeSlot } from "@/components/crm/CrmOrderTimeSlot";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { Link } from "@/i18n/navigation";
import { useCurrentUser } from "@/hooks/useAuth";
import { useCrmUnconfirmedOrders, useDeleteCrmOrder } from "@/hooks/useCrmOrders";
import type { CrmOrder } from "@/lib/api/types";
import { CRM_ORDER_STATUS_MESSAGE_KEYS, crmOrderStatusTone } from "@/lib/crmStatus";
import {
  formatAed,
  formatCrmCompactDate,
  formatCrmDate,
  getTbilisiTodayIsoDate,
  sortCrmBoardOrders,
} from "@/lib/format";
import { cn } from "@/lib/utils";

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

export default function CrmUnconfirmedPage() {
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
          <CrmUnconfirmedBoard />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function CrmUnconfirmedBoard() {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();
  const locale = useLocale();
  const ordersQuery = useCrmUnconfirmedOrders();
  const orders = sortCrmBoardOrders(ordersQuery.data?.orders ?? []);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild variant="outline">
          <Link href="/crm/map">{t("ordersMap")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/crm">{t("dailyBoard")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/crm/month">{t("monthlyOrders")}</Link>
        </Button>
        {currentUser.data?.is_staff ? (
          <Button asChild>
            <Link href={`/crm/new?date=${getTbilisiTodayIsoDate()}`}>
              <Plus className="mr-1.5 h-4 w-4" />
              {t("createOrder")}
            </Link>
          </Button>
        ) : null}
        <CrmOverflowMenu />
      </div>

      {ordersQuery.isLoading ? (
        <div className="flex min-h-[300px] items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12">
          <Spinner className="h-8 w-8 text-[var(--brand)]" />
        </div>
      ) : ordersQuery.isError ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-12 text-center text-sm text-[var(--danger)]">
          {t("unconfirmedLoadError")}
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
          <Package className="h-12 w-12 text-[var(--muted)]" />
          <p className="mt-4 text-base font-semibold text-[var(--ink)]">
            {t("unconfirmedEmptyTitle")}
          </p>
          <p className="mt-1 text-sm text-[var(--muted-2)]">{t("unconfirmedEmptyHint")}</p>
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
                <CrmUnconfirmedOrderRow key={order.id} order={order} />
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function CrmUnconfirmedOrderRow({ order }: { order: CrmOrder }) {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();
  const thumb = order.images[0];
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const deleteMutation = useDeleteCrmOrder();
  const tone = crmOrderStatusTone(order.status);

  return (
    <div
      className={cn(
        "flex min-w-0 items-center gap-1.5 rounded-xl border px-1.5 py-1.5 shadow-sm md:gap-3 md:rounded-2xl md:px-3 md:py-2",
        tone.card,
      )}
    >
      <Link
        href={`/crm?date=${order.date}&order=${order.id}`}
        className="flex min-w-0 flex-1 items-center gap-1.5 md:gap-3"
      >
        <div
          className={cn(
            "h-8 w-8 shrink-0 overflow-hidden rounded-md border md:h-12 md:w-12 md:rounded-lg",
            tone.media,
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
              <CrmOrderTimeSlot
                timeStart={order.time_start}
                timeEnd={order.time_end}
                whenReady={order.when_ready}
                layout="month"
              />
            </div>
            <span className="shrink-0 text-[10px] font-medium text-[var(--muted-2)]">
              #{order.id}
            </span>
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
                tone.chip,
              )}
            >
              {t(CRM_ORDER_STATUS_MESSAGE_KEYS[order.status])}
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
      </Link>

      {currentUser.data?.is_staff ? (
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
      ) : null}
      {currentUser.data?.is_staff ? (
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
      ) : null}
      <CrmOrderActionsMenu
        orderId={order.id}
        clientToken={order.client_token}
        onDelete={
          currentUser.data?.is_staff
            ? () => {
                deleteMutation.reset();
                setIsDeleteOpen(true);
              }
            : null
        }
      />
    </div>
  );
}
