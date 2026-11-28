"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { ImageCropEditor } from "@/components/site/ImageCropEditor";
import { OptionImagePreview } from "@/components/site/ImageSitePreview";
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
import {
  matchesVisibility,
  useSiteOptionGroups,
  useSiteOptionImageDelete,
  useSiteOptionImageUpload,
  useSiteTechCards,
  useSiteTranslation,
  useVisibility,
} from "@/hooks/useSite";
import { defaultCenterCrop, type CropValues } from "@/lib/site/crop";
import type { SiteOptionGroup, SiteTranslationBody } from "@/lib/api/site-schemas";
import { newDraftKey } from "@/components/menu/ComponentLinesEditor";

type OptionDraft = {
  key: string;
  id: number | null;
  name_en: string;
  name_ka: string;
  name_ru: string;
  price_delta: string;
  weight_kg: string;
  tech_card: number | null;
  position: number;
  is_active: boolean;
  crop_left: number | null;
  crop_top: number | null;
  crop_size: number | null;
  image_src: string | null;
  image_width: number | null;
  image_height: number | null;
};

type GroupDraft = {
  slug: string;
  name_en: string;
  name_ka: string;
  name_ru: string;
  selection_type: "single" | "multi";
  is_required_default: boolean;
  affects_production: boolean;
  min_selections: string;
  max_selections: string;
  options: OptionDraft[];
};

function draftFrom(row: SiteOptionGroup | null): GroupDraft {
  if (row === null) {
    return {
      slug: "",
      name_en: "",
      name_ka: "",
      name_ru: "",
      selection_type: "single",
      is_required_default: true,
      affects_production: true,
      min_selections: "0",
      max_selections: "1",
      options: [],
    };
  }
  return {
    slug: row.slug,
    name_en: row.name_en,
    name_ka: row.name_ka,
    name_ru: row.name_ru,
    selection_type: row.selection_type,
    is_required_default: row.is_required_default,
    affects_production: row.affects_production,
    min_selections: String(row.min_selections),
    max_selections: row.max_selections === null ? "" : String(row.max_selections),
    options: row.options.map((option) => ({
      key: newDraftKey(),
      id: option.id,
      name_en: option.name_en,
      name_ka: option.name_ka,
      name_ru: option.name_ru,
      price_delta: option.price_delta,
      weight_kg: option.weight_kg ?? "",
      tech_card: option.tech_card,
      position: option.position,
      is_active: option.is_active,
      crop_left: option.crop_left,
      crop_top: option.crop_top,
      crop_size: option.crop_size,
      image_src: option.image?.original.src ?? null,
      image_width: option.image?.width ?? null,
      image_height: option.image?.height ?? null,
    })),
  };
}

function cropFromOption(option: OptionDraft): CropValues {
  return {
    crop_left: option.crop_left ?? 0,
    crop_top: option.crop_top ?? 0,
    crop_size: option.crop_size ?? 1,
  };
}

