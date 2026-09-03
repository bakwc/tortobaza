"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import {
  AtSign,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  PackageCheck,
  Pencil,
  Plus,
  Store,
  ThumbsUp,
  Truck,
  User,
  Utensils,
  ZoomIn,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmContactLinks } from "@/components/crm/CrmContactLinks";
import { CrmDeleteOrderDialog } from "@/components/crm/CrmDeleteOrderDialog";
import { CrmIncomeStats } from "@/components/crm/CrmIncomeStats";
import { CrmOrderActionsMenu } from "@/components/crm/CrmOrderActionsMenu";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { Link, useRouter } from "@/i18n/navigation";
import { useCurrentUser } from "@/hooks/useAuth";
import {
  useCrmOrders,
  useDeleteCrmOrder,
  usePatchCrmOrder,
  useResolveGoogleAddress,
  useResolveYandexAddress,
} from "@/hooks/useCrmOrders";
import { GoogleMapsIcon, YandexMapsIcon } from "@/content/contacts/icons";
import type { CrmOrder, CrmOrderStatus } from "@/lib/api/types";
import {
  CRM_ORDER_NEXT_STATUS,
  CRM_ORDER_NEXT_STEP_MESSAGE_KEYS,
  CRM_ORDER_STATUS_MESSAGE_KEYS,
  CRM_ORDER_STATUSES,
  crmOrderStatusTone,
} from "@/lib/crmStatus";
import { formatAed, getTbilisiTodayIsoDate, sortCrmBoardOrders } from "@/lib/format";
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
  const currentUser = useCurrentUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  const todayStr = getTbilisiTodayIsoDate();
  const selectedDate = searchParams.get("date") ?? todayStr;
  const focusedOrderId = searchParams.get("order");

  const setSelectedDate = (next: string) => {
    router.replace(`/crm?date=${next}`);
  };

  const ordersQuery = useCrmOrders(selectedDate);
  const patchMutation = usePatchCrmOrder();

  const orders = sortCrmBoardOrders(ordersQuery.data?.orders ?? []);
  const isToday = selectedDate === todayStr;

  useEffect(() => {
    if (!focusedOrderId || ordersQuery.isLoading) {
      return;
    }
    const el = document.getElementById(`crm-order-${focusedOrderId}`);
    if (!el) {
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusedOrderId, ordersQuery.isLoading, orders.length]);

  const deliveredCount = orders.filter((o) => o.status === "delivered").length;
  const paidCount = orders.filter((o) => o.is_paid).length;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild variant="outline">
          <Link href="/crm/month">{t("monthlyOrders")}</Link>
        </Button>
        {currentUser.data?.is_staff ? (
          <Button asChild>
            <Link href={`/crm/new?date=${selectedDate}`}>
              <Plus className="mr-1.5 h-4 w-4" />
              {t("createOrder")}
            </Link>
          </Button>
        ) : null}
        <CrmOverflowMenu />
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
        <CrmIncomeStats orders={orders} compact={false} />
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
        <div className="grid gap-3 md:gap-6">
          {orders.map((order) => (
            <CrmOrderCard
              key={order.id}
              order={order}
              focused={focusedOrderId === String(order.id)}
              isPatching={patchMutation.isPending && patchMutation.variables?.id === order.id}
              onSetStatus={(status) =>
                patchMutation.mutate({
                  id: order.id,
                  body: { status },
                })
              }
              onTogglePaid={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { is_paid: !order.is_paid },
                })
              }
              onTakeInWork={() =>
                patchMutation.mutate({
                  id: order.id,
                  body: { take_in_work: true },
                })
              }
            />
          ))}
        </div>
      )}
    </div>
  );
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

function paymentTypeLabel(type: string, t: (key: string) => string): string {
  if (type === "unknown") return t("paymentUnknown");
  if (type === "cash") return t("paymentCash");
  if (type === "terminal") return t("paymentTerminal");
  if (type === "tbc") return t("paymentTbc");
  if (type === "bog") return t("paymentBog");
  if (type === "flowwow") return t("paymentFlowwow");
  if (type === "crypto") return t("paymentCrypto");
  if (type === "online") return t("paymentOnline");
  return type;
}

