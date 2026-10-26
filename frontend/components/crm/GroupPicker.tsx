"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Field, NativeSelect } from "@/components/menu/ui";
import type { TechCardGroup } from "@/lib/api/types";
import type { CrmItemModifierDraft } from "@/lib/crmItems";
import { cn } from "@/lib/utils";

export function GroupPicker({
  group,
  selected,
  onChange,
}: {
  group: TechCardGroup;
  selected: CrmItemModifierDraft[];
  onChange: (rows: CrmItemModifierDraft[]) => void;
}) {
  const t = useTranslations("crm.items");
  const ids = new Set(group.modifiers.map((modifier) => modifier.id));
  const inGroup = selected.filter((row) => ids.has(row.modifier));
  const others = selected.filter((row) => !ids.has(row.modifier));
  const setQuantity = (modifier: number, quantity: string) =>
    onChange([...others, ...inGroup.map((row) => (row.modifier === modifier ? { ...row, quantity } : row))]);

  const label = `${group.group_name}${group.effective_is_required ? " *" : ""}`;

  if (group.selection_type === "single") {
    const current = inGroup[0];
    return (
      <Field label={label}>
        <div className="flex gap-2">
          <NativeSelect
            value={current ? String(current.modifier) : ""}
            onChange={(event) =>
              onChange(
                event.target.value === ""
                  ? others
                  : [...others, { modifier: Number(event.target.value), quantity: current?.quantity ?? "1" }],
              )
            }
          >
            <option value="">{t("notSelected")}</option>
            {group.modifiers.map((modifier) => (
              <option key={modifier.id} value={modifier.id}>
                {modifier.name}
              </option>
            ))}
          </NativeSelect>
          {current ? (
            <Input
              inputMode="numeric"
              aria-label={t("modifierQuantity")}
              value={current.quantity}
              onChange={(event) => setQuantity(current.modifier, event.target.value)}
              className="w-20"
            />
          ) : null}
        </div>
      </Field>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{label}</span>
      <div className="flex flex-wrap gap-2">
        {group.modifiers.map((modifier) => {
          const row = inGroup.find((item) => item.modifier === modifier.id);
          return (
            <div
              key={modifier.id}
              className={cn(
                "flex items-center gap-2 rounded-2xl border px-3 py-2 text-sm",
                row ? "border-[var(--brand)] bg-[var(--cream)]" : "border-[var(--line)]",
              )}
            >
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={row !== undefined}
                  onChange={(event) =>
                    onChange(
                      event.target.checked
                        ? [...selected, { modifier: modifier.id, quantity: "1" }]
                        : selected.filter((item) => item.modifier !== modifier.id),
                    )
                  }
                  className="h-4 w-4 accent-[var(--brand)]"
                />
                {modifier.name}
              </label>
              {row ? (
                <input
                  inputMode="numeric"
                  aria-label={t("modifierQuantity")}
                  value={row.quantity}
                  onChange={(event) => setQuantity(modifier.id, event.target.value)}
                  className="h-7 w-12 rounded-full border border-[var(--line)] px-2 text-center text-sm"
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
