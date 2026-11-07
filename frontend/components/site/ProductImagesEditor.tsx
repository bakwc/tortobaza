"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/menu/ui";
import { ImageCropEditor, loadImageSize } from "@/components/site/ImageCropEditor";
import { ImageSitePreview } from "@/components/site/ImageSitePreview";
import { LocaleTabs, type SiteLocale } from "@/components/site/LocaleTabs";
import { useSiteProductImages } from "@/hooks/useSite";
import { defaultCenterCrop, type CropValues } from "@/lib/site/crop";
import type { SiteProductImage } from "@/lib/api/site-schemas";

type PendingUpload = {
  key: string;
  file: File;
  url: string;
  width: number;
  height: number;
  crop: CropValues;
  alt_en: string;
  alt_ka: string;
  alt_ru: string;
};

function cropFromImage(row: SiteProductImage): CropValues {
  return {
    crop_left: row.crop_left ?? 0,
    crop_top: row.crop_top ?? 0,
    crop_size: row.crop_size ?? 1,
  };
}

export function ProductImagesEditor({
  productId,
  images,
  productName,
  price,
  canEdit,
  onRefresh,
  flushRef,
}: {
  productId: number | null;
  images: SiteProductImage[];
  productName: string;
  price: string;
  canEdit: boolean;
  onRefresh: () => void;
  flushRef: RefObject<((targetId: number) => Promise<void>) | null>;
}) {
  const t = useTranslations("site");
  const fileRef = useRef<HTMLInputElement>(null);
  const mutations = useSiteProductImages(productId);
  const [locale, setLocale] = useState<SiteLocale>("ru");
  const [activeId, setActiveId] = useState<number | "pending" | null>(
    images[0]?.id ?? null,
  );
  const [pending, setPending] = useState<PendingUpload[]>([]);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [cropDrafts, setCropDrafts] = useState<Record<number, CropValues>>({});
  const pendingRef = useRef(pending);
  pendingRef.current = pending;
  const cropDraftsRef = useRef(cropDrafts);
  cropDraftsRef.current = cropDrafts;
  const debounceTimersRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const sorted = [...images].sort((a, b) => a.position - b.position || a.id - b.id);
  const activeImage = sorted.find((row) => row.id === activeId) ?? null;
  const activePending = pending.find((row) => row.key === pendingKey) ?? null;

  const scheduleCropSave = useCallback(
    (imageId: number, crop: CropValues) => {
      const existing = debounceTimersRef.current[imageId];
      if (existing) clearTimeout(existing);
      debounceTimersRef.current[imageId] = setTimeout(() => {
        delete debounceTimersRef.current[imageId];
        const sent = crop;
        void mutations.patch
          .mutateAsync({
            imageId,
            body: {
              crop_left: sent.crop_left,
              crop_top: sent.crop_top,
              crop_size: sent.crop_size,
            },
          })
          .then(() => {
            onRefresh();
            setCropDrafts((prev) => {
              const current = prev[imageId];
              if (
                current &&
                current.crop_left === sent.crop_left &&
                current.crop_top === sent.crop_top &&
                current.crop_size === sent.crop_size
              ) {
                const next = { ...prev };
                delete next[imageId];
                return next;
              }
              return prev;
            });
          });
      }, 600);
    },
    [mutations.patch, onRefresh],
  );

  const flush = useCallback(async (targetId: number) => {
    const rows = pendingRef.current;
    for (const row of rows) {
      await mutations.upload.mutateAsync({
        targetId,
        file: row.file,
        fields: {
          alt_en: row.alt_en,
          alt_ka: row.alt_ka,
          alt_ru: row.alt_ru,
          crop_left: row.crop.crop_left,
          crop_top: row.crop.crop_top,
          crop_size: row.crop.crop_size,
        },
      });
      URL.revokeObjectURL(row.url);
    }
    if (rows.length > 0) {
      const uploaded = new Set(rows.map((row) => row.key));
      setPending((current) => current.filter((item) => !uploaded.has(item.key)));
      setPendingKey(null);
    }
    for (const imageId of Object.keys(debounceTimersRef.current)) {
      clearTimeout(debounceTimersRef.current[Number(imageId)]);
    }
    debounceTimersRef.current = {};
    const drafts = cropDraftsRef.current;
    const entries = Object.entries(drafts);
    if (entries.length > 0) {
      await Promise.all(
        entries.map(([imageId, crop]) =>
          mutations.patch.mutateAsync({
            imageId: Number(imageId),
            body: {
              crop_left: crop.crop_left,
              crop_top: crop.crop_top,
              crop_size: crop.crop_size,
            },
          }),
        ),
      );
      setCropDrafts((prev) => {
        const next = { ...prev };
        for (const [imageId, crop] of entries) {
          const id = Number(imageId);
          const current = next[id];
          if (
            current &&
            current.crop_left === crop.crop_left &&
            current.crop_top === crop.crop_top &&
            current.crop_size === crop.crop_size
          ) {
            delete next[id];
          }
        }
        return next;
      });
    }
  }, [mutations.upload, mutations.patch]);

  useEffect(() => {
    flushRef.current = flush;
    return () => {
      flushRef.current = null;
    };
  }, [flush, flushRef]);

  const pickFiles = async (files: FileList | null) => {
    if (!files || !canEdit) return;
    const next: PendingUpload[] = [];
    for (const file of Array.from(files)) {
      const loaded = await loadImageSize(file);
      next.push({
        key: `${file.name}-${file.size}-${loaded.url}`,
        file,
        url: loaded.url,
        width: loaded.width,
        height: loaded.height,
        crop: defaultCenterCrop(loaded.width, loaded.height),
        alt_en: "",
        alt_ka: "",
        alt_ru: "",
      });
    }
    setPending((rows) => [...rows, ...next]);
    if (next[0]) {
      setActiveId(null);
      setPendingKey(next[0].key);
    }
  };

  const move = (id: number, direction: -1 | 1) => {
    const ids = sorted.map((row) => row.id);
    const index = ids.indexOf(id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ids.length) return;
    const swapped = [...ids];
    swapped[index] = ids[target];
    swapped[target] = ids[index];
    mutations.reorder.mutate(swapped, { onSuccess: onRefresh });
  };

  const previewSrc =
    activePending?.url ??
    activeImage?.image.original.src ??
    sorted[0]?.image.cropped.src ??
    null;
  const previewWidth = activePending?.width ?? activeImage?.image.width ?? 1;
  const previewHeight = activePending?.height ?? activeImage?.image.height ?? 1;
  const previewCrop: CropValues = activePending
    ? activePending.crop
    : activeImage
      ? (cropDrafts[activeImage.id] ?? cropFromImage(activeImage))
      : {
          crop_left: 0,
          crop_top: 0,
          crop_size: 1,
        };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-[var(--ink)]">{t("productImages")}</p>
        {canEdit ? (
          <>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(event) => {
                void pickFiles(event.target.files);
                event.target.value = "";
              }}
            />
            <Button type="button" size="sm" onClick={() => fileRef.current?.click()}>
              {t("addImages")}
            </Button>
          </>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        {sorted.map((row) => (
          <div key={row.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => {
                setActiveId(row.id);
                setPendingKey(null);
              }}
              className={`h-16 w-16 overflow-hidden rounded-xl border ${
                activeId === row.id ? "border-[var(--brand)]" : "border-[var(--line)]"
              }`}
            >
              <img src={row.image.cropped.src} alt="" className="h-full w-full object-cover" />
            </button>
            {canEdit ? (
              <>
                <Button type="button" size="sm" variant="outline" onClick={() => move(row.id, -1)}>
                  <ChevronUp className="h-4 w-4" />
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={() => move(row.id, 1)}>
                  <ChevronDown className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => mutations.remove.mutate(row.id, { onSuccess: onRefresh })}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            ) : null}
          </div>
        ))}
        {pending.map((row) => (
          <button
            key={row.key}
            type="button"
            onClick={() => {
              setActiveId(null);
              setPendingKey(row.key);
            }}
            className={`h-16 w-16 overflow-hidden rounded-xl border border-dashed ${
              pendingKey === row.key ? "border-[var(--brand)]" : "border-[var(--line)]"
            }`}
          >
            <img src={row.url} alt="" className="h-full w-full object-cover" />
          </button>
        ))}
      </div>
      {previewSrc ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="grid gap-3">
            {canEdit ? (
              <>
                <ImageCropEditor
                  src={activePending?.url ?? activeImage?.image.original.src ?? previewSrc}
                  width={previewWidth}
                  height={previewHeight}
                  crop={previewCrop}
                  onChange={(crop) => {
                    if (activePending) {
                      setPending((rows) =>
                        rows.map((row) => (row.key === activePending.key ? { ...row, crop } : row)),
                      );
                      return;
                    }
                    if (activeImage) {
                      setCropDrafts((prev) => ({ ...prev, [activeImage.id]: crop }));
                      scheduleCropSave(activeImage.id, crop);
                    }
                  }}
                />
                <LocaleTabs locale={locale} onChange={setLocale} labels={{ en: "EN", ka: "KA", ru: "RU" }} />
                <Field label={t("imageAlt")}>
                  <Input
                    value={
                      activePending
                        ? activePending[`alt_${locale}`]
                        : activeImage?.[`alt_${locale}`] ?? ""
                    }
                    onChange={(event) => {
                      const value = event.target.value;
                      if (activePending) {
                        setPending((rows) =>
                          rows.map((row) =>
                            row.key === activePending.key ? { ...row, [`alt_${locale}`]: value } : row,
                          ),
                        );
                        return;
                      }
                      if (activeImage) {
                        mutations.patch.mutate(
                          { imageId: activeImage.id, body: { [`alt_${locale}`]: value } },
                          { onSuccess: onRefresh },
                        );
                      }
                    }}
                  />
                </Field>
              </>
            ) : null}
          </div>
          <ImageSitePreview
            src={activePending?.url ?? activeImage?.image.original.src ?? previewSrc}
            width={previewWidth}
            height={previewHeight}
            crop={previewCrop}
            productName={productName}
            price={price}
          />
        </div>
      ) : (
        <p className="text-sm text-[var(--muted-2)]">{t("noImages")}</p>
      )}
    </div>
  );
}