const NEXT_STEP_ICONS = {
  in_work: Utensils,
  client_approved: ThumbsUp,
  in_delivery: Truck,
  delivered: PackageCheck,
} as const;

function CrmOrderStatusMenu({
  order,
  isPatching,
  onSetStatus,
  onTogglePaid,
}: {
  order: CrmOrder;
  isPatching: boolean;
  onSetStatus: (status: CrmOrderStatus) => void;
  onTogglePaid: () => void;
}) {
  const t = useTranslations("crm");
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="lg"
        onClick={() => setOpen((prev) => !prev)}
        disabled={isPatching}
        aria-label={t("statusMenu")}
        aria-expanded={open}
        className="h-11 w-11 shrink-0 px-0 lg:h-14 lg:w-14"
      >
        <ChevronDown className="h-4 w-4 lg:h-5 lg:w-5" />
      </Button>
      {open ? (
        <div className="absolute bottom-full right-0 z-20 mb-2 min-w-[220px] rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg">
          {CRM_ORDER_STATUSES.map((status) => (
            <button
              key={status}
              type="button"
              disabled={status === order.status}
              onClick={() => {
                setOpen(false);
                onSetStatus(status);
              }}
              className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)] disabled:pointer-events-none"
            >
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-2.5 w-2.5 rounded-full border border-[var(--line)]",
                    crmOrderStatusTone(status).chip,
                  )}
                />
                {t(CRM_ORDER_STATUS_MESSAGE_KEYS[status])}
              </span>
              {status === order.status ? (
                <Check className="h-4 w-4 text-[var(--brand)]" />
              ) : null}
            </button>
          ))}
          <div className="my-1 border-t border-[var(--line)]" />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onTogglePaid();
            }}
            className={cn(
              "flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium hover:bg-[var(--cream)]",
              order.is_paid ? "bg-emerald-600 text-white hover:bg-emerald-700" : "text-[var(--ink)]",
            )}
          >
            {order.is_paid ? (
              <Check className="h-4 w-4" />
            ) : (
              <CreditCard className="h-4 w-4" />
            )}
            {t("markPaid")}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function CrmOrderCard({
  order,
  focused,
  isPatching,
  onSetStatus,
  onTogglePaid,
  onTakeInWork,
}: {
  order: CrmOrder;
  focused: boolean;
  isPatching: boolean;
  onSetStatus: (status: CrmOrderStatus) => void;
  onTogglePaid: () => void;
  onTakeInWork: () => void;
}) {
  const t = useTranslations("crm");
  const currentUser = useCurrentUser();
  const tone = crmOrderStatusTone(order.status);
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState<boolean>(false);
  const deleteMutation = useDeleteCrmOrder();
  const resolveYandex = useResolveYandexAddress();
  const resolveGoogle = useResolveGoogleAddress();
  const [resolvingTarget, setResolvingTarget] = useState<"address" | "yandex" | "google" | null>(
    null,
  );

  const images = order.images;
  const activeImage = images[activeImageIndex] ?? images[0];

  const priceNum = Number.parseFloat(order.cake_price);
  const prepayNum = Number.parseFloat(order.prepayment);
  const remainingNum = Math.max(0, priceNum - prepayNum);

  const nextStatus = CRM_ORDER_NEXT_STATUS[order.status];
  const NextStepIcon = nextStatus ? NEXT_STEP_ICONS[nextStatus] : null;

  return (
    <div
      id={`crm-order-${order.id}`}
      className={cn(
        "rounded-2xl border p-3 shadow-sm transition-colors sm:p-4 md:rounded-3xl md:p-8",
        tone.card,
        focused && "ring-2 ring-[var(--brand)] ring-offset-2",
      )}
    >
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-12 lg:gap-8">
        <div className="flex flex-col gap-2 lg:col-span-5 lg:gap-3">
          <div
            className={cn(
              "relative mx-auto aspect-square w-full max-w-44 overflow-hidden rounded-xl border sm:max-w-56 lg:max-w-none lg:rounded-2xl",
              tone.media,
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
                  sizes="(max-width: 1024px) 224px, 40vw"
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
                <Package className="h-7 w-7 text-[var(--muted)] lg:h-10 lg:w-10" />
                <span className="text-xs lg:text-sm">{t("noImage")}</span>
              </div>
            )}
          </div>

          {images.length > 1 ? (
            <div className="flex flex-wrap justify-center gap-1.5 lg:justify-start lg:gap-2">
              {images.map((img, idx) => (
                <button
                  type="button"
                  key={img.id}
                  onClick={() => setActiveImageIndex(idx)}
                  className={cn(
                    "relative h-11 w-11 overflow-hidden rounded-lg border-2 transition-all lg:h-16 lg:w-16 lg:rounded-xl",
                    order.status === "new" ? "bg-[var(--cream)]" : "bg-white",
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

        <div className="flex flex-col justify-between gap-3 lg:col-span-7 lg:gap-6">
          <div className="flex flex-col gap-2.5 lg:gap-4">
            <div
              className={cn(
                "flex flex-wrap items-center justify-between gap-2 border-b pb-2.5 lg:pb-4",
                tone.divider,
              )}
            >
              <div className="flex items-center gap-1.5 lg:gap-2">
                <Clock className="h-4 w-4 text-[var(--brand)] lg:h-5 lg:w-5" />
                <span className="text-lg font-bold tracking-tight text-[var(--ink)] lg:text-2xl">
                  {formatTimeSlot(
                    order.time_start,
                    order.time_end,
                    order.when_ready,
                    t("timeUnknown"),
                    t("timeWhenReady"),
                  )}
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
                <Link
                  href={`/crm?date=${order.date}&order=${order.id}`}
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-medium text-[var(--ink)] underline-offset-2 hover:underline",
                    order.status === "new" ? "bg-[var(--cream)]" : "bg-white",
                  )}
                >
                  #{order.id}
                </Link>
                {currentUser.data?.is_staff ? (
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/crm/${order.id}/edit`}>
                      <Pencil className="mr-1.5 h-3.5 w-3.5" />
                      {t("editOrder")}
                    </Link>
                  </Button>
                ) : null}
                {currentUser.data?.is_staff ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-[var(--danger)] hover:bg-red-50"
                    onClick={() => {
                      deleteMutation.reset();
                      setIsDeleteOpen(true);
                    }}
                  >
                    {t("deleteOrder")}
                  </Button>
                ) : null}
                <CrmOrderActionsMenu orderId={order.id} />
              </div>
            </div>

            <div
              className={cn(
                "rounded-xl p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4",
                tone.panelSoft,
              )}
            >
              <div className="flex items-start gap-2">
                <User className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                <div className="min-w-0 flex-1">
                  <span className="font-semibold text-[10px] uppercase tracking-wider text-[var(--ink)]/60 lg:text-xs">
                    {t("contact")}
                  </span>
                  <div className="mt-0.5 flex items-start justify-between gap-3 lg:mt-1">
                    <p className="min-w-0 whitespace-pre-wrap font-medium">{order.contact}</p>
                    <CrmContactLinks
                      tel={order.contact_tel}
                      whatsapp={order.contact_whatsapp}
                      telegram={order.contact_telegram}
                    />
                  </div>
                </div>
              </div>
            </div>

            {order.nickname ? (
              <div
                className={cn(
                  "rounded-xl p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4",
                  tone.panelSoft,
                )}
              >
                <div className="flex items-start gap-2">
                  <AtSign className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div>
                    <span className="font-semibold text-[10px] uppercase tracking-wider text-[var(--ink)]/60 lg:text-xs">
                      {t("nickname")}
                    </span>
                    <p className="mt-0.5 whitespace-pre-wrap font-medium lg:mt-1">{order.nickname}</p>
                  </div>
                </div>
              </div>
            ) : null}

            {order.fulfillment_type === "pickup" && order.delivery_address.length < 5 ? (
              <div
                className={cn(
                  "rounded-xl p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4",
                  tone.panelSoft,
                )}
              >
                <div className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div>
                    <span className="font-semibold text-[10px] uppercase tracking-wider text-[var(--ink)]/60 lg:text-xs">
                      {t("deliveryAddress")}
                    </span>
                    <div className="mt-0.5 lg:mt-1">
                      <span className="flex w-fit items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-900">
                        <Store className="h-3.5 w-3.5" />
                        <span>{t("pickup")}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : order.delivery_address ? (
              <div
                className={cn(
                  "w-full rounded-xl p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4",
                  tone.panelSoft,
                )}
              >
                <div className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold text-[10px] uppercase tracking-wider text-[var(--ink)]/60 lg:text-xs">
                      {t("deliveryAddress")}
                    </span>
                    <div className="mt-0.5 flex items-start gap-2 lg:mt-1">
                      {resolvingTarget === "address" && resolveYandex.isPending ? (
                        <p className="flex min-w-0 flex-1 items-center gap-2 font-medium">
                          <Spinner className="h-4 w-4 text-[var(--brand)]" />
                          {t("resolvingAddress")}
                        </p>
                      ) : (
                        <button
                          type="button"
                          disabled={resolveYandex.isPending || resolveGoogle.isPending}
                          onClick={() => {
                            if (resolveYandex.isPending || resolveGoogle.isPending) return;
                            setResolvingTarget("address");
                            resolveYandex.mutate(order.delivery_address, {
                              onSuccess: (data) => {
                                window.open(data.url, "_blank", "noopener,noreferrer");
                              },
                              onSettled: () => setResolvingTarget(null),
                            });
                          }}
                          className="min-w-0 flex-1 cursor-pointer whitespace-pre-wrap text-left font-medium"
                        >
                          {order.delivery_address}
                        </button>
                      )}
                      <span className="flex shrink-0 items-center gap-1.5">
                        <button
                          type="button"
                          disabled={resolveYandex.isPending || resolveGoogle.isPending}
                          aria-label={t("openYandexMaps")}
                          onClick={() => {
                            if (resolveYandex.isPending || resolveGoogle.isPending) return;
                            setResolvingTarget("yandex");
                            resolveYandex.mutate(order.delivery_address, {
                              onSuccess: (data) => {
                                window.open(data.url, "_blank", "noopener,noreferrer");
                              },
                              onSettled: () => setResolvingTarget(null),
                            });
                          }}
                          className="text-[var(--brand)] hover:opacity-80 disabled:opacity-50"
                        >
                          {resolvingTarget === "yandex" && resolveYandex.isPending ? (
                            <Spinner className="h-6 w-6 text-[var(--brand)]" />
                          ) : (
                            <YandexMapsIcon className="h-6 w-6" />
                          )}
                        </button>
                        <button
                          type="button"
                          disabled={resolveYandex.isPending || resolveGoogle.isPending}
                          aria-label={t("openGoogleMaps")}
                          onClick={() => {
                            if (resolveYandex.isPending || resolveGoogle.isPending) return;
                            setResolvingTarget("google");
                            resolveGoogle.mutate(order.delivery_address, {
                              onSuccess: (data) => {
                                window.open(data.url, "_blank", "noopener,noreferrer");
                              },
                              onSettled: () => setResolvingTarget(null),
                            });
                          }}
                          className="text-[var(--brand)] hover:opacity-80 disabled:opacity-50"
                        >
                          {resolvingTarget === "google" && resolveGoogle.isPending ? (
                            <Spinner className="h-6 w-6 text-[var(--brand)]" />
                          ) : (
                            <GoogleMapsIcon className="h-6 w-6" />
                          )}
                        </button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-2 lg:gap-3">
              <div
                className={cn(
                  "rounded-xl border p-2.5 lg:rounded-2xl lg:p-3.5",
                  tone.panel,
                )}
              >
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  {t("weight")}
                </span>
                <p className="mt-0.5 font-semibold text-[var(--ink)] lg:mt-1">{order.weight}</p>
              </div>
              <div
                className={cn(
                  "rounded-xl border p-2.5 lg:rounded-2xl lg:p-3.5",
                  tone.panel,
                )}
              >
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  {t("filling")}
                </span>
                <p className="mt-0.5 font-semibold text-[var(--ink)] lg:mt-1">{order.filling}</p>
              </div>
            </div>

            {order.description ? (
              <div
                className={cn(
                  "rounded-xl border p-2.5 lg:rounded-2xl lg:p-3.5",
                  tone.panel,
                )}
              >
                <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  <FileText className="h-3.5 w-3.5" />
                  <span>{t("notes")}</span>
                </div>
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-[var(--ink)] lg:mt-1">
                  {order.description}
                </p>
              </div>
            ) : null}

            <div
              className={cn(
                "grid grid-cols-2 gap-2 rounded-xl p-2.5 sm:grid-cols-4 lg:gap-3 lg:rounded-2xl lg:p-4",
                tone.panelSoft,
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

          <div className="flex flex-col gap-2 pt-1 sm:gap-3 lg:pt-2">
            <div className="flex flex-wrap items-center gap-1.5 lg:gap-2">
              <span
                className={cn(
                  "flex items-center rounded-full px-3 py-1 text-xs font-semibold",
                  tone.chip,
                )}
              >
                {t(CRM_ORDER_STATUS_MESSAGE_KEYS[order.status])}
              </span>
              {order.taken_by_name ? (
                <span className="flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                  <Utensils className="h-3.5 w-3.5" />
                  {order.taken_by_telegram_url ? (
                    <a
                      href={order.taken_by_telegram_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-2"
                    >
                      @{order.taken_by_name}
                    </a>
                  ) : (
                    <span>{order.taken_by_name}</span>
                  )}
                </span>
              ) : null}
              <button
                type="button"
                onClick={onTogglePaid}
                disabled={isPatching}
                className={cn(
                  "flex cursor-pointer items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition-colors disabled:pointer-events-none disabled:opacity-60",
                  order.is_paid
                    ? "bg-emerald-600 text-white hover:bg-emerald-700"
                    : "border border-[var(--line)] bg-white text-[var(--muted-2)] hover:bg-[var(--cream-soft)]",
                )}
              >
                {order.is_paid ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <CreditCard className="h-3.5 w-3.5" />
                )}
                {order.is_paid ? t("paid") : t("notPaid")}
              </button>
              {isPatching ? <Spinner className="h-4 w-4 text-[var(--brand)]" /> : null}
            </div>
            <div className="flex items-stretch justify-end gap-2 sm:gap-3">
              {nextStatus && NextStepIcon ? (
                <Button
                  type="button"
                  size="lg"
                  onClick={() => {
                    if (nextStatus === "in_work") {
                      onTakeInWork();
                    } else {
                      onSetStatus(nextStatus);
                    }
                  }}
                  disabled={isPatching}
                  className="h-11 flex-1 px-2 font-semibold whitespace-normal leading-tight lg:h-14 lg:px-8 lg:whitespace-nowrap"
                >
                  {isPatching ? (
                    <Spinner className="h-5 w-5" />
                  ) : (
                    <span className="flex items-center gap-1 text-xs lg:gap-2 lg:text-sm">
                      <NextStepIcon className="h-4 w-4 lg:h-5 lg:w-5" />
                      {t(CRM_ORDER_NEXT_STEP_MESSAGE_KEYS[nextStatus])}
                    </span>
                  )}
                </Button>
              ) : null}
              <CrmOrderStatusMenu
                order={order}
                isPatching={isPatching}
                onSetStatus={onSetStatus}
                onTogglePaid={onTogglePaid}
              />
            </div>
          </div>
        </div>
      </div>
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
    </div>
  );
}
