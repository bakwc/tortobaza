"use client";

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
  const isSingle = group.selection_type === "single";

  const toggle = (optionId: number) => {
    if (isSingle) {
      onChange([optionId]);
      return;
    }
    if (selected.includes(optionId)) {
      onChange(selected.filter((id) => id !== optionId));
    } else {
      onChange([...selected, optionId]);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-2xl text-[var(--ink)]">{group.name}</h3>
        {group.is_required ? (
          <span className="text-sm text-[var(--danger)]">Required</span>
        ) : null}
      </div>
      <ul className="space-y-1">
        {group.options.map((option) => {
          const isChecked = selected.includes(option.id);
          return (
            <li key={option.id}>
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-4 py-3 transition-colors",
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
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    checked={isChecked}
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
