"use client";

import { useTranslations } from "next-intl";

import { NativeSelect } from "@/components/menu/ui";
import type { DeliveryScheduleTier } from "@/lib/api/site-schemas";

export function DeliveryTierSelect({
  value,
  onChange,
  allowEmpty,
}: {
  value: DeliveryScheduleTier | null;
  onChange: (value: DeliveryScheduleTier | null) => void;
  allowEmpty: boolean;
}) {
  const t = useTranslations("site");
  return (
    <NativeSelect
      value={value ?? ""}
      onChange={(event) => {
        const raw = event.target.value;
        onChange(raw === "" ? null : (raw as DeliveryScheduleTier));
      }}
    >
      {allowEmpty ? <option value="">{t("deliveryTierInherit")}</option> : null}
      <option value="all_day">{t("deliveryTierAllDay")}</option>
      <option value="same_day">{t("deliveryTierSameDay")}</option>
      <option value="next_day">{t("deliveryTierNextDay")}</option>
      <option value="plus_2">{t("deliveryTierPlus2")}</option>
      <option value="plus_3">{t("deliveryTierPlus3")}</option>
    </NativeSelect>
  );
}
