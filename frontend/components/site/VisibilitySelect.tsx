"use client";

import { useTranslations } from "next-intl";

import { Field, NativeSelect } from "@/components/menu/ui";
import { useSetVisibility, useVisibility, type SiteVisibility } from "@/hooks/useSite";

export function VisibilitySelect() {
  const t = useTranslations("site");
  const visibility = useVisibility();
  const setVisibility = useSetVisibility();
  return (
    <Field label={t("visibility")}>
      <NativeSelect
        value={visibility}
        onChange={(event) => setVisibility(event.target.value as SiteVisibility)}
      >
        <option value="active">{t("visibilityActive")}</option>
        <option value="hidden">{t("visibilityHidden")}</option>
        <option value="all">{t("visibilityAll")}</option>
      </NativeSelect>
    </Field>
  );
}
