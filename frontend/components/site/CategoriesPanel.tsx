"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Languages, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, QueryState } from "@/components/menu/ui";
import { DeliveryTierSelect } from "@/components/site/DeliveryTierSelect";
import {
  LocaleTabs,
  hasAnyName,
  otherLocaleNames,
  type SiteLocale,
} from "@/components/site/LocaleTabs";
import { VisibilitySelect } from "@/components/site/VisibilitySelect";
import { useCan } from "@/hooks/useAuth";
import {
  matchesVisibility,
  useSiteCategories,
  useSiteCategoryImageDelete,
  useSiteCategoryImageUpload,
  useSiteNameTranslation,
  useVisibility,
} from "@/hooks/useSite";
import type { SiteCategory, SiteCategoryBody } from "@/lib/api/site-schemas";

type CategoryDraft = SiteCategoryBody & { id: number | null };

function draftFrom(row: SiteCategory | null, position: number): CategoryDraft {
  if (row === null) {
    return {
      id: null,
      slug: "",
      name_en: "",
      name_ka: "",
      name_ru: "",
      page_slug_en: "",
      page_slug_ka: "",
      page_slug_ru: "",
      page_heading_en: "",
      page_heading_ka: "",
      page_heading_ru: "",
      page_description_en: "",
      page_description_ka: "",
      page_description_ru: "",
      seo_title_en: "",
      seo_title_ka: "",
      seo_title_ru: "",
      seo_description_en: "",
      seo_description_ka: "",
      seo_description_ru: "",
      position,
      is_active: true,
      delivery_schedule_tier: "same_day",
    };
  }
  const { id, image: _image, updated_at: _updated, ...body } = row;
  return { id, ...body };
}

