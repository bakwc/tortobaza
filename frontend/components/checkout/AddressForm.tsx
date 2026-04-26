"use client";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { OrderAddress } from "@/lib/api/types";

export type AddressFormProps = {
  value: OrderAddress;
  onChange: (next: OrderAddress) => void;
  errors?: Partial<Record<keyof OrderAddress, string>>;
};

export function AddressForm({ value, onChange, errors }: AddressFormProps) {
  const update = (key: keyof OrderAddress, val: string) =>
    onChange({ ...value, [key]: val });

  return (
    <div className="grid gap-3">
      <Field label="Street" error={errors?.street}>
        <Input
          value={value.street}
          onChange={(e) => update("street", e.target.value)}
          placeholder="Sheikh Zayed Road"
        />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Building" error={errors?.building}>
          <Input
            value={value.building}
            onChange={(e) => update("building", e.target.value)}
            placeholder="Burj Khalifa"
          />
        </Field>
        <Field label="Apartment / unit" error={errors?.apartment}>
          <Input
            value={value.apartment}
            onChange={(e) => update("apartment", e.target.value)}
            placeholder="1205"
          />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="City" error={errors?.city}>
          <Input
            value={value.city}
            onChange={(e) => update("city", e.target.value)}
            placeholder="Dubai"
          />
        </Field>
        <Field label="Postal code" error={errors?.postal_code}>
          <Input
            value={value.postal_code}
            onChange={(e) => update("postal_code", e.target.value)}
            placeholder=""
          />
        </Field>
      </div>
      <Field label="Notes for courier" error={errors?.notes}>
        <Textarea
          rows={3}
          value={value.notes}
          onChange={(e) => update("notes", e.target.value)}
          placeholder="Door code, landmarks, etc."
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
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
        {label}
      </span>
      {children}
      {error ? <span className="text-xs text-[var(--danger)]">{error}</span> : null}
    </label>
  );
}
