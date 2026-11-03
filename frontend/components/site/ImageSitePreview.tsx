"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { cropPreviewStyle, type CropValues } from "@/lib/site/crop";
import { formatAed } from "@/lib/format";

function useRefSize() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new ResizeObserver(() => setWidth(node.clientWidth));
    observer.observe(node);
    setWidth(node.clientWidth);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

function CroppedFrame({
  src,
  width,
  height,
  crop,
  className,
  rounded,
}: {
  src: string;
  width: number;
  height: number;
  crop: CropValues;
  className: string;
  rounded?: string;
}) {
  const frameRef = useRefSize();
  const size = frameRef.width || 160;
  const preview = cropPreviewStyle(width, height, crop, size);
  return (
    <div ref={frameRef.ref} className={`relative overflow-hidden bg-[var(--cream)] ${className} ${rounded ?? ""}`}>
      <img
        src={src}
        alt=""
        className="absolute left-0 top-0 max-w-none"
        style={{
          width: preview.width,
          height: preview.height,
          transform: preview.transform,
        }}
      />
    </div>
  );
}

export function ImageSitePreview({
  src,
  width,
  height,
  crop,
  productName,
  price,
}: {
  src: string;
  width: number;
  height: number;
  crop: CropValues;
  productName: string;
  price: string;
}) {
  const t = useTranslations("site");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-2)]">
          {t("previewCard")}
        </p>
        <div className="max-w-[220px] bg-white p-4">
          <CroppedFrame
            src={src}
            width={width}
            height={height}
            crop={crop}
            className="aspect-square w-full"
          />
          <h3 className="mt-4 text-lg text-[#666]">{productName || "—"}</h3>
          <div className="mt-4">
            <span className="inline-flex h-9 w-full items-center justify-center rounded-full bg-product-price-btn px-4 text-sm text-white">
              {formatAed(price || "0")}
            </span>
          </div>
        </div>
      </div>
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-2)]">
          {t("previewProductPage")}
        </p>
        <CroppedFrame
          src={src}
          width={width}
          height={height}
          crop={crop}
          className="aspect-square w-full max-w-xs"
          rounded="rounded-3xl"
        />
        <p className="mt-3 text-xs font-medium uppercase tracking-wide text-[var(--muted-2)]">
          {t("previewCart")}
        </p>
        <CroppedFrame
          src={src}
          width={width}
          height={height}
          crop={crop}
          className="mt-2 h-16 w-16"
          rounded="rounded-xl"
        />
      </div>
    </div>
  );
}

export function OptionImagePreview({
  src,
  width,
  height,
  crop,
  label,
}: {
  src: string;
  width: number;
  height: number;
  crop: CropValues;
  label: string;
}) {
  const t = useTranslations("site");
  return (
    <div className="max-w-[120px]">
      <p className="mb-1 text-xs text-[var(--muted-2)]">{t("previewOption")}</p>
      <CroppedFrame
        src={src}
        width={width}
        height={height}
        crop={crop}
        className="aspect-square w-full rounded-2xl border border-[var(--line)]"
      />
      <p className="mt-1 text-center text-xs text-[var(--muted-2)]">{label}</p>
    </div>
  );
}
