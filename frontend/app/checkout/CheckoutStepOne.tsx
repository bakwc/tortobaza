"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { FulfillmentToggle } from "@/components/checkout/FulfillmentToggle";
import { AddressForm } from "@/components/checkout/AddressForm";
import { PickupPicker } from "@/components/checkout/PickupPicker";
import {
  emptyDraft,
  loadDraft,
  saveDraft,
  type CheckoutDraft,
} from "@/lib/checkout-draft";
import type { OrderAddress } from "@/lib/api/types";

const emptyAddress: OrderAddress = {
  street: "",
  building: "",
  apartment: "",
  city: "Batumi",
  postal_code: "",
  notes: "",
};

export function CheckoutStepOne() {
  const t = useTranslations("checkout");
  const router = useRouter();
  const [draft, setDraft] = useState<CheckoutDraft>(emptyDraft);
  const [hydrated, setHydrated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(loadDraft());
    setHydrated(true);
  }, []);

  if (!hydrated) {
    return <div className="h-64 animate-pulse rounded-3xl bg-white/40" />;
  }

  const address = draft.address ?? emptyAddress;

  const handleNext = () => {
    setError(null);
    if (draft.fulfillment_type === "delivery") {
      const required: (keyof OrderAddress)[] = ["street", "building", "city"];
      const missing = required.filter((k) => !address[k].trim());
      if (missing.length > 0) {
        setError(t("fillStreetBuildingCity"));
        return;
      }
      const next: CheckoutDraft = {
        ...draft,
        address,
        pickup_location_id: null,
      };
      saveDraft(next);
    } else {
      if (!draft.pickup_location_id) {
        setError(t("pickLocationRequired"));
        return;
      }
      const next: CheckoutDraft = {
        ...draft,
        address: null,
      };
      saveDraft(next);
    }
    router.push("/checkout/confirm");
  };

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
        <FulfillmentToggle
          value={draft.fulfillment_type}
          onChange={(value) =>
            setDraft((prev) => ({
              ...prev,
              fulfillment_type: value,
              schedule: null,
            }))
          }
        />
      </section>

      {draft.fulfillment_type === "delivery" ? (
        <section className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
          <h2 className="font-display text-2xl">{t("deliveryAddress")}</h2>
          <p className="mt-1 text-sm text-[var(--ink)]/60">{t("deliveryAcrossBatumi")}</p>
          <div className="mt-4">
            <AddressForm
              value={address}
              onChange={(next) => setDraft((prev) => ({ ...prev, address: next }))}
            />
          </div>
        </section>
      ) : (
        <section className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
          <h2 className="font-display text-2xl">{t("pickupLocation")}</h2>
          <p className="mt-1 text-sm text-[var(--ink)]/60">{t("pickupHint")}</p>
          <div className="mt-4">
            <PickupPicker
              value={draft.pickup_location_id}
              onChange={(id) =>
                setDraft((prev) => ({ ...prev, pickup_location_id: id }))
              }
            />
          </div>
        </section>
      )}

      {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

      <Button size="lg" onClick={handleNext} className="w-full sm:w-auto">
        {t("continue")}
      </Button>
    </div>
  );
}
