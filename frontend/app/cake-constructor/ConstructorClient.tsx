"use client";

import dynamic from "next/dynamic";
import { useRef, useState, type ChangeEvent } from "react";
import { useTranslations } from "next-intl";
import { ImagePlus, Trash2, Type } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { PRESET_ILLUSTRATIONS } from "@/components/constructor/presets";
import { cakeScriptFont } from "@/components/constructor/cakeFont";
import { clampToCake, type Decoration } from "@/components/constructor/types";

const CakeScene = dynamic(() => import("@/components/constructor/CakeScene"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[var(--cream)]">
      <Spinner className="h-6 w-6 text-[var(--brand)]" />
    </div>
  ),
});

function newId(): string {
  return crypto.randomUUID();
}

export default function ConstructorClient() {
  const t = useTranslations("constructor");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [decorations, setDecorations] = useState<Decoration[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showPresets, setShowPresets] = useState(false);

  const selected = decorations.find((item) => item.id === selectedId) ?? null;

  function addText() {
    const id = newId();
    const decoration: Decoration = {
      id,
      kind: "text",
      text: t("defaultText"),
      x: 0,
      y: 0.35,
      scale: 1,
    };
    setDecorations((prev) => [...prev, decoration]);
    setSelectedId(id);
    setShowPresets(false);
  }

  function addImage(src: string) {
    const id = newId();
    const decoration: Decoration = {
      id,
      kind: "image",
      src,
      x: 0,
      y: -0.25,
      scale: 1,
    };
    setDecorations((prev) => [...prev, decoration]);
    setSelectedId(id);
    setShowPresets(false);
  }

  function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const src = URL.createObjectURL(file);
    addImage(src);
    event.target.value = "";
  }

  function onMove(id: string, x: number, y: number) {
    const [cx, cy] = clampToCake(x, y);
    setDecorations((prev) =>
      prev.map((item) => (item.id === id ? { ...item, x: cx, y: cy } : item)),
    );
  }

  function updateSelectedText(text: string) {
    if (!selectedId) {
      return;
    }
    setDecorations((prev) =>
      prev.map((item) =>
        item.id === selectedId && item.kind === "text" ? { ...item, text } : item,
      ),
    );
  }

  function updateSelectedScale(scale: number) {
    if (!selectedId) {
      return;
    }
    setDecorations((prev) =>
      prev.map((item) => (item.id === selectedId ? { ...item, scale } : item)),
    );
  }

  function removeSelected() {
    if (!selectedId) {
      return;
    }
    setDecorations((prev) => prev.filter((item) => item.id !== selectedId));
    setSelectedId(null);
  }

  return (
    <div className={`mx-auto w-full max-w-[1400px] px-4 py-6 md:px-6 md:py-10 ${cakeScriptFont.className}`}>
      <div className="mb-5 md:mb-6">
        <h1 className="font-display text-3xl tracking-tight text-[var(--ink)] md:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--ink)]/80 md:text-base">{t("subtitle")}</p>
      </div>

      <div className="flex flex-col gap-5 md:flex-row md:items-stretch md:gap-6">
        <div className="h-[50vh] min-h-[280px] w-full overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--cream)] md:h-auto md:min-h-[70vh] md:w-[62%]">
          <CakeScene
            decorations={decorations}
            selectedId={selectedId}
            isDragging={isDragging}
            onSelect={setSelectedId}
            onMove={onMove}
            onDragChange={setIsDragging}
          />
        </div>

        <div className="flex w-full flex-col gap-4 md:w-[38%]">
          <div className="rounded-3xl border border-[var(--line)] bg-white p-4 md:p-5">
            <p className="mb-3 text-sm text-[var(--ink)]/70">{t("hint")}</p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="primary" size="sm" onClick={addText}>
                <Type className="mr-2 h-4 w-4" />
                {t("addText")}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowPresets((open) => !open)}
              >
                <ImagePlus className="mr-2 h-4 w-4" />
                {t("addIllustration")}
              </Button>
            </div>

            {showPresets ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm font-medium text-[var(--ink)]">{t("choosePreset")}</p>
                <div className="grid grid-cols-4 gap-2">
                  {PRESET_ILLUSTRATIONS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className="aspect-square overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--cream)] transition hover:border-[var(--brand)]"
                      onClick={() => addImage(preset.src)}
                    >
                      <img
                        src={preset.src}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    </button>
                  ))}
                </div>
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={onUpload}
                  />
                  <Button
                    type="button"
                    variant="soft"
                    size="sm"
                    className="w-full"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {t("uploadOwn")}
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          {selected ? (
            <div className="rounded-3xl border border-[var(--line)] bg-white p-4 md:p-5">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-[var(--ink)]">
                  {selected.kind === "text" ? t("editText") : t("editIllustration")}
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("delete")}
                  onClick={removeSelected}
                >
                  <Trash2 className="h-4 w-4 text-[var(--danger)]" />
                </Button>
              </div>

              {selected.kind === "text" ? (
                <Input
                  value={selected.text}
                  onChange={(event) => updateSelectedText(event.target.value)}
                  placeholder={t("textPlaceholder")}
                />
              ) : null}

              <div className="mt-4">
                <label className="mb-2 block text-sm text-[var(--ink)]/80" htmlFor="decoration-scale">
                  {t("scale")}
                </label>
                <input
                  id="decoration-scale"
                  type="range"
                  min={0.5}
                  max={2}
                  step={0.05}
                  value={selected.scale}
                  onChange={(event) => updateSelectedScale(Number(event.target.value))}
                  className="w-full accent-[var(--brand)]"
                />
              </div>
            </div>
          ) : (
            <div className="rounded-3xl border border-dashed border-[var(--line)] bg-white/60 p-4 text-sm text-[var(--ink)]/70 md:p-5">
              {t("selectHint")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
