"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CreditCard, Wallet } from "lucide-react";
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
import type { Order, PaymentMethod, PlaceOrderBody } from "@/lib/api/types";

export function CheckoutConfirm() {
  const router = useRouter();
  const [draft, setDraft] = useState<CheckoutDraft>(emptyDraft);
  const [hydrated, setHydrated] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    onSuccess: (order: Order) => {
      rememberOrder(order.number, order.lookup_token);
      clearDraft();
      router.push(`/orders/${order.number}?token=${order.lookup_token}`);
    },
    onError: (e) => {
      let message = "Could not place the order. Please try again.";
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
    if (!draft.timeslot_id) return false;
    if (!draft.customer_name.trim()) return false;
    if (!draft.customer_phone.trim()) return false;
    if (!draft.customer_email.trim()) return false;
    return true;
  }, [draft]);

  const handlePlaceOrder = () => {
    setError(null);
    if (!canPlace || !draft.timeslot_id) {
      setError("Please fill in your contact info and pick a timeslot.");
      return;
    }
    const body: PlaceOrderBody = {
      fulfillment_type: draft.fulfillment_type,
      timeslot_id: draft.timeslot_id,
      payment_method: draft.payment_method,
      customer_name: draft.customer_name.trim(),
      customer_phone: draft.customer_phone.trim(),
      customer_email: draft.customer_email.trim(),
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

  if (!hydrated) {
    return <div className="mt-8 h-96 animate-pulse rounded-3xl bg-white/40" />;
  }

  return (
    <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
      <div className="space-y-6">
        <Section title="Payment method">
          <div className="grid grid-cols-2 gap-3">
            <PaymentTile
              icon={<CreditCard className="h-5 w-5" />}
              label="Card"
              active={draft.payment_method === "card"}
              onClick={() => update({ payment_method: "card" })}
            />
            <PaymentTile
              icon={<Wallet className="h-5 w-5" />}
              label="Cash"
              active={draft.payment_method === "cash"}
              onClick={() => update({ payment_method: "cash" })}
            />
          </div>
        </Section>

        <Section
          title={draft.fulfillment_type === "delivery" ? "Delivery time" : "Pickup time"}
          subtitle="Time slots are shown in the UAE time zone."
        >
          <TimeslotPicker
            type={draft.fulfillment_type}
            value={draft.timeslot_id}
            onChange={(id) => update({ timeslot_id: id })}
          />
        </Section>

        <Section title="Your contact info">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              placeholder="Full name"
              value={draft.customer_name}
              onChange={(e) => update({ customer_name: e.target.value })}
            />
            <Input
              placeholder="Phone"
              value={draft.customer_phone}
              onChange={(e) => update({ customer_phone: e.target.value })}
            />
          </div>
          <Input
            type="email"
            placeholder="Email"
            value={draft.customer_email}
            onChange={(e) => update({ customer_email: e.target.value })}
          />
        </Section>

        {draft.fulfillment_type === "delivery" && draft.address ? (
          <Section title="Deliver to">
            <p className="text-sm leading-relaxed text-[var(--ink)]/80">
              {draft.address.building}, {draft.address.street}
              {draft.address.apartment ? `, ${draft.address.apartment}` : ""}
              <br />
              {draft.address.city}
              {draft.address.postal_code ? `, ${draft.address.postal_code}` : ""}
              {draft.address.notes ? (
                <>
                  <br />
                  <span className="italic text-[var(--ink)]/60">
                    {draft.address.notes}
                  </span>
                </>
              ) : null}
            </p>
            <button
              type="button"
              onClick={() => router.push("/checkout")}
              className="mt-2 text-sm text-[var(--brand)] underline-offset-2 hover:underline"
            >
              Change address
            </button>
          </Section>
        ) : null}

        <Section title="Order comment">
          <Textarea
            rows={3}
            value={draft.comment}
            onChange={(e) => update({ comment: e.target.value })}
            placeholder="e.g. without nuts"
          />
        </Section>

        <Section title="Promo code">
          <PromoCodeBox
            value={draft.promo_code}
            onApplied={(code) => update({ promo_code: code })}
          />
        </Section>

        {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
      </div>

      <OrderSummary
        fulfillmentType={draft.fulfillment_type}
        promoCode={draft.promo_code}
        onPlaceOrder={handlePlaceOrder}
        isPlacing={placeOrder.isPending}
        canPlace={canPlace}
      />
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
    <section className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
      <h2 className="font-display text-2xl">{title}</h2>
      {subtitle ? (
        <p className="mt-1 text-sm text-[var(--ink)]/60">{subtitle}</p>
      ) : null}
      <div className="mt-4 space-y-3">{children}</div>
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

export type { PaymentMethod };
