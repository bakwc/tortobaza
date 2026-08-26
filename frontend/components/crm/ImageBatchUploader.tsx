"use client";

import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { useTranslations } from "next-intl";
import { ImagePlus, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function ImageBatchUploader({
  existing,
  newFiles,
  onAddFiles,
  onRemoveExisting,
  onRemoveNew,
}: {
  existing: { id: number; src: string; srcset: string }[];
  newFiles: File[];
  onAddFiles: (files: File[]) => void;
  onRemoveExisting: (id: number) => void;
  onRemoveNew: (index: number) => void;
}) {
  const t = useTranslations("crm");
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const previewUrls = useMemo(
    () => newFiles.map((file) => URL.createObjectURL(file)),
    [newFiles],
  );

  useEffect(() => {
    return () => {
      previewUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [previewUrls]);

  const takeFiles = (list: FileList | File[]) => {
    const files = Array.from(list).filter((file) => file.type.startsWith("image/"));
    if (files.length > 0) {
      onAddFiles(files);
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    takeFiles(event.dataTransfer.files);
  };

  return (
    <div className="grid gap-3">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors",
          isDragging
            ? "border-[var(--brand)] bg-[var(--cream)]"
            : "border-[var(--line)] bg-white hover:border-[var(--brand)]/40",
        )}
      >
        <ImagePlus className="h-8 w-8 text-[var(--brand)]" />
        <p className="text-sm font-medium text-[var(--ink)]">{t("imagesDrop")}</p>
        <p className="text-xs text-[var(--muted-2)]">{t("imagesHint")}</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(event) => {
            if (event.target.files) {
              takeFiles(event.target.files);
              event.target.value = "";
            }
          }}
        />
      </div>

      {existing.length > 0 || newFiles.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {existing.map((img) => (
            <div
              key={img.id}
              className="relative h-20 w-20 overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--cream)]"
            >
              <img
                src={img.src}
                srcSet={img.srcset}
                sizes="80px"
                alt=""
                className="h-full w-full object-cover"
              />
              <button
                type="button"
                onClick={() => onRemoveExisting(img.id)}
                className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/70 text-white"
                aria-label={t("imagesRemove")}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          {newFiles.map((file, index) => (
            <div
              key={`${file.name}-${file.size}-${index}`}
              className="relative h-20 w-20 overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--cream)]"
            >
              <img
                src={previewUrls[index]}
                alt={file.name}
                className="h-full w-full object-cover"
              />
              <button
                type="button"
                onClick={() => onRemoveNew(index)}
                className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/70 text-white"
                aria-label={t("imagesRemove")}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
