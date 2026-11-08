"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { OrderAddress } from "@/lib/api/types";

export type AddressFormProps = {
  value: OrderAddress;
  onChange: (next: OrderAddress) => void;
  errors?: Partial<Record<keyof OrderAddress, string>>;
};

export function AddressForm({ value, onChange, errors }: AddressFormProps) {
  const t = useTranslations("checkout");

  const update = (key: keyof OrderAddress, val: string) =>
    onChange({ ...value, [key]: val });

  return (
    <div className="grid gap-3">
      <Field label={t("addressStreet")} error={errors?.street}>
        <Input
          name="street"
          className={errors?.street ? "border-[var(--danger)] bg-red-50" : undefined}
          value={value.street}
          onChange={(e) => update("street", e.target.value)}
          placeholder=""
        />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t("addressBuilding")} error={errors?.building}>
          <Input
            name="building"
            className={errors?.building ? "border-[var(--danger)] bg-red-50" : undefined}
            value={value.building}
            onChange={(e) => update("building", e.target.value)}
            placeholder=""
          />
        </Field>
        <Field label={t("addressApartment")} error={errors?.apartment}>
          <Input
            value={value.apartment}
            onChange={(e) => update("apartment", e.target.value)}
            placeholder=""
          />
        </Field>
      </div>
      <Field label={t("addressCity")} error={errors?.city}>
        <Input
          name="city"
          className={errors?.city ? "border-[var(--danger)] bg-red-50" : undefined}
          value={value.city}
          onChange={(e) => update("city", e.target.value)}
          placeholder={t("cityPlaceholder")}
        />
      </Field>
      <Field label={t("addressNotesCourier")} error={errors?.notes}>
        <Textarea
          rows={3}
          value={value.notes}
          onChange={(e) => update("notes", e.target.value)}
          placeholder={t("courierPlaceholder")}
        />
      </Field>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{label}</span>
      {children}
      {error ? <span className="text-xs text-[var(--danger)]">{error}</span> : null}
    </label>
  );
}
