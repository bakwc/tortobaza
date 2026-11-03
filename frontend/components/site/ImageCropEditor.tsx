"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/menu/ui";
import {
  centerCrop,
  cropPreviewStyle,
  panCrop,
  zoomCrop,
  type CropValues,
} from "@/lib/site/crop";

export function ImageCropEditor({
  src,
  width,
  height,
  crop,
  onChange,
}: {
  src: string;
  width: number;
  height: number;
  crop: CropValues;
  onChange: (value: CropValues) => void;
}) {
  const t = useTranslations("site");
  const frameRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ x: number; y: number; crop: CropValues } | null>(null);
  const [frameSize, setFrameSize] = useState(280);

  useEffect(() => {
    const node = frameRef.current;
    if (!node) return;
    const observer = new ResizeObserver(() => {
      setFrameSize(node.clientWidth);
    });
    observer.observe(node);
    setFrameSize(node.clientWidth);
    return () => observer.disconnect();
  }, []);

  const preview = cropPreviewStyle(width, height, crop, frameSize);
  const zoom = 1 / crop.crop_size;

  return (
    <div className="grid gap-3">
      <div
        ref={frameRef}
        className="relative aspect-square w-full max-w-sm touch-none cursor-grab overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--cream)] active:cursor-grabbing"
        onPointerDown={(event) => {
          dragRef.current = { x: event.clientX, y: event.clientY, crop };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!dragRef.current) return;
          onChange(
            panCrop(
              width,
              height,
              dragRef.current.crop,
              event.clientX - dragRef.current.x,
              event.clientY - dragRef.current.y,
              frameSize,
            ),
          );
        }}
        onPointerUp={(event) => {
          dragRef.current = null;
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => {
          dragRef.current = null;
        }}
      >
        <img
          src={src}
          alt=""
          draggable={false}
          className="absolute left-0 top-0 max-w-none select-none"
          style={{
            width: preview.width,
            height: preview.height,
            transform: preview.transform,
          }}
        />
      </div>
      <Field label={t("cropZoom")}>
        <Input
          type="range"
          min={1}
          max={5}
          step={0.01}
          value={zoom}
          onChange={(event) =>
            onChange(zoomCrop(width, height, crop, 1 / Number(event.target.value)))
          }
        />
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" onClick={() => onChange(centerCrop(crop))}>
          {t("cropCenter")}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onChange({ crop_left: 0.5, crop_top: 0.5, crop_size: 1 })}
        >
          {t("cropFit")}
        </Button>
      </div>
    </div>
  );
}

export function loadImageSize(file: File): Promise<{ width: number; height: number; url: string }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight, url });
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("image load failed"));
    };
    img.src = url;
  });
}
