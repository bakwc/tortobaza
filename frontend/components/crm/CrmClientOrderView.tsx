"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import {
  AtSign,
  Check,
  Clock,
  CreditCard,
  FileText,
  MapPin,
  Package,
  Store,
  Truck,
  User,
  ZoomIn,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { CrmContactLinks } from "@/components/crm/CrmContactLinks";
import { useCrmClientOrderMap } from "@/hooks/useCrmOrders";
import { CRM_CLIENT_ORDER_STATUS_MESSAGE_KEYS, crmOrderStatusTone } from "@/lib/crmStatus";
import { SITE_INFO } from "@/lib/site-info";
import type { CrmClientOrder } from "@/lib/api/types";
import { formatAed } from "@/lib/format";
import { cn } from "@/lib/utils";

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

function formatClientDate(isoDate: string, locale: string): string {
  const d = new Date(`${isoDate}T00:00:00`);
  const tag = locale === "ka" ? "ka-GE" : locale === "ru" ? "ru-RU" : "en-GB";
  return d.toLocaleDateString(tag, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function googleMapsUrlToEmbed(url: string): string {
  const parsed = new URL(url);
  const query = parsed.searchParams.get("query");
  if (!query) {
    throw new Error("Google Maps URL is missing query");
  }
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&z=16&output=embed`;
}

export function CrmClientOrderView({
  order,
  token,
}: {
  order: CrmClientOrder;
  token: string;
}) {
  const t = useTranslations("crm");
  const locale = useLocale();
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const images = order.images;
  const activeImage = images[activeImageIndex] ?? images[0];
  const priceNum = Number.parseFloat(order.cake_price);
  const prepayNum = Number.parseFloat(order.prepayment);
  const remainingNum = Math.max(0, priceNum - prepayNum);
  const showPickupBadge =
    order.fulfillment_type === "pickup" && order.delivery_address.length < 5;
  const needsMap = Boolean(order.delivery_address) && !showPickupBadge;
  const mapQuery = useCrmClientOrderMap(token, needsMap && order.google_maps_url === null);
  const googleMapsUrl = order.google_maps_url ?? mapQuery.data?.url ?? null;
  const mapEmbed = googleMapsUrl !== null ? googleMapsUrlToEmbed(googleMapsUrl) : null;
  const statusTone = crmOrderStatusTone(order.status);

  return (
    <div className="grid gap-6">
      <div className="text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[var(--brand)]">
          {SITE_INFO.brand}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-[var(--ink)]">{t("clientPageTitle")}</h1>
        <p className="mt-1 text-lg font-semibold tabular-nums text-[var(--ink)]">
          {t("clientOrderNumber", { id: order.id })}
        </p>
        <span
          className={cn(
            "mt-2 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
            statusTone.chip,
          )}
        >
          {t(CRM_CLIENT_ORDER_STATUS_MESSAGE_KEYS[order.status])}
        </span>
      </div>
      <div className="rounded-2xl border border-[var(--line)] bg-white p-3 shadow-sm sm:p-4 md:rounded-3xl md:p-8">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-12 lg:gap-8">
          <div className="flex flex-col gap-2 lg:col-span-5 lg:gap-3">
            <div className="relative mx-auto aspect-square w-full max-w-44 overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--cream)] sm:max-w-56 lg:max-w-none lg:rounded-2xl">
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
                      "relative h-11 w-11 overflow-hidden rounded-lg border-2 bg-[var(--cream)] transition-all lg:h-16 lg:w-16 lg:rounded-xl",
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

          <div className="flex flex-col gap-2.5 lg:col-span-7 lg:gap-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-2.5 lg:pb-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-sm text-[var(--muted-2)]">
                  {formatClientDate(order.date, locale)}
                </span>
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
              </div>
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
            </div>

            <div className="rounded-xl bg-[var(--cream-soft)] p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4">
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
              <div className="rounded-xl bg-[var(--cream-soft)] p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4">
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

            {showPickupBadge ? (
              <div className="rounded-xl bg-[var(--cream-soft)] p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4">
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
              <div className="w-full rounded-xl bg-[var(--cream-soft)] p-2.5 text-sm text-[var(--ink)] lg:rounded-2xl lg:p-4">
                <div className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold text-[10px] uppercase tracking-wider text-[var(--ink)]/60 lg:text-xs">
                      {t("deliveryAddress")}
                    </span>
                    <p className="mt-0.5 whitespace-pre-wrap font-medium lg:mt-1">
                      {order.delivery_address}
                    </p>
                    {mapEmbed ? (
                      <div className="mt-3 overflow-hidden rounded-xl border border-[var(--line)]">
                        <iframe
                          title={t("clientMapTitle")}
                          src={mapEmbed}
                          loading="lazy"
                          referrerPolicy="no-referrer"
                          className="h-[280px] w-full md:h-[360px]"
                          style={{ border: 0 }}
                        />
                      </div>
                    ) : (
                      <div className="mt-3 flex h-[280px] w-full items-center justify-center overflow-hidden rounded-xl border border-[var(--line)] bg-white md:h-[360px]">
                        <Spinner className="h-8 w-8 text-[var(--brand)]" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-2 lg:gap-3">
              <div className="rounded-xl border border-[var(--line)] p-2.5 lg:rounded-2xl lg:p-3.5">
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  {t("weight")}
                </span>
                <p className="mt-0.5 font-semibold text-[var(--ink)] lg:mt-1">{order.weight}</p>
              </div>
              <div className="rounded-xl border border-[var(--line)] p-2.5 lg:rounded-2xl lg:p-3.5">
                <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  {t("filling")}
                </span>
                <p className="mt-0.5 font-semibold text-[var(--ink)] lg:mt-1">{order.filling}</p>
              </div>
            </div>

            {order.description ? (
              <div className="rounded-xl border border-[var(--line)] p-2.5 lg:rounded-2xl lg:p-3.5">
                <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                  <FileText className="h-3.5 w-3.5" />
                  <span>{t("notes")}</span>
                </div>
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-[var(--ink)] lg:mt-1">
                  {order.description}
                </p>
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-2 rounded-xl bg-[var(--cream-soft)] p-2.5 sm:grid-cols-4 lg:gap-3 lg:rounded-2xl lg:p-4">
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

            <div className="flex flex-wrap items-center gap-1.5 lg:gap-2">
              <span
                className={cn(
                  "flex cursor-default items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold",
                  order.is_paid
                    ? "bg-emerald-600 text-white"
                    : "border border-[var(--line)] bg-white text-[var(--muted-2)]",
                )}
              >
                {order.is_paid ? <Check className="h-3.5 w-3.5" /> : <CreditCard className="h-3.5 w-3.5" />}
                {order.is_paid ? t("paid") : t("notPaid")}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
