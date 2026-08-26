"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import {
  AtSign,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  Pencil,
  Plus,
  Store,
  Truck,
  User,
  ZoomIn,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { Link, useRouter } from "@/i18n/navigation";
import { useCrmOrders, usePatchCrmOrder } from "@/hooks/useCrmOrders";
import type { CrmOrder } from "@/lib/api/types";
import { formatAed, getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

function shiftDate(isoDate: string, days: number): string {
  const [yearStr, monthStr, dayStr] = isoDate.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  const nextDay = String(date.getUTCDate()).padStart(2, "0");
  return `${nextYear}-${nextMonth}-${nextDay}`;
}

export default function CrmPage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-[40vh] items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <CrmBoard />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function CrmBoard() {
  const t = useTranslations("crm");
  const router = useRouter();
  const searchParams = useSearchParams();
  const todayStr = getTbilisiTodayIsoDate();
  const selectedDate = searchParams.get("date") ?? todayStr;

  const setSelectedDate = (next: string) => {
    router.replace(`/crm?date=${next}`);
  };

  const ordersQuery = useCrmOrders(selectedDate);
  const patchMutation = usePatchCrmOrder();

  const orders = ordersQuery.data?.orders ?? [];
  const isToday = selectedDate === todayStr;

  const deliveredCount = orders.filter((o) => o.is_delivered).length;
  const paidCount = orders.filter((o) => o.is_paid).length;

  return (
    <div className="grid gap-6">
      <div className="flex justify-end">
        <Button asChild>
          <Link href={`/crm/new?date=${selectedDate}`}>
            <Plus className="mr-1.5 h-4 w-4" />
            {t("createOrder")}
          </Link>
        </Button>
      </div>
      <div className="rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}
            className="flex items-center gap-1.5"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>{t("previousDay")}</span>
          </Button>

          <div className="flex w-full max-w-md flex-col items-center gap-1 text-center">
            <MondayDatePicker value={selectedDate} onChange={setSelectedDate} />
            <div className="flex items-center gap-2">
              {isToday ? (
                <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                  {t("today")}
                </span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedDate(todayStr)}
                  className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
                >
                  {t("jumpToToday")}
                </Button>
              )}
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}
            className="flex items-center gap-1.5"
          >
            <span>{t("nextDay")}</span>
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
          {t("loadError")}
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
          <Package className="h-12 w-12 text-[var(--muted)]" />
          <p className="mt-4 text-base font-semibold text-[var(--ink)]">
            {t("emptyTitle")}
          </p>
          <p className="mt-1 text-sm text-[var(--muted-2)]">
            {t("emptyHint")}
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {orders.map((order) => (
            <CrmOrderCard
              key={order.id}
              order={order}
              isPatching={patchMutation.isPending && patchMutation.variables?.id === order.id}
              onToggleDelivered={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { is_delivered: !order.is_delivered },
                })
              }
              onTogglePaid={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { is_paid: !order.is_paid },
                })
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimeSlot(start: string, end: string | null): string {
  const s = start.slice(0, 5);
  if (!end) return s;
  return `${s} – ${end.slice(0, 5)}`;
}

function paymentTypeLabel(type: string, t: (key: string) => string): string {
  if (type === "unknown") return t("paymentUnknown");
  if (type === "cash") return t("paymentCash");
  if (type === "terminal") return t("paymentTerminal");
  if (type === "tbc") return t("paymentTbc");
  if (type === "bog") return t("paymentBog");
  return type;
}

function CrmOrderCard({
  order,
  isPatching,
  onToggleDelivered,
  onTogglePaid,
}: {
  order: CrmOrder;
  isPatching: boolean;
  onToggleDelivered: () => void;
  onTogglePaid: () => void;
}) {
  const t = useTranslations("crm");
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const images = order.images;
  const activeImage = images[activeImageIndex] ?? images[0];

  const priceNum = Number.parseFloat(order.cake_price);
  const prepayNum = Number.parseFloat(order.prepayment);
  const remainingNum = Math.max(0, priceNum - prepayNum);

  return (
    <div
      className={cn(
        "rounded-3xl border p-6 shadow-sm transition-colors md:p-8",
        order.is_delivered
          ? "border-sky-200 bg-sky-50/70"
          : "border-[var(--line)] bg-white",
      )}
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-8">
        <div className="flex flex-col gap-3 lg:col-span-5">
          <div
            className={cn(
              "relative aspect-square w-full overflow-hidden rounded-2xl border",
              order.is_delivered
                ? "border-sky-200 bg-white"
                : "border-[var(--line)] bg-[var(--cream)]",
            )}
          >
            {activeImage ? (
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="group relative h-full w-full cursor-pointer focus:outline-none"
                title={t("enlargeTitle")}
              >
                <img
                  src={activeImage.image.src}
                  srcSet={activeImage.image.srcset}
                  sizes="(max-width: 1024px) 100vw, 40vw"
                  alt={t("orderAlt", { id: order.id })}
                  className="h-full w-full object-contain transition-transform duration-200 group-hover:scale-[1.02]"
                  loading="lazy"
                />
                <span className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  <ZoomIn className="h-4 w-4" />
                </span>
              </button>
            ) : (
              <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-[var(--muted-2)]">
                <Package className="h-10 w-10 text-[var(--muted)]" />
                <span className="text-sm">{t("noImage")}</span>
              </div>
            )}
          </div>

          {images.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {images.map((img, idx) => (
                <button
                  type="button"
                  key={img.id}
                  onClick={() => setActiveImageIndex(idx)}
                  className={cn(
                    "relative h-16 w-16 overflow-hidden rounded-xl border-2 transition-all",
                    order.is_delivered ? "bg-white" : "bg-[var(--cream)]",
                    activeImageIndex === idx
                      ? "border-[var(--brand)] ring-2 ring-[var(--brand)]/30"
                      : "border-[var(--line)] opacity-70 hover:opacity-100",
                  )}
                >
                  <img
                    src={img.image.src}
                    srcSet={img.image.srcset}
                    sizes="64px"
                    alt={t("thumbAlt", { n: idx + 1 })}
                    className="h-full w-full object-contain"
                  />
                </button>
              ))}
            </div>
          ) : null}

          {activeImage ? (
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogContent className="max-w-4xl p-4 md:p-6">
                <VisuallyHidden.Root asChild>
                  <DialogTitle>{t("orderImageTitle", { id: order.id })}</DialogTitle>
                </VisuallyHidden.Root>
                <div className="flex flex-col items-center gap-4">
                  <div className="relative flex max-h-[75vh] w-full items-center justify-center overflow-hidden rounded-2xl bg-[var(--cream)] p-2">
                    <img
                      src={activeImage.image.src}
                      srcSet={activeImage.image.srcset}
                      sizes="(max-width: 1024px) 95vw, 80vw"
                      alt={t("orderAlt", { id: order.id })}
                      className="max-h-[72vh] w-auto max-w-full object-contain"
                    />
                  </div>
                  {images.length > 1 ? (
                    <div className="flex flex-wrap justify-center gap-2">
                      {images.map((img, idx) => (
                        <button
                          type="button"
                          key={img.id}
                          onClick={() => setActiveImageIndex(idx)}
                          className={cn(
                            "relative h-16 w-16 overflow-hidden rounded-xl border-2 bg-[var(--cream)] transition-all",
                            activeImageIndex === idx
                              ? "border-[var(--brand)] ring-2 ring-[var(--brand)]/30"
                              : "border-[var(--line)] opacity-70 hover:opacity-100",
                          )}
                        >
                          <img
                            src={img.image.src}
                            srcSet={img.image.srcset}
                            sizes="64px"
                            alt={t("thumbAlt", { n: idx + 1 })}
                            className="h-full w-full object-contain"
                          />
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </DialogContent>
            </Dialog>
          ) : null}
        </div>

        <div className="flex flex-col justify-between gap-6 lg:col-span-7">
          <div className="flex flex-col gap-4">
            <div
              className={cn(
                "flex flex-wrap items-center justify-between gap-2 border-b pb-4",
                order.is_delivered ? "border-sky-200" : "border-[var(--line)]",
              )}
            >
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-[var(--brand)]" />
                <span className="text-2xl font-bold tracking-tight text-[var(--ink)]">
                  {formatTimeSlot(order.time_start, order.time_end)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold",
                    order.fulfillment_type === "delivery"
                      ? "bg-amber-100 text-amber-900"
                      : "bg-blue-100 text-blue-900",
                  )}
                >
                  {order.fulfillment_type === "delivery" ? (
                    <>
                      <Truck className="h-3.5 w-3.5" />
                      <span>{t("delivery")}</span>
                    </>
                  ) : (
                    <>
                      <Store className="h-3.5 w-3.5" />
                      <span>{t("pickup")}</span>
                    </>
                  )}
                </span>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-medium text-[var(--ink)]",
                    order.is_delivered ? "bg-white" : "bg-[var(--cream)]",
                  )}
                >
                  #{order.id}
                </span>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/crm/${order.id}/edit`}>
                    <Pencil className="mr-1.5 h-3.5 w-3.5" />
                    {t("editOrder")}
                  </Link>
                </Button>
              </div>
            </div>

            <div
              className={cn(
                "rounded-2xl p-4 text-sm text-[var(--ink)]",
                order.is_delivered
                  ? "border border-sky-200/80 bg-white/80"
                  : "bg-[var(--cream-soft)]",
              )}
            >
              <div className="flex items-start gap-2">
                <User className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                <div>
                  <span className="font-semibold text-xs uppercase tracking-wider text-[var(--ink)]/60">
                    {t("contact")}
                  </span>
                  <p className="mt-1 whitespace-pre-wrap font-medium">{order.contact}</p>
                </div>
              </div>
            </div>

            {order.nickname ? (
              <div
                className={cn(
                  "rounded-2xl p-4 text-sm text-[var(--ink)]",
                  order.is_delivered
                    ? "border border-sky-200/80 bg-white/80"
                    : "bg-[var(--cream-soft)]",
                )}
              >
                <div className="flex items-start gap-2">
                  <AtSign className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div>
                    <span className="font-semibold text-xs uppercase tracking-wider text-[var(--ink)]/60">
                      {t("nickname")}
                    </span>
                    <p className="mt-1 whitespace-pre-wrap font-medium">{order.nickname}</p>
                  </div>
                </div>
              </div>
            ) : null}

            {order.delivery_address ? (
              <div
                className={cn(
                  "rounded-2xl p-4 text-sm text-[var(--ink)]",
                  order.is_delivered
                    ? "border border-sky-200/80 bg-white/80"
                    : "bg-[var(--cream-soft)]",
                )}
              >
                <div className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div>
                    <span className="font-semibold text-xs uppercase tracking-wider text-[var(--ink)]/60">
                      {t("deliveryAddress")}
                    </span>
                    <p className="mt-1 whitespace-pre-wrap font-medium">
                      {order.delivery_address}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div
                className={cn(
                  "rounded-2xl border p-3.5",
                  order.is_delivered
                    ? "border-sky-200/80 bg-white/70"
                    : "border-[var(--line)]",
                )}
              >
                <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  {t("weight")}
                </span>
                <p className="mt-1 font-semibold text-[var(--ink)]">{order.weight}</p>
              </div>
              <div
                className={cn(
                  "rounded-2xl border p-3.5",
                  order.is_delivered
                    ? "border-sky-200/80 bg-white/70"
                    : "border-[var(--line)]",
                )}
              >
                <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  {t("filling")}
                </span>
                <p className="mt-1 font-semibold text-[var(--ink)]">{order.filling}</p>
              </div>
            </div>

            {order.description ? (
              <div
                className={cn(
                  "rounded-2xl border p-3.5",
                  order.is_delivered
                    ? "border-sky-200/80 bg-white/70"
                    : "border-[var(--line)]",
                )}
              >
                <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-[var(--muted-2)]">
                  <FileText className="h-3.5 w-3.5" />
                  <span>{t("notes")}</span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-sm text-[var(--ink)]">
                  {order.description}
                </p>
              </div>
            ) : null}

            <div
              className={cn(
                "grid grid-cols-2 gap-3 rounded-2xl p-4 sm:grid-cols-4",
                order.is_delivered
                  ? "border border-sky-200/80 bg-white/80"
                  : "bg-[var(--cream-soft)]",
              )}
            >
              <div>
                <span className="text-xs text-[var(--muted-2)]">{t("price")}</span>
                <p className="mt-0.5 text-base font-bold text-[var(--ink)]">
                  {formatAed(order.cake_price)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">{t("prepaid")}</span>
                <p className="mt-0.5 text-base font-semibold text-[var(--ink)]">
                  {formatAed(order.prepayment)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">{t("remaining")}</span>
                <p
                  className={cn(
                    "mt-0.5 text-base font-bold",
                    remainingNum > 0 ? "text-[var(--danger)]" : "text-emerald-700",
                  )}
                >
                  {formatAed(remainingNum)}
                </p>
              </div>
              <div>
                <span className="text-xs text-[var(--muted-2)]">{t("paymentMethod")}</span>
                <p className="mt-0.5 text-sm font-semibold text-[var(--ink)]">
                  {paymentTypeLabel(order.payment_type, t)}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-2">
            <Button
              type="button"
              size="lg"
              onClick={onToggleDelivered}
              disabled={isPatching}
              className={cn(
                "h-14 font-semibold transition-all",
                order.is_delivered
                  ? "bg-sky-600 text-white hover:bg-sky-700"
                  : "border-2 border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {isPatching ? (
                <Spinner className="h-5 w-5" />
              ) : order.is_delivered ? (
                <span className="flex items-center gap-2">
                  <Check className="h-5 w-5" />
                  {t("delivered")}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Truck className="h-5 w-5 text-[var(--muted-2)]" />
                  {t("markDelivered")}
                </span>
              )}
            </Button>

            <Button
              type="button"
              size="lg"
              onClick={onTogglePaid}
              disabled={isPatching}
              className={cn(
                "h-14 font-semibold transition-all",
                order.is_paid
                  ? "bg-emerald-600 text-white hover:bg-emerald-700"
                  : "border-2 border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {isPatching ? (
                <Spinner className="h-5 w-5" />
              ) : order.is_paid ? (
                <span className="flex items-center gap-2">
                  <Check className="h-5 w-5" />
                  {t("paid")}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-[var(--muted-2)]" />
                  {t("markPaid")}
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
