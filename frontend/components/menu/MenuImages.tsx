"use client";

import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardTitle } from "@/components/menu/ui";
import type { MenuImage } from "@/lib/api/types";

type MenuImagesProps = {
  images: MenuImage[];
  pending: boolean;
  onUpload: (file: File) => void;
  onDelete: (imageId: number) => void;
};

export function MenuImages({ images, pending, onUpload, onDelete }: MenuImagesProps) {
  const t = useTranslations("stock");
  return (
    <div className="grid gap-3">
      <CardTitle>{t("images")}</CardTitle>
      {images.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {images.map((row) => (
            <div key={row.id} className="relative">
              <img src={row.image.src} alt="" className="h-28 w-28 rounded-xl object-cover" />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t("removeImage")}
                className="absolute right-1 top-1 bg-white/90"
                disabled={pending}
                onClick={() => onDelete(row.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
      <label className="text-sm text-[var(--ink)]">
        {t("addImage")}
        <input
          type="file"
          accept="image/*"
          className="mt-1 block w-full text-sm"
          disabled={pending}
          onChange={(event) => {
            const files = event.target.files;
            event.target.value = "";
            if (files !== null && files.length > 0) onUpload(files[0]);
          }}
        />
      </label>
    </div>
  );
}
