"use client";

import { useEffect, useState } from "react";
import { CheckoutBasket } from "@/components/checkout/CheckoutBasket";
import { CheckoutStepOne } from "./CheckoutStepOne";
import { emptyDraft, loadDraft, saveDraft, type CheckoutDraft } from "@/lib/checkout-draft";

export function CheckoutPageClient() {
  const [draft, setDraft] = useState(emptyDraft);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setDraft(loadDraft());
    setHydrated(true);
  }, []);

  const updateDraft = (updater: (prev: CheckoutDraft) => CheckoutDraft) => {
    setDraft((prev) => {
      const next = updater(prev);
      saveDraft(next);
      return next;
    });
  };

  if (!hydrated) {
    return <div className="h-64 animate-pulse rounded-3xl bg-white/40" />;
  }

  return (
    <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
      <CheckoutStepOne draft={draft} onDraftChange={updateDraft} />
      <CheckoutBasket
        fulfillmentType={draft.fulfillment_type}
        promoCode={draft.promo_code}
      />
    </div>
  );
}