export function CategoriesPanel() {
  const t = useTranslations("site");
  const canEdit = useCan("edit_catalog");
  const visibility = useVisibility();
  const categories = useSiteCategories();
  const visibleCategories = (categories.list.data ?? []).filter((row) =>
    matchesVisibility(row.is_active, visibility),
  );
  const uploadImage = useSiteCategoryImageUpload();
  const deleteImage = useSiteCategoryImageDelete();
  const translateName = useSiteNameTranslation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<CategoryDraft | null>(null);

  const open = (row: SiteCategory | null) => {
    categories.save.reset();
    categories.remove.reset();
    translateName.reset();
    setEditingId(row ? row.id : null);
    setDraft(draftFrom(row, (categories.list.data ?? []).length));
  };
  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>{t("categories")}</CardTitle>
          <div className="flex flex-wrap items-end gap-3">
            <VisibilitySelect />
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("newCategory")}
              </Button>
            ) : null}
          </div>
        </div>
        <QueryState isLoading={categories.list.isLoading} isError={categories.list.isError}>
          <div className="mt-4 grid gap-3">
            {visibleCategories.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="flex items-center gap-4 rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                {row.image?.preview ? (
                  <img
                    src={row.image.preview.src}
                    alt=""
                    className="h-14 w-14 rounded-xl object-cover"
                  />
                ) : (
                  <span className="h-14 w-14 rounded-xl bg-[var(--cream)]" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-[var(--ink)]">{row.name_ru || row.name_en}</p>
                  <p className="text-sm text-[var(--muted-2)]">{row.slug}</p>
                </div>
                {!row.is_active ? (
                  <span className="shrink-0 rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--muted-2)]">
                    {t("inactive")}
                  </span>
                ) : null}
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
          title={draft.id === null ? t("newCategory") : draft.slug}
          pending={categories.save.isPending}
          error={
            categories.save.error ??
            categories.remove.error ??
            translateName.error ??
            uploadImage.error ??
            deleteImage.error
          }
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() => {
            const { id, ...body } = draft;
            categories.save.mutate({ id, body }, { onSuccess: close });
          }}
          onDelete={
            canEdit && draft.id !== null
              ? () => categories.remove.mutate(draft.id as number, { onSuccess: close })
              : null
          }
          deletePending={categories.remove.isPending}
          headerAction={null}
          below={null}
        >
          <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label={t("name")}>
              <Input
                required={!hasAnyName(draft)}
                name={`name_${locale}`}
                value={draft[`name_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`name_${locale}`]: event.target.value })
                }
              />
              {canEdit ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="self-start"
                  disabled={draft[`name_${locale}`].trim() === "" || translateName.isPending}
                  onClick={() => {
                    const source = locale;
                    translateName.mutate(
                      { kind: "category", language: source, name: draft[`name_${source}`] },
                      {
                        onSuccess: (names) =>
                          setDraft((row) =>
                            row === null ? null : { ...row, ...otherLocaleNames(names, source) },
                          ),
                      },
                    );
                  }}
                >
                  {translateName.isPending ? (
                    <Spinner className="mr-1 h-4 w-4" />
                  ) : (
                    <Languages className="mr-1 h-4 w-4" />
                  )}
                  {t("translateName")}
                </Button>
              ) : null}
            </Field>
            <Field label={t("slug")}>
              <Input
                name="slug"
                required
                value={draft.slug}
                onChange={(event) => setDraft({ ...draft, slug: event.target.value })}
              />
            </Field>
            <Field label={t("pageSlug")}>
              <Input
                value={draft[`page_slug_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`page_slug_${locale}`]: event.target.value })
                }
              />
            </Field>
            <Field label={t("position")}>
              <Input
                type="number"
                value={draft.position}
                onChange={(event) => setDraft({ ...draft, position: Number(event.target.value) })}
              />
            </Field>
            <Field label={t("pageHeading")} className="sm:col-span-2">
              <Input
                value={draft[`page_heading_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`page_heading_${locale}`]: event.target.value })
                }
              />
            </Field>
            <Field label={t("pageDescription")} className="sm:col-span-2">
              <Textarea
                rows={3}
                value={draft[`page_description_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`page_description_${locale}`]: event.target.value })
                }
              />
            </Field>
            <Field label={t("seoTitle")} className="sm:col-span-2">
              <Input
                value={draft[`seo_title_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`seo_title_${locale}`]: event.target.value })
                }
              />
            </Field>
            <Field label={t("seoDescription")} className="sm:col-span-2">
              <Textarea
                rows={3}
                value={draft[`seo_description_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`seo_description_${locale}`]: event.target.value })
                }
              />
            </Field>
            <Field label={t("deliveryTier")}>
              <DeliveryTierSelect
                allowEmpty={false}
                value={draft.delivery_schedule_tier}
                onChange={(value) =>
                  setDraft({
                    ...draft,
                    delivery_schedule_tier: value ?? draft.delivery_schedule_tier,
                  })
                }
              />
            </Field>
            <CheckboxField
              label={t("active")}
              checked={draft.is_active}
              onChange={(checked) => setDraft({ ...draft, is_active: checked })}
            />
          </div>
          {draft.id !== null ? (
            <div className="mt-6 grid gap-3">
              <p className="font-medium text-[var(--ink)]">{t("categoryImage")}</p>
              {(() => {
                const row = (categories.list.data ?? []).find((item) => item.id === draft.id);
                return row?.image?.preview ? (
                  <img
                    src={row.image.preview.src}
                    alt=""
                    className="aspect-video max-w-xs rounded-2xl object-cover"
                  />
                ) : null;
              })()}
              {canEdit ? (
                <>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file && draft.id !== null) {
                        uploadImage.mutate({ id: draft.id, file });
                      }
                      event.target.value = "";
                    }}
                  />
                  <div className="flex gap-2">
                    <Button type="button" size="sm" onClick={() => fileRef.current?.click()}>
                      {t("uploadImage")}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => draft.id !== null && deleteImage.mutate(draft.id)}
                    >
                      {t("removeImage")}
                    </Button>
                  </div>
                </>
              ) : null}
            </div>
          ) : null}
        </EditorDialog>
      ) : null}
    </div>
  );
}
