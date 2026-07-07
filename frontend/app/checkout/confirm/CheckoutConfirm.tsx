"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Building2, CreditCard, Wallet } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { OrderSummary } from "@/components/checkout/OrderSummary";
import { TimeslotPicker } from "@/components/checkout/TimeslotPicker";
import { PromoCodeBox } from "@/components/checkout/PromoCodeBox";
import {
  clearDraft,
  emptyDraft,
  loadDraft,
  saveDraft,
  type CheckoutDraft,
} from "@/lib/checkout-draft";
import { rememberOrder } from "@/lib/order-history";
import { submitLibertyPaymentForm } from "@/lib/liberty-pay";
import type { Order, PlaceOrderBody } from "@/lib/api/types";

const BANK_ACCOUNT_NUMBER = "GE94BG0000000612361573GEL";
const BANK_RECIPIENT_NAME = "SWEET CHILL";

export function CheckoutConfirm() {
  const locale = useLocale();
  const t = useTranslations("checkout");
  const router = useRouter();
  const [draft, setDraft] = useState<CheckoutDraft>(emptyDraft);
  const [hydrated, setHydrated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bankTransferStep, setBankTransferStep] = useState(false);

  useEffect(() => {
    const loaded = loadDraft();
    if (
      loaded.fulfillment_type === "delivery" &&
      !loaded.address
    ) {
      router.replace("/checkout");
      return;
    }
    if (
      loaded.fulfillment_type === "pickup" &&
      !loaded.pickup_location_id
    ) {
      router.replace("/checkout");
      return;
    }
    setDraft(loaded);
    setHydrated(true);
  }, [router]);

  const update = (patch: Partial<CheckoutDraft>) => {
    setDraft((prev) => {
      const next = { ...prev, ...patch };
      saveDraft(next);
      return next;
    });
  };

  const placeOrder = useMutation({
    mutationFn: (body: PlaceOrderBody) => api.placeOrder(body),
    onSuccess: async (order: Order) => {
      rememberOrder(order.number, order.lookup_token);
      clearDraft();
      if (order.payment_method === "card") {
        const payment = await api.startLibertyPayment({
          number: order.number,
          token: order.lookup_token,
        });
        submitLibertyPaymentForm(payment);
        return;
      }
      router.push(`/orders/${order.number}?token=${order.lookup_token}`);
    },
    onError: (e) => {
      let message = t("genericPlaceError");
      if (e instanceof ApiError) {
        const parsed = e.parsed<Record<string, unknown>>();
        if (parsed) {
          const flat = Object.values(parsed).flat();
          if (flat.length > 0) message = String(flat[0]);
        } else if (e.detail) {
          message = e.detail;
        }
      }
      setError(message);
    },
  });

  const canPlace = useMemo(() => {
    if (!draft.schedule) return false;
    if (!draft.schedule.date || !draft.schedule.start_time || !draft.schedule.end_time) {
      return false;
    }
    if (!draft.customer_name.trim()) return false;
    if (!draft.customer_phone.trim()) return false;
    return true;
  }, [draft]);

  const handlePlaceOrder = () => {
    setError(null);
    if (!canPlace || !draft.schedule) {
      setError(t("fillContactsAndSlot"));
      return;
    }
    if (draft.payment_method === "bank_transfer" && !bankTransferStep) {
      setBankTransferStep(true);
      return;
    }
    const sch = draft.schedule;
    const body: PlaceOrderBody = {
      fulfillment_type: draft.fulfillment_type,
      schedule_mode: "slot",
      schedule_date: sch.date,
      schedule_start_time: sch.start_time,
      schedule_end_time: sch.end_time,
      locale,
      payment_method: draft.payment_method,
      customer_name: draft.customer_name.trim(),
      customer_phone: draft.customer_phone.trim(),
      ...(draft.customer_email.trim()
        ? { customer_email: draft.customer_email.trim() }
        : {}),
      ...(draft.customer_instagram.trim()
        ? { customer_instagram: draft.customer_instagram.trim() }
        : {}),
      ...(draft.customer_telegram.trim()
        ? { customer_telegram: draft.customer_telegram.trim() }
        : {}),
      comment: draft.comment.trim(),
      promo_code: draft.promo_code || undefined,
      ...(draft.fulfillment_type === "delivery" && draft.address
        ? { address: draft.address }
        : {}),
      ...(draft.fulfillment_type === "pickup" && draft.pickup_location_id
        ? { pickup_location_id: draft.pickup_location_id }
        : {}),
    };
    placeOrder.mutate(body);
  };

  const placeOrderLabel =
    draft.payment_method === "bank_transfer" && bankTransferStep ? t("confirmPayment") : t("placeOrder");

  if (!hydrated) {
    return <div className="mt-8 h-96 animate-pulse rounded-3xl bg-white/40" />;
  }

  return (
    <div className="mt-8 grid min-w-0 gap-8 lg:grid-cols-[1fr_360px]">
      <div className="min-w-0 space-y-6">
        <Section title={t("paymentMethod")}>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <PaymentTile
              icon={<CreditCard className="h-5 w-5" />}
              label={t("card")}
              active={draft.payment_method === "card"}
              onClick={() => {
                setBankTransferStep(false);
                update({ payment_method: "card" });
              }}
            />
            <PaymentTile
              icon={<Building2 className="h-5 w-5" />}
              label={t("bankTransfer")}
              active={draft.payment_method === "bank_transfer"}
              onClick={() => {
                setBankTransferStep(false);
                update({ payment_method: "bank_transfer" });
              }}
            />
            <PaymentTile
              icon={<Wallet className="h-5 w-5" />}
              label={t("cash")}
              active={draft.payment_method === "cash"}
              onClick={() => {
                setBankTransferStep(false);
                update({ payment_method: "cash" });
              }}
            />
          </div>
        </Section>

        {bankTransferStep ? (
          <Section title={t("bankTransferDetails")}>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/50">
                  {t("accountNumber")}
                </dt>
                <dd className="mt-1 font-medium tabular-nums">{BANK_ACCOUNT_NUMBER}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/50">
                  {t("recipientName")}
                </dt>
                <dd className="mt-1 font-medium">{BANK_RECIPIENT_NAME}</dd>
              </div>
            </dl>
            <p className="text-sm leading-relaxed text-[var(--ink)]/70">{t("sendTransferHint")}</p>
          </Section>
        ) : null}

        <Section
          title={draft.fulfillment_type === "delivery" ? t("deliveryTime") : t("pickupTime")}
          subtitle={t("timezoneGeorgia")}
        >
          <TimeslotPicker
            type={draft.fulfillment_type}
            value={draft.schedule}
            onChange={(schedule) => update({ schedule })}
          />
        </Section>

        <Section title={t("contactTitle")} subtitle={t("contactSubtitle")}>
          <div className="grid gap-3 sm:grid-cols-2">
            <RequiredInput
              placeholder={t("namePlaceholder")}
              value={draft.customer_name}
              onChange={(e) => update({ customer_name: e.target.value })}
            />
            <RequiredInput
              placeholder={t("phonePlaceholder")}
              value={draft.customer_phone}
              onChange={(e) => update({ customer_phone: e.target.value })}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Input
              type="email"
              placeholder={t("emailPlaceholder")}
              value={draft.customer_email}
              onChange={(e) => update({ customer_email: e.target.value })}
            />
            <Input
              placeholder={t("instagramPlaceholder")}
              value={draft.customer_instagram}
              onChange={(e) => update({ customer_instagram: e.target.value })}
            />
            <Input
              placeholder={t("telegramPlaceholder")}
              value={draft.customer_telegram}
              onChange={(e) => update({ customer_telegram: e.target.value })}
            />
          </div>
        </Section>

        {draft.fulfillment_type === "delivery" && draft.address ? (
          <Section title={t("deliverTo")}>
            <p className="text-sm leading-relaxed text-[var(--ink)]/80">
              {draft.address.building}, {draft.address.street}
              {draft.address.apartment ? `, ${draft.address.apartment}` : ""}
              <br />
              {draft.address.city}
              {draft.address.postal_code ? `, ${draft.address.postal_code}` : ""}
              {draft.address.notes ? (
                <>
                  <br />
                  <span className="italic text-[var(--ink)]/60">{draft.address.notes}</span>
                </>
              ) : null}
            </p>
            <button
              type="button"
              onClick={() => router.push("/checkout")}
              className="mt-2 text-sm text-[var(--brand)] underline-offset-2 hover:underline"
            >
              {t("changeAddress")}
            </button>
          </Section>
        ) : null}

        <Section title={t("orderComment")}>
          <Textarea
            rows={3}
            value={draft.comment}
            onChange={(e) => update({ comment: e.target.value })}
            placeholder={t("commentPlaceholder")}
          />
        </Section>

        <Section title={t("promoCodeSection")}>
          <PromoCodeBox
            value={draft.promo_code}
            onApplied={(code) => update({ promo_code: code })}
          />
        </Section>

        <p className="text-sm leading-relaxed text-[var(--ink)]/70">
          {t("termsLead")}{" "}
          <Link href="/terms" className="text-[var(--brand)] underline underline-offset-2">
            {t("termsLink")}
          </Link>{" "}
          {t("termsMiddle")}{" "}
          <Link href="/privacy" className="text-[var(--brand)] underline underline-offset-2">
            {t("privacyLink")}
          </Link>
          .
        </p>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
      </div>

      <OrderSummary
        fulfillmentType={draft.fulfillment_type}
        promoCode={draft.promo_code}
        onPlaceOrder={handlePlaceOrder}
        isPlacing={placeOrder.isPending}
        canPlace={canPlace}
        placeOrderLabel={placeOrderLabel}
      />
    </div>
  );
}

function RequiredInput(props: React.ComponentProps<typeof Input>) {
  return (
    <div className="relative">
      <Input {...props} className={cn("pr-8", props.className)} required aria-required />
      <span
        aria-hidden
        className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 text-sm text-[var(--danger)]"
      >
        *
      </span>
    </div>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
      <h2 className="font-display text-2xl">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-[var(--ink)]/60">{subtitle}</p> : null}
      <div className="mt-4 min-w-0 space-y-3">{children}</div>
    </section>
  );
}

function PaymentTile({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex h-14 items-center justify-center gap-2 rounded-2xl border text-sm transition",
        active
          ? "border-[var(--brand)] bg-[var(--brand)] text-[var(--brand-foreground)]"
          : "border-[var(--line)] bg-white text-[var(--ink)] hover:border-[var(--muted-2)]",
      )}
    >
      {icon} {label}
    </button>
  );
}