export function OptionGroupsPanel() {
  const t = useTranslations("site");
  const tForms = useTranslations("forms");
  const canEdit = useCan("edit_catalog");
  const visibility = useVisibility();
  const groups = useSiteOptionGroups();
  const techCards = useSiteTechCards();
  const techCardOptions = [
    { value: "", label: t("noTechCard") },
    ...(techCards.data ?? []).map((card) => ({ value: String(card.id), label: card.name })),
  ];
  const visibleGroups = (groups.list.data ?? []).flatMap((row) => {
    const options = row.options.filter((option) => matchesVisibility(option.is_active, visibility));
    if (visibility !== "all" && options.length === 0) return [];
    return [{ row, options }];
  });
  const uploadOptionImage = useSiteOptionImageUpload();
  const deleteOptionImage = useSiteOptionImageDelete();
  const translate = useSiteTranslation();
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<GroupDraft | null>(null);
  const [activeOptionKey, setActiveOptionKey] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadTargetRef = useRef<{ id: number; key: string } | null>(null);

  const open = (row: SiteOptionGroup | null) => {
    groups.save.reset();
    groups.remove.reset();
    translate.reset();
    setEditingId(row ? row.id : null);
    const next = draftFrom(row);
    setDraft(next);
    setActiveOptionKey(next.options[0]?.key ?? null);
  };
  const close = () => {
    setDraft(null);
    setActiveOptionKey(null);
  };

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>{t("optionGroups")}</CardTitle>
          <div className="flex flex-wrap items-end gap-3">
            <VisibilitySelect />
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("newOptionGroup")}
              </Button>
            ) : null}
          </div>
        </div>
        <QueryState isLoading={groups.list.isLoading} isError={groups.list.isError}>
          <div className="mt-4 grid gap-3">
            {visibleGroups.map(({ row, options }) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <p className="font-medium text-[var(--ink)]">{row.name_ru || row.name_en}</p>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--muted-2)]">
                  {options.length === 0 ? (
                    "—"
                  ) : (
                    options.map((option) => (
                      <span key={option.id} className="inline-flex items-center gap-1">
                        {option.name_ru || option.name_en}
                        {!option.is_active ? (
                          <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--muted-2)]">
                            {t("inactive")}
                          </span>
                        ) : null}
                      </span>
                    ))
                  )}
                </div>
              </button>
            ))}
          </div>
        </QueryState>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newOptionGroup") : draft.slug}
          pending={groups.save.isPending}
          error={
            groups.save.error ??
            groups.remove.error ??
            translate.error ??
            uploadOptionImage.error ??
            deleteOptionImage.error
          }
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            groups.save.mutate(
              {
                id: editingId,
                body: {
                  slug: draft.slug,
                  name_en: draft.name_en,
                  name_ka: draft.name_ka,
                  name_ru: draft.name_ru,
                  selection_type: draft.selection_type,
                  is_required_default: draft.is_required_default,
                  affects_production: draft.affects_production,
                  min_selections: Number(draft.min_selections || "0"),
                  max_selections: draft.max_selections === "" ? null : Number(draft.max_selections),
                  options: draft.options.map((row) => ({
                    id: row.id,
                    name_en: row.name_en,
                    name_ka: row.name_ka,
                    name_ru: row.name_ru,
                    price_delta: row.price_delta,
                    weight_kg: row.weight_kg === "" ? null : row.weight_kg,
                    tech_card: row.tech_card,
                    position: row.position,
                    is_active: row.is_active,
                    crop_left: row.crop_left,
                    crop_top: row.crop_top,
                    crop_size: row.crop_size,
                  })),
                },
              },
              { onSuccess: close },
            )
          }
          onDelete={
            canEdit && editingId !== null
              ? () => groups.remove.mutate(editingId, { onSuccess: close })
              : null
          }
          deletePending={groups.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
            {canEdit ? (
              <TranslateFieldsButton
                label={t("translateFields")}
                pending={translate.isPending}
                disabled={
                  Object.keys(filledFields(draft, locale, ["name"])).length === 0 &&
                  !draft.options.some((option) => option[`name_${locale}`].trim() !== "")
                }
                onClick={() => {
                  const source = locale;
                  const items: SiteTranslationBody["items"] = [];
                  const groupFields = filledFields(draft, source, ["name"]);
                  if (Object.keys(groupFields).length > 0) {
                    items.push({
                      key: "group",
                      kind: "optiongroup" as const,
                      id: editingId,
                      fields: groupFields,
                    });
                  }
                  for (const option of draft.options) {
                    const fields = filledFields(option, source, ["name"]);
                    if (Object.keys(fields).length > 0) {
                      items.push({
                        key: `option-${option.key}`,
                        kind: "option" as const,
                        id: option.id,
                        fields,
                      });
                    }
                  }
                  translate.mutate(
                    { language: source, items },
                    {
                      onSuccess: (result) => {
                        const byKey = new Map(result.items.map((item) => [item.key, item]));
                        setDraft((row) => {
                          if (row === null) return null;
                          const group = byKey.get("group");
                          return {
                            ...(group ? { ...row, ...applyTranslatedFields(group.fields, source) } : row),
                            options: row.options.map((option) => {
                              const translated = byKey.get(`option-${option.key}`);
                              return translated
                                ? { ...option, ...applyTranslatedFields(translated.fields, source) }
                                : option;
                            }),
                          };
                        });
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
            <Field label={t("slug")}>
              <Input
                name="slug"
                required
                value={draft.slug}
                onChange={(event) => setDraft({ ...draft, slug: event.target.value })}
              />
            </Field>
            <Field label={t("selectionType")}>
              <NativeSelect
                value={draft.selection_type}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    selection_type: event.target.value as "single" | "multi",
                  })
                }
              >
                <option value="single">{t("selectionSingle")}</option>
                <option value="multi">{t("selectionMulti")}</option>
              </NativeSelect>
            </Field>
            <CheckboxField
              label={t("requiredByDefault")}
              checked={draft.is_required_default}
              onChange={(checked) => setDraft({ ...draft, is_required_default: checked })}
            />
            <CheckboxField
              label={t("affectsProduction")}
              checked={draft.affects_production}
              onChange={(checked) => setDraft({ ...draft, affects_production: checked })}
            />
            <Field label={t("minSelections")}>
              <Input
                value={draft.min_selections}
                onChange={(event) => setDraft({ ...draft, min_selections: event.target.value })}
              />
            </Field>
            <Field label={t("maxSelections")}>
              <Input
                value={draft.max_selections}
                onChange={(event) => setDraft({ ...draft, max_selections: event.target.value })}
              />
            </Field>
          </div>
          <div className="mt-6 grid gap-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-[var(--ink)]">{t("options")}</p>
              {canEdit ? (
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    const key = newDraftKey();
                    setDraft({
                      ...draft,
                      options: [
                        ...draft.options,
                        {
                          key,
                          id: null,
                          name_en: "",
                          name_ka: "",
                          name_ru: "",
                          price_delta: "0",
                          weight_kg: "",
                          tech_card: null,
                          position: draft.options.length,
                          is_active: true,
                          crop_left: null,
                          crop_top: null,
                          crop_size: null,
                          image_src: null,
                          image_width: null,
                          image_height: null,
                        },
                      ],
                    });
                    setActiveOptionKey(key);
                  }}
                >
                  <Plus className="mr-1 h-4 w-4" />
                  {t("addOption")}
                </Button>
              ) : null}
            </div>
            {canEdit ? (
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  const target = uploadTargetRef.current;
                  if (file && target) {
                    uploadOptionImage.mutate(
                      { id: target.id, file },
                      {
                        onSuccess: (saved) => {
                          const savedOption = saved.options.find((item) => item.id === target.id);
                          if (!savedOption?.image) return;
                          setDraft((current) => {
                            if (!current) return current;
                            return {
                              ...current,
                              options: current.options.map((item) =>
                                item.key === target.key
                                  ? {
                                      ...item,
                                      image_src: savedOption.image?.original.src ?? null,
                                      image_width: savedOption.image?.width ?? null,
                                      image_height: savedOption.image?.height ?? null,
                                      crop_left: savedOption.crop_left,
                                      crop_top: savedOption.crop_top,
                                      crop_size: savedOption.crop_size,
                                    }
                                  : item,
                              ),
                            };
                          });
                        },
                      },
                    );
                  }
                  event.target.value = "";
                }}
              />
            ) : null}
            {draft.options.map((row, index) => (
              <div
                key={row.key}
                data-field-group={tForms("rowNumber", { number: index + 1 })}
                data-error-list="options"
                className={`grid gap-3 rounded-2xl border px-3 py-3 ${
                  activeOptionKey === row.key ? "border-[var(--brand)]" : "border-[var(--line)]"
                }`}
              >
                <button type="button" className="text-left font-medium" onClick={() => setActiveOptionKey(row.key)}>
                  {row.name_ru || row.name_en || t("newOption")}
                </button>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Field label={t("name")}>
                    <Input
                      required={!hasAnyValue(row, "name")}
                      name={`name_${locale}`}
                      value={row[`name_${locale}`]}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          options: draft.options.map((item) =>
                            item.key === row.key
                              ? { ...item, [`name_${locale}`]: event.target.value }
                              : item,
                          ),
                        })
                      }
                    />
                  </Field>
                  <Field label={t("priceDelta")}>
                    <Input
                      name="price_delta"
                      required
                      inputMode="decimal"
                      value={row.price_delta}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          options: draft.options.map((item) =>
                            item.key === row.key ? { ...item, price_delta: event.target.value } : item,
                          ),
                        })
                      }
                    />
                  </Field>
                  <Field label={t("weightKg")}>
                    <Input
                      value={row.weight_kg}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          options: draft.options.map((item) =>
                            item.key === row.key ? { ...item, weight_kg: event.target.value } : item,
                          ),
                        })
                      }
                    />
                  </Field>
                  <Field label={t("techCard")}>
                    <SearchSelect
                      options={techCardOptions}
                      value={row.tech_card === null ? "" : String(row.tech_card)}
                      onChange={(value) =>
                        setDraft({
                          ...draft,
                          options: draft.options.map((item) =>
                            item.key === row.key
                              ? { ...item, tech_card: value === "" ? null : Number(value) }
                              : item,
                          ),
                        })
                      }
                      placeholder={t("noTechCard")}
                      required={false}
                      name={null}
                      className=""
                      onCreate={null}
                      createPending={false}
                      keepSelectedOnDigit={false}
                    />
                  </Field>
                </div>
                {canEdit ? (
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => setActiveOptionKey(row.key)}>
                      {t("editImage")}
                    </Button>
                    {row.id !== null ? (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (row.id === null) return;
                            setActiveOptionKey(row.key);
                            uploadTargetRef.current = { id: row.id, key: row.key };
                            fileRef.current?.click();
                          }}
                        >
                          {t("uploadImage")}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            row.id !== null &&
                            deleteOptionImage.mutate(row.id, {
                              onSuccess: () =>
                                setDraft((current) => {
                                  if (!current) return current;
                                  return {
                                    ...current,
                                    options: current.options.map((item) =>
                                      item.key === row.key
                                        ? {
                                            ...item,
                                            image_src: null,
                                            image_width: null,
                                            image_height: null,
                                          }
                                        : item,
                                    ),
                                  };
                                }),
                            })
                          }
                        >
                          {t("removeImage")}
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs text-[var(--muted-2)]">{t("saveBeforeOptionImage")}</span>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setDraft({
                          ...draft,
                          options: draft.options.filter((item) => item.key !== row.key),
                        })
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ) : null}
                {row.image_src && row.image_width && row.image_height ? (
                  activeOptionKey === row.key ? (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {canEdit ? (
                        <ImageCropEditor
                          src={row.image_src}
                          width={row.image_width}
                          height={row.image_height}
                          crop={cropFromOption(row)}
                          onChange={(crop) =>
                            setDraft({
                              ...draft,
                              options: draft.options.map((item) =>
                                item.key === row.key
                                  ? {
                                      ...item,
                                      crop_left: crop.crop_left,
                                      crop_top: crop.crop_top,
                                      crop_size: crop.crop_size,
                                    }
                                  : item,
                              ),
                            })
                          }
                        />
                      ) : null}
                      <OptionImagePreview
                        src={row.image_src}
                        width={row.image_width}
                        height={row.image_height}
                        crop={cropFromOption(row)}
                        label={row.name_ru || row.name_en}
                      />
                    </div>
                  ) : (
                    <OptionImagePreview
                      src={row.image_src}
                      width={row.image_width}
                      height={row.image_height}
                      crop={cropFromOption(row)}
                      label={row.name_ru || row.name_en}
                    />
                  )
                ) : null}
              </div>
            ))}
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
