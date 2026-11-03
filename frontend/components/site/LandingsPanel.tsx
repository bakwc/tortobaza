"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { LocaleTabs, type SiteLocale } from "@/components/site/LocaleTabs";
import { useCan } from "@/hooks/useAuth";
import {
  useShowHidden,
  useSiteCategories,
  useSiteCategoryLandings,
  useSiteCategoryLandingImageDelete,
  useSiteCategoryLandingImageUpload,
} from "@/hooks/useSite";
import type { SiteCategoryLanding, SiteCategoryLandingBody } from "@/lib/api/site-schemas";

type LandingDraft = SiteCategoryLandingBody & { id: number | null };

function draftFrom(row: SiteCategoryLanding | null, categories: { id: number }[]): LandingDraft {
  if (row === null) {
    return {
      id: null,
      slug: "",
      source: categories[0]?.id ?? 0,
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
      is_active: true,
    };
  }
  const { id, source_name: _sourceName, image: _image, updated_at: _updated, ...body } = row;
  return { id, ...body };
}

export function LandingsPanel() {
  const t = useTranslations("site");
  const canEdit = useCan("edit_catalog");
  const categories = useSiteCategories();
  const showHidden = useShowHidden();
  const landings = useSiteCategoryLandings();
  const visibleLandings = (landings.list.data ?? []).filter((row) => showHidden || row.is_active);
  const uploadImage = useSiteCategoryLandingImageUpload();
  const deleteImage = useSiteCategoryLandingImageDelete();
  const fileRef = useRef<HTMLInputElement>(null);
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [draft, setDraft] = useState<LandingDraft | null>(null);

  const open = (row: SiteCategoryLanding | null) => {
    landings.save.reset();
    landings.remove.reset();
    setDraft(draftFrom(row, categories.list.data ?? []));
  };
  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("landings")}</CardTitle>
          {canEdit ? (
            <Button type="button" size="sm" onClick={() => open(null)}>
              <Plus className="mr-1 h-4 w-4" />
              {t("newLanding")}
            </Button>
          ) : null}
        </div>
        <QueryState isLoading={landings.list.isLoading} isError={landings.list.isError}>
          <div className="mt-4 grid gap-3">
            {visibleLandings.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="flex items-center gap-4 rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-[var(--ink)]">{row.slug}</p>
                  <p className="text-sm text-[var(--muted-2)]">
                    {row.source_name} · {row.page_slug_ru || row.page_slug_en || "—"}
                  </p>
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
          title={draft.id === null ? t("newLanding") : draft.slug}
          pending={landings.save.isPending}
          error={landings.save.error ?? landings.remove.error}
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() => {
            const { id, ...body } = draft;
            landings.save.mutate({ id, body }, { onSuccess: close });
          }}
          onDelete={
            canEdit && draft.id !== null
              ? () => landings.remove.mutate(draft.id as number, { onSuccess: close })
              : null
          }
          deletePending={landings.remove.isPending}
          headerAction={null}
          below={null}
        >
          <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label={t("slug")}>
              <Input value={draft.slug} onChange={(event) => setDraft({ ...draft, slug: event.target.value })} />
            </Field>
            <Field label={t("sourceCategory")}>
              <NativeSelect
                value={String(draft.source)}
                onChange={(event) => setDraft({ ...draft, source: Number(event.target.value) })}
              >
                {(categories.list.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name_ru || row.name_en}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label={t("pageSlug")}>
              <Input
                value={draft[`page_slug_${locale}`]}
                onChange={(event) =>
                  setDraft({ ...draft, [`page_slug_${locale}`]: event.target.value })
                }
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
            <CheckboxField
              label={t("active")}
              checked={draft.is_active}
              onChange={(checked) => setDraft({ ...draft, is_active: checked })}
            />
          </div>
          {draft.id !== null ? (
            <div className="mt-6 grid gap-3">
              <p className="font-medium text-[var(--ink)]">{t("landingImage")}</p>
              {(() => {
                const row = (landings.list.data ?? []).find((item) => item.id === draft.id);
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
