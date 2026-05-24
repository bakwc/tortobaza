"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { formatPriceDelta } from "@/lib/format";
import type { OptionGroup as OptionGroupType } from "@/lib/api/types";

export type OptionSelection = Record<number, number[]>;

export function OptionGroup({
  group,
  selected,
  onChange,
}: {
  group: OptionGroupType;
  selected: number[];
  onChange: (next: number[]) => void;
}) {
  const tItem = useTranslations("item");

  const isSingle = group.selection_type === "single";
  const atMax =
    !isSingle &&
    group.max_selections !== null &&
    selected.length >= group.max_selections;

  const selectionHint = (() => {
    if (isSingle) return null;
    const { min_selections, max_selections } = group;
    if (min_selections > 0 && max_selections !== null) {
      if (min_selections === max_selections) {
        return tItem("chooseExact", { count: min_selections });
      }
      return tItem("chooseRange", { min: min_selections, max: max_selections });
    }
    if (max_selections !== null) {
      return tItem("chooseUpTo", { max: max_selections });
    }
    if (min_selections > 0) {
      return tItem("chooseAtLeast", { min: min_selections });
    }
    return null;
  })();

  const toggle = (optionId: number) => {
    if (isSingle) {
      onChange([optionId]);
      return;
    }
    if (selected.includes(optionId)) {
      onChange(selected.filter((id) => id !== optionId));
    } else if (group.max_selections === null || selected.length < group.max_selections) {
      onChange([...selected, optionId]);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h3 className="font-display text-2xl text-[var(--ink)]">{group.name}</h3>
          {selectionHint ? (
            <p className="mt-1 text-sm text-[var(--ink)]/60">{selectionHint}</p>
          ) : null}
        </div>
        {group.is_required ? (
          <span className="shrink-0 text-sm text-[var(--danger)]">{tItem("required")}</span>
        ) : null}
      </div>
      <ul className="space-y-1">
        {group.options.map((option) => {
          const isChecked = selected.includes(option.id);
          const isDisabled = atMax && !isChecked;
          return (
            <li key={option.id}>
              <label
                className={cn(
                  "flex items-center gap-4 py-3 transition-colors",
                  isDisabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
                  isChecked ? "text-[var(--ink)]" : "text-[var(--ink)]/90",
                )}
              >
                {option.image ? (
                  <span className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-[var(--cream)]">
                    <img
                      src={option.image.src}
                      srcSet={option.image.srcset}
                      sizes="48px"
                      alt={option.name}
                      className="h-full w-full object-cover"
                      loading="lazy"
                      decoding="async"
                    />
                  </span>
                ) : (
                  <span className="h-12 w-12 shrink-0 rounded-xl bg-[var(--cream)]" />
                )}
                <span className="flex-1">
                  <span className="block">{option.name}</span>
                  {Number.parseFloat(option.price_delta) !== 0 ? (
                    <span className="block text-xs text-[var(--ink)]/60">
                      {formatPriceDelta(option.price_delta)}
                    </span>
                  ) : null}
                </span>
                <span
                  aria-hidden="true"
                  className={cn(
                    "relative flex h-5 w-5 items-center justify-center border border-[var(--muted-2)]",
                    isSingle ? "rounded-full" : "rounded-md",
                    isChecked && "border-[var(--brand)]",
                  )}
                >
                  <input
                    type={isSingle ? "radio" : "checkbox"}
                    name={`group-${group.id}`}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
                    checked={isChecked}
                    disabled={isDisabled}
                    onChange={() => toggle(option.id)}
                  />
                  {isChecked ? (
                    <span
                      className={cn(
                        "bg-[var(--brand)]",
                        isSingle ? "h-2.5 w-2.5 rounded-full" : "h-3 w-3 rounded-sm",
                      )}
                    />
                  ) : null}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
