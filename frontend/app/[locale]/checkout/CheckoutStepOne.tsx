"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { FulfillmentToggle } from "@/components/checkout/FulfillmentToggle";
import { AddressForm } from "@/components/checkout/AddressForm";
import { PickupPicker } from "@/components/checkout/PickupPicker";
import { saveDraft, type CheckoutDraft } from "@/lib/checkout-draft";
import type { OrderAddress } from "@/lib/api/types";
import { useRouter } from "@/i18n/navigation";

const emptyAddress: OrderAddress = {
  street: "",
  building: "",
  apartment: "",
  city: "Batumi",
  postal_code: "",
  notes: "",
};

export function CheckoutStepOne({
  draft,
  onDraftChange,
}: {
  draft: CheckoutDraft;
  onDraftChange: (updater: (prev: CheckoutDraft) => CheckoutDraft) => void;
}) {
  const t = useTranslations("checkout");
  const tForms = useTranslations("forms");
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [addressErrors, setAddressErrors] = useState<Partial<Record<keyof OrderAddress, string>>>({});

  const address = draft.address ?? emptyAddress;

  const handleNext = () => {
    setError(null);
    setAddressErrors({});
    if (draft.fulfillment_type === "delivery") {
      const labels: Record<"street" | "building" | "city", string> = {
        street: t("addressStreet"),
        building: t("addressBuilding"),
        city: t("addressCity"),
      };
      const required = ["street", "building", "city"] as const;
      const missing = required.filter((key) => !address[key].trim());
      if (missing.length > 0) {
        const next: Partial<Record<keyof OrderAddress, string>> = {};
        for (const key of missing) next[key] = tForms("requiredField");
        setAddressErrors(next);
        setError(tForms("requiredFieldsMissing", { fields: missing.map((key) => labels[key]).join(", ") }));
        document.querySelector(`[name="${missing[0]}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      const next: CheckoutDraft = {
        ...draft,
        address,
        pickup_location_id: null,
      };
      saveDraft(next);
      onDraftChange(() => next);
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
      onDraftChange(() => next);
    }
    router.push("/checkout/confirm");
  };

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 ring-1 ring-[var(--line)]">
        <FulfillmentToggle
          value={draft.fulfillment_type}
          onChange={(value) =>
            onDraftChange((prev) => ({
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
              errors={addressErrors}
              onChange={(next) => onDraftChange((prev) => ({ ...prev, address: next }))}
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
              onChange={(id) => onDraftChange((prev) => ({ ...prev, pickup_location_id: id }))}
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
