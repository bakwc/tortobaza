"use client";

import { useRef, useState } from "react";
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

export function ProductImagesEditor({
  productId,
  images,
  productName,
  price,
  canEdit,
  onRefresh,
}: {
  productId: number;
  images: SiteProductImage[];
  productName: string;
  price: string;
  canEdit: boolean;
  onRefresh: () => void;
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

  const sorted = [...images].sort((a, b) => a.position - b.position || a.id - b.id);
  const activeImage = sorted.find((row) => row.id === activeId) ?? null;
  const activePending = pending.find((row) => row.key === pendingKey) ?? null;

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

  const uploadPending = (row: PendingUpload) => {
    mutations.upload.mutate(
      {
        file: row.file,
        fields: {
          alt_en: row.alt_en,
          alt_ka: row.alt_ka,
          alt_ru: row.alt_ru,
          crop_left: row.crop.crop_left,
          crop_top: row.crop.crop_top,
          crop_size: row.crop.crop_size,
        },
      },
      {
        onSuccess: () => {
          URL.revokeObjectURL(row.url);
          setPending((rows) => rows.filter((item) => item.key !== row.key));
          setPendingKey(null);
          onRefresh();
        },
      },
    );
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
    : {
        crop_left: activeImage?.crop_left ?? 0,
        crop_top: activeImage?.crop_top ?? 0,
        crop_size: activeImage?.crop_size ?? 1,
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
                      mutations.patch.mutate(
                        {
                          imageId: activeImage.id,
                          body: {
                            crop_left: crop.crop_left,
                            crop_top: crop.crop_top,
                            crop_size: crop.crop_size,
                          },
                        },
                        { onSuccess: onRefresh },
                      );
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
                {activePending ? (
                  <Button type="button" onClick={() => uploadPending(activePending)}>
                    {t("uploadImage")}
                  </Button>
                ) : null}
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
