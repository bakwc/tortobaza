"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, QueryState } from "@/components/menu/ui";
import {
  LocaleTabs,
  TranslateFieldsButton,
  applyTranslatedFields,
  filledFields,
  hasAnyValue,
  type SiteLocale,
} from "@/components/site/LocaleTabs";
import { VisibilitySelect } from "@/components/site/VisibilitySelect";
import { useCan } from "@/hooks/useAuth";
import { matchesVisibility, useSiteModifiers, useSiteOptions, useSiteTranslation, useVisibility } from "@/hooks/useSite";
import type { SiteModifierChoice, SiteOptionDetail, SiteTranslationBody } from "@/lib/api/site-schemas";

type OptionDraft = {
  id: number;
  name_en: string;
  name_ka: string;
  name_ru: string;
  price_delta: string;
  weight_kg: string;
  is_active: boolean;
  modifiers: number[];
};

function draftFrom(row: SiteOptionDetail): OptionDraft {
  return {
    id: row.id,
    name_en: row.name_en,
    name_ka: row.name_ka,
    name_ru: row.name_ru,
    price_delta: row.price_delta,
    weight_kg: row.weight_kg ?? "",
    is_active: row.is_active,
    modifiers: row.modifiers,
  };
}

function modifierGroups(rows: SiteModifierChoice[]): Array<[string, SiteModifierChoice[]]> {
  const groups = new Map<string, SiteModifierChoice[]>();
  for (const row of rows) {
    const current = groups.get(row.group_name) ?? [];
    current.push(row);
    groups.set(row.group_name, current);
  }
  return [...groups.entries()];
}

export function OptionsPanel() {
  const t = useTranslations("site");
  const canEdit = useCan("edit_catalog");
  const visibility = useVisibility();
  const options = useSiteOptions();
  const modifiers = useSiteModifiers();
  const translate = useSiteTranslation();
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [draft, setDraft] = useState<OptionDraft | null>(null);
  const visible = (options.list.data ?? []).filter((row) => matchesVisibility(row.is_active, visibility));
  const grouped = new Map<number, { id: number; title: string; rows: SiteOptionDetail[] }>();
  for (const row of visible) {
    const current = grouped.get(row.group);
    if (current === undefined) {
      grouped.set(row.group, { id: row.group, title: row.group_name_ru || row.group_name_en, rows: [row] });
    } else {
      current.rows.push(row);
    }
  }

  const open = (row: SiteOptionDetail) => {
    options.save.reset();
    translate.reset();
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>{t("options")}</CardTitle>
          <VisibilitySelect />
        </div>
        <QueryState isLoading={options.list.isLoading} isError={options.list.isError}>
          <div className="mt-4 grid gap-6">
            {[...grouped.values()].map((group) => (
              <div key={group.id} className="grid gap-2">
                <p className="text-sm font-medium text-[var(--muted-2)]">{group.title}</p>
                {group.rows.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    onClick={() => open(row)}
                    className="rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
                  >
                    <span className="font-medium text-[var(--ink)]">{row.name_ru || row.name_en}</span>
                    {!row.is_active ? (
                      <span className="ml-2 rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--muted-2)]">
                        {t("inactive")}
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </QueryState>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={draft.name_ru || draft.name_en || t("options")}
          pending={options.save.isPending}
          error={options.save.error ?? translate.error}
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            options.save.mutate(
              {
                id: draft.id,
                body: {
                  name_en: draft.name_en,
                  name_ka: draft.name_ka,
                  name_ru: draft.name_ru,
                  price_delta: draft.price_delta,
                  weight_kg: draft.weight_kg === "" ? null : draft.weight_kg,
                  is_active: draft.is_active,
                  modifiers: draft.modifiers,
                },
              },
              { onSuccess: close },
            )
          }
          onDelete={null}
          deletePending={false}
          headerAction={null}
          below={null}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
            {canEdit ? (
              <TranslateFieldsButton
                label={t("translateFields")}
                pending={translate.isPending}
                disabled={Object.keys(filledFields(draft, locale, ["name"])).length === 0}
                onClick={() => {
                  const fields = filledFields(draft, locale, ["name"]);
                  const items: SiteTranslationBody["items"] = [
                    { key: "option", kind: "option", id: draft.id, fields },
                  ];
                  translate.mutate(
                    { language: locale, items },
                    {
                      onSuccess: (result) => {
                        const translated = result.items.find((item) => item.key === "option");
                        if (translated === undefined) return;
                        setDraft((row) => (row === null ? null : { ...row, ...applyTranslatedFields(translated.fields, locale) }));
                      },
                    },
                  );
                }}
              />
            ) : null}
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label={t("name")}>
              <Input
                required={!hasAnyValue(draft, "name")}
                name={`name_${locale}`}
                value={draft[`name_${locale}`]}
                onChange={(event) => setDraft({ ...draft, [`name_${locale}`]: event.target.value })}
              />
            </Field>
            <Field label={t("priceDelta")}>
              <Input
                name="price_delta"
                required
                inputMode="decimal"
                value={draft.price_delta}
                onChange={(event) => setDraft({ ...draft, price_delta: event.target.value })}
              />
            </Field>
            <Field label={t("weightKg")}>
              <Input
                value={draft.weight_kg}
                onChange={(event) => setDraft({ ...draft, weight_kg: event.target.value })}
              />
            </Field>
            <div className="flex items-end pb-3">
              <CheckboxField
                label={t("active")}
                checked={draft.is_active}
                onChange={(checked) => setDraft({ ...draft, is_active: checked })}
              />
            </div>
          </div>
          <div className="mt-6 grid gap-4">
            <p className="font-medium text-[var(--ink)]">{t("modifiers")}</p>
            <QueryState isLoading={modifiers.isLoading} isError={modifiers.isError}>
              {modifierGroups(modifiers.data ?? []).map(([name, rows]) => (
                <div key={name} className="grid gap-2">
                  <p className="text-sm text-[var(--muted-2)]">{name}</p>
                  <div className="flex flex-wrap gap-4">
                    {rows.map((row) => (
                      <CheckboxField
                        key={row.id}
                        label={row.is_active ? row.name : `${row.name} (${t("inactive")})`}
                        checked={draft.modifiers.includes(row.id)}
                        onChange={(checked) =>
                          setDraft({
                            ...draft,
                            modifiers: checked
                              ? [...draft.modifiers, row.id]
                              : draft.modifiers.filter((id) => id !== row.id),
                          })
                        }
                      />
                    ))}
                  </div>
                </div>
              ))}
            </QueryState>
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
