"use client";

import { useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { ExternalLink, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { DeliveryTierSelect } from "@/components/site/DeliveryTierSelect";
import { LocaleTabs, type SiteLocale } from "@/components/site/LocaleTabs";
import { ProductImagesEditor } from "@/components/site/ProductImagesEditor";
import { VisibilitySelect } from "@/components/site/VisibilitySelect";
import { useCan } from "@/hooks/useAuth";
import {
  matchesVisibility,
  useSiteCategories,
  useSiteOptionGroups,
  useSiteProductDetail,
  useSiteProducts,
  useSiteTechCards,
  useVisibility,
} from "@/hooks/useSite";
import { Link } from "@/i18n/navigation";
import { ApiError } from "@/lib/api/client";
import type { SiteProduct, SiteProductBody, SiteProductListItem } from "@/lib/api/site-schemas";

type ProductDraft = SiteProductBody & { id: number | null };

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function draftFrom(row: SiteProduct | null, categories: { id: number }[]): ProductDraft {
  if (row === null) {
    return {
      id: null,
      slug: "",
      name_en: "",
      name_ka: "",
      name_ru: "",
      description_en: "",
      description_ka: "",
      description_ru: "",
      base_price: "0",
      category: categories[0]?.id ?? 0,
      delivery_schedule_tier: null,
      tech_card: null,
      position: 0,
      is_active: true,
      option_groups: [],
    };
  }
  return {
    id: row.id,
    slug: row.slug,
    name_en: row.name_en,
    name_ka: row.name_ka,
    name_ru: row.name_ru,
    description_en: row.description_en,
    description_ka: row.description_ka,
    description_ru: row.description_ru,
    base_price: row.base_price,
    category: row.category,
    delivery_schedule_tier: row.delivery_schedule_tier,
    tech_card: row.tech_card,
    position: row.position,
    is_active: row.is_active,
    option_groups: row.option_groups.map((link) => ({
      option_group: link.option_group,
      position: link.position,
      is_required: link.is_required,
    })),
  };
}

function deletePreview(error: unknown): { labels: string[]; total: number } | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const body = error.parsed<{ related: { label: string }[]; related_total: number }>();
  if (body === null || !Array.isArray(body.related) || typeof body.related_total !== "number") return null;
  return {
    labels: body.related.map((row) => row.label),
    total: body.related_total,
  };
}

function displayName(row: SiteProductListItem, locale: SiteLocale): string {
  if (locale === "en") return row.name_en;
  if (locale === "ka") return row.name_ka;
  return row.name_ru;
}

export function ProductsPanel() {
  const t = useTranslations("site");
  const canEdit = useCan("edit_catalog");
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | undefined>(undefined);
  const visibility = useVisibility();
  const categories = useSiteCategories();
  const optionGroups = useSiteOptionGroups();
  const techCards = useSiteTechCards();
  const products = useSiteProducts({ category: categoryFilter, search });
  const visibleCategories = (categories.list.data ?? []).filter((row) =>
    matchesVisibility(row.is_active, visibility),
  );
  const visibleProducts = (products.list.data ?? []).filter((row) =>
    matchesVisibility(row.is_active, visibility),
  );
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ProductDraft | null>(null);
  const [imageError, setImageError] = useState<unknown>(null);
  const [deletePrompt, setDeletePrompt] = useState<{
    id: number;
    labels: string[];
    total: number;
  } | null>(null);
  const detail = useSiteProductDetail(editingId);
  const flushImagesRef = useRef<((targetId: number) => Promise<void>) | null>(null);

  const open = (row: SiteProductListItem | null) => {
    products.save.reset();
    products.remove.reset();
    setDeletePrompt(null);
    if (row === null) {
      setEditingId(null);
      setDraft(draftFrom(null, categories.list.data ?? []));
      return;
    }
    setEditingId(row.id);
    setDraft(null);
  };

  const close = () => {
    setEditingId(null);
    setDraft(null);
    setDeletePrompt(null);
  };

  const activeDraft = useMemo(() => {
    if (draft) return draft;
    if (detail.data) return draftFrom(detail.data, categories.list.data ?? []);
    return null;
  }, [draft, detail.data, categories.list.data]);

  const orderedOptionGroups = useMemo(() => {
    const groups = optionGroups.list.data ?? [];
    if (!activeDraft) return groups;
    const attached = new Set(activeDraft.option_groups.map((link) => link.option_group));
    const byId = new Map(groups.map((group) => [group.id, group]));
    return [
      ...activeDraft.option_groups.flatMap((link) => {
        const group = byId.get(link.option_group);
        return group ? [group] : [];
      }),
      ...groups.filter((group) => !attached.has(group.id)),
    ];
  }, [optionGroups.list.data, activeDraft]);

  const productDetail = detail.data;

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <CardTitle>{t("products")}</CardTitle>
          {canEdit ? (
            <Button type="button" size="sm" onClick={() => open(null)}>
              <Plus className="mr-1 h-4 w-4" />
              {t("newProduct")}
            </Button>
          ) : null}
        </div>
        <div className="mt-4 grid items-end gap-3 sm:grid-cols-3">
          <Field label={t("search")}>
            <Input value={search} onChange={(event) => setSearch(event.target.value)} />
          </Field>
          <Field label={t("category")}>
            <NativeSelect
              value={categoryFilter ?? ""}
              onChange={(event) => {
                const raw = event.target.value;
                setCategoryFilter(raw === "" ? undefined : Number(raw));
              }}
            >
              <option value="">{t("allCategories")}</option>
              {visibleCategories.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name_ru || row.name_en}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <VisibilitySelect />
        </div>
        <QueryState isLoading={products.list.isLoading} isError={products.list.isError}>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {visibleProducts.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="rounded-2xl border border-[var(--line)] bg-white p-4 text-left hover:bg-[var(--cream)]"
              >
                <div className="aspect-square w-full overflow-hidden bg-[var(--cream)]">
                  {row.primary_image ? (
                    <img
                      src={row.primary_image.src}
                      srcSet={row.primary_image.srcset}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : null}
                </div>
                <div className="mt-3 flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-[var(--ink)]">{displayName(row, locale)}</p>
                    <p className="text-sm text-[var(--muted-2)]">{row.category_name}</p>
                  </div>
                  {!row.is_active ? (
                    <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--muted-2)]">
                      {t("inactive")}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-sm text-[var(--ink)]">{row.base_price} GEL</p>
              </button>
            ))}
          </div>
        </QueryState>
      </Card>

      {draft !== null || editingId !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={
            !activeDraft
              ? t("newProduct")
              : activeDraft.id === null
                ? t("newProduct")
                : activeDraft.slug
          }
          pending={products.save.isPending || (editingId !== null && detail.isLoading)}
          error={
            imageError ??
            products.save.error ??
            (deletePreview(products.remove.error) ? null : products.remove.error) ??
            detail.error
          }
          submitLabel={canEdit && activeDraft ? t("save") : null}
          onSubmit={() => {
            if (!activeDraft) return;
            const body: SiteProductBody = {
              slug: activeDraft.slug,
              name_en: activeDraft.name_en,
              name_ka: activeDraft.name_ka,
              name_ru: activeDraft.name_ru,
              description_en: activeDraft.description_en,
              description_ka: activeDraft.description_ka,
              description_ru: activeDraft.description_ru,
              base_price: activeDraft.base_price,
              category: activeDraft.category,
              delivery_schedule_tier: activeDraft.delivery_schedule_tier,
              tech_card: activeDraft.tech_card,
              position: activeDraft.position,
              is_active: activeDraft.is_active,
              option_groups: activeDraft.option_groups,
            };
            setImageError(null);
            void (async () => {
              const saved = await products.save.mutateAsync({ id: activeDraft.id, body });
              await flushImagesRef.current?.(saved.id);
              if (activeDraft.id === null) {
                setEditingId(saved.id);
                setDraft(null);
              } else {
                close();
              }
            })().catch((error: unknown) => setImageError(error));
          }}
          onDelete={
            canEdit && activeDraft !== null && activeDraft.id !== null
              ? () => {
                  const id = activeDraft.id as number;
                  setDeletePrompt(null);
                  products.remove.mutate(
                    { id, confirm: false },
                    {
                      onError: (error) => {
                        const preview = deletePreview(error);
                        if (preview) {
                          setDeletePrompt({ id, labels: preview.labels, total: preview.total });
                        }
                      },
                    },
                  );
                }
              : null
          }
          deletePending={products.remove.isPending}
          headerAction={
            activeDraft !== null && activeDraft.id !== null ? (
              <Button type="button" size="sm" variant="outline" asChild>
                <Link href={`/order/${activeDraft.slug}`} target="_blank">
                  <ExternalLink className="mr-1 h-4 w-4" />
                  {t("openOnSite")}
                </Link>
              </Button>
            ) : null
          }
          below={null}
        >
          {!activeDraft ? (
            <p className="text-sm text-[var(--muted-2)]">{t("loading")}</p>
          ) : (
          <>
          <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label={t("name")}>
              <Input
                required
                name={`name_${locale}`}
                value={activeDraft[`name_${locale}`]}
                onChange={(event) => {
                  const value = event.target.value;
                  setDraft((row) => {
                    const base = row ?? activeDraft;
                    const next = { ...base, [`name_${locale}`]: value };
                    if (locale === "en" && base.id === null && base.slug === slugify(base.name_en)) {
                      next.slug = slugify(value);
                    }
                    return next;
                  });
                }}
              />
              {(["en", "ka", "ru"] as const)
                .filter((code) => code !== locale)
                .map((code) => (
                  <input
                    key={code}
                    required
                    name={`name_${code}`}
                    value={activeDraft[`name_${code}`]}
                    placeholder={`${t("name")} ${code.toUpperCase()}`}
                    onChange={() => undefined}
                    tabIndex={-1}
                    className="sr-only"
                  />
                ))}
            </Field>
            <Field label={t("slug")}>
              <Input
                name="slug"
                required
                value={activeDraft.slug}
                onChange={(event) =>
                  setDraft((row) => ({ ...(row ?? activeDraft), slug: event.target.value }))
                }
              />
            </Field>
            <Field label={t("category")} className="sm:col-span-2">
              <NativeSelect
                name="category"
                required
                value={activeDraft.category === 0 ? "" : String(activeDraft.category)}
                onChange={(event) =>
                  setDraft((row) => ({
                    ...(row ?? activeDraft),
                    category: Number(event.target.value),
                  }))
                }
              >
                <option value="">{t("category")}</option>
                {(categories.list.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name_ru || row.name_en}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label={t("description")} className="sm:col-span-2">
              <Textarea
                rows={4}
                value={activeDraft[`description_${locale}`]}
                onChange={(event) =>
                  setDraft((row) => ({
                    ...(row ?? activeDraft),
                    [`description_${locale}`]: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label={t("price")}>
              <Input
                name="base_price"
                required
                inputMode="decimal"
                value={activeDraft.base_price}
                onChange={(event) =>
                  setDraft((row) => ({ ...(row ?? activeDraft), base_price: event.target.value }))
                }
              />
            </Field>
            <Field label={t("position")}>
              <Input
                type="number"
                value={activeDraft.position}
                onChange={(event) =>
                  setDraft((row) => ({
                    ...(row ?? activeDraft),
                    position: Number(event.target.value),
                  }))
                }
              />
            </Field>
            <Field label={t("deliveryTier")}>
              <DeliveryTierSelect
                allowEmpty
                value={activeDraft.delivery_schedule_tier}
                onChange={(value) =>
                  setDraft((row) => ({ ...(row ?? activeDraft), delivery_schedule_tier: value }))
                }
              />
            </Field>
            <Field label={t("techCard")}>
              <NativeSelect
                value={activeDraft.tech_card ?? ""}
                onChange={(event) =>
                  setDraft((row) => ({
                    ...(row ?? activeDraft),
                    tech_card: event.target.value === "" ? null : Number(event.target.value),
                  }))
                }
              >
                <option value="">{t("noTechCard")}</option>
                {(techCards.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <CheckboxField
              label={t("active")}
              checked={activeDraft.is_active}
              onChange={(checked) =>
                setDraft((row) => ({ ...(row ?? activeDraft), is_active: checked }))
              }
            />
          </div>
          <div className="mt-6 grid gap-3">
            <p className="font-medium text-[var(--ink)]">{t("optionGroups")}</p>
            {orderedOptionGroups.map((group) => {
              const link = activeDraft.option_groups.find((row) => row.option_group === group.id);
              const enabled = link !== undefined;
              return (
                <div
                  key={group.id}
                  className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--line)] px-3 py-2"
                >
                  <CheckboxField
                    label={group.name_ru || group.name_en}
                    checked={enabled}
                    onChange={(checked) => {
                      setDraft((row) => {
                        const base = row ?? activeDraft;
                        if (!checked) {
                          return {
                            ...base,
                            option_groups: base.option_groups.filter(
                              (item) => item.option_group !== group.id,
                            ),
                          };
                        }
                        if (base.option_groups.some((item) => item.option_group === group.id)) {
                          return base;
                        }
                        return {
                          ...base,
                          option_groups: [
                            ...base.option_groups,
                            {
                              option_group: group.id,
                              position: base.option_groups.length,
                              is_required: null,
                            },
                          ],
                        };
                      });
                    }}
                  />
                  {enabled ? (
                    <CheckboxField
                      label={t("requiredOverride")}
                      checked={link?.is_required === true}
                      onChange={(checked) =>
                        setDraft((row) => {
                          const base = row ?? activeDraft;
                          return {
                            ...base,
                            option_groups: base.option_groups.map((item) =>
                              item.option_group === group.id
                                ? { ...item, is_required: checked ? true : null }
                                : item,
                            ),
                          };
                        })
                      }
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
          <div className="mt-8 border-t border-[var(--line)] pt-6">
            <ProductImagesEditor
              productId={activeDraft.id}
              images={productDetail?.images ?? []}
              productName={activeDraft[`name_${locale}`]}
              price={activeDraft.base_price}
              canEdit={canEdit}
              onRefresh={() => detail.refetch()}
              flushRef={flushImagesRef}
            />
          </div>
          {deletePrompt !== null ? (
            <div className="mt-6 grid gap-3 rounded-2xl border border-[var(--line)] p-4">
              {deletePrompt.total > 0 ? (
                <>
                  <p className="font-medium text-[var(--ink)]">{t("deleteRelatedTitle")}</p>
                  <ul className="grid gap-1 text-sm text-[var(--ink)]">
                    {deletePrompt.labels.map((label, index) => (
                      <li key={`${label}-${index}`}>{label}</li>
                    ))}
                  </ul>
                  {deletePrompt.total > deletePrompt.labels.length ? (
                    <p className="text-sm text-[var(--muted-2)]">
                      {t("deleteRelatedMore", {
                        count: deletePrompt.total - deletePrompt.labels.length,
                      })}
                    </p>
                  ) : null}
                  <p className="text-sm text-[var(--ink)]">{t("deleteRelatedConfirm")}</p>
                </>
              ) : (
                <p className="text-sm text-[var(--ink)]">{t("deleteConfirmQuestion")}</p>
              )}
              <div className="flex gap-2">
                <Button
                  type="button"
                  onClick={() =>
                    products.remove.mutate(
                      { id: deletePrompt.id, confirm: true },
                      { onSuccess: close },
                    )
                  }
                  disabled={products.remove.isPending}
                >
                  {products.remove.isPending ? <Spinner className="h-4 w-4" /> : t("confirmDelete")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDeletePrompt(null)}
                  disabled={products.remove.isPending}
                >
                  {t("cancelDelete")}
                </Button>
              </div>
            </div>
          ) : null}
          </>
          )}
        </EditorDialog>
      ) : null}
    </div>
  );
}
