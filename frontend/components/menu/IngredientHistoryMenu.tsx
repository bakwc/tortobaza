"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { History, MoreHorizontal } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { useAuditEvents } from "@/hooks/useAuditEvents";
import type { AuditEvent, IngredientCategory, MenuUnit } from "@/lib/api/types";

const FIELDS = [
  "name",
  "category_id",
  "unit",
  "grams_per_unit",
  "avg_cost",
  "cost_quantity",
  "sale_price",
  "is_active",
] as const;

const FIELD_KEYS = {
  name: "name",
  category_id: "category",
  unit: "unit",
  grams_per_unit: "gramsPerUnit",
  avg_cost: "avgCost",
  cost_quantity: "costQuantity",
  sale_price: "salePrice",
  is_active: "isActive",
} as const;

const ACTION_KEYS = {
  created: "historyActionCreated",
  updated: "historyActionUpdated",
  deleted: "historyActionDeleted",
} as const;

const UNITS: readonly MenuUnit[] = ["g", "ml", "pcs"];

function historyLocale(locale: string): string {
  if (locale === "ka") return "ka-GE";
  if (locale === "ru") return "ru-RU";
  return "en-GB";
}

function formatWhen(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(historyLocale(locale), {
    timeZone: "Asia/Tbilisi",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function isUnit(value: string): value is MenuUnit {
  return UNITS.some((unit) => unit === value);
}

function orderedFields(changes: AuditEvent["changes"]): string[] {
  const known = new Set<string>(FIELDS);
  return [...FIELDS.filter((field) => field in changes), ...Object.keys(changes).filter((field) => !known.has(field))];
}

function IngredientHistoryDialog({
  ingredientId,
  categories,
  open,
  onOpenChange,
}: {
  ingredientId: number;
  categories: IngredientCategory[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("stock");
  const tCrm = useTranslations("crm");
  const tHistory = useTranslations("operationHistory");
  const units = useTranslations("stock.units");
  const locale = useLocale();
  const events = useAuditEvents(
    {
      page: 1,
      start: "",
      end: "",
      app: "menu",
      q: "",
      model: "ingredient",
      objectId: String(ingredientId),
    },
    open,
  );

  function fieldLabel(field: string): string {
    if (field in FIELD_KEYS) return t(FIELD_KEYS[field as keyof typeof FIELD_KEYS]);
    return field;
  }

  function formatValue(field: string, value: unknown): string {
    if (value === null || value === "") return "—";
    if (typeof value === "boolean") return value ? t("yes") : t("no");
    if (field === "unit" && typeof value === "string" && isUnit(value)) return units(value);
    if (field === "category_id" && (typeof value === "number" || typeof value === "string")) {
      const category = categories.find((row) => row.id === Number(value));
      return category === undefined ? String(value) : category.name;
    }
    if (typeof value === "string" || typeof value === "number") return String(value);
    return JSON.stringify(value);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(520px,calc(100vw-1.5rem))] max-w-[520px]">
        {open ? (
          <div className="max-h-[calc(100vh-3rem)] overflow-y-auto p-6">
            <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">{t("history")}</DialogTitle>
            {events.isPending ? (
              <div className="flex justify-center py-10">
                <Spinner className="h-5 w-5" />
              </div>
            ) : null}
            {events.isError ? <p className="mt-4 text-sm text-[var(--danger)]">{tHistory("loadError")}</p> : null}
            {events.data && events.data.results.length === 0 ? (
              <p className="mt-4 text-sm text-[var(--muted-2)]">{tHistory("empty")}</p>
            ) : null}
            {events.data && events.data.results.length > 0 ? (
              <ol className="mt-4 flex flex-col gap-4">
                {events.data.results.map((event) => (
                  <li key={event.id} className="border-t border-[var(--line)] pt-4 first:border-t-0 first:pt-0">
                    <p className="text-sm font-medium text-[var(--ink)]">
                      {formatWhen(event.created_at, locale)}
                      {" · "}
                      {event.actor_name ?? tHistory("system")}
                    </p>
                    <p className="mt-0.5 text-xs text-[var(--muted-2)]">{tCrm(ACTION_KEYS[event.action])}</p>
                    <div className="mt-2 flex flex-col gap-1.5">
                      {orderedFields(event.changes).map((field) => {
                        const change = event.changes[field];
                        if (!change) return null;
                        return (
                          <p key={field} className="text-sm text-[var(--ink)]">
                            <span className="text-[var(--muted-2)]">{fieldLabel(field)}: </span>
                            <span className="whitespace-pre-wrap break-words">
                              {formatValue(field, change.old)}
                              {" → "}
                              {formatValue(field, change.new)}
                            </span>
                          </p>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ol>
            ) : null}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export function IngredientHistoryMenu({
  ingredientId,
  categories,
}: {
  ingredientId: number;
  categories: IngredientCategory[];
}) {
  const t = useTranslations("stock");
  const [menuOpen, setMenuOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-[var(--ink)] shadow hover:bg-white"
        onClick={() => setMenuOpen((prev) => !prev)}
        aria-label={t("history")}
        aria-expanded={menuOpen}
      >
        <MoreHorizontal className="h-5 w-5" />
      </button>
      {menuOpen ? (
        <div className="absolute right-0 z-20 mt-2 min-w-[180px] rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => {
              setMenuOpen(false);
              setHistoryOpen(true);
            }}
          >
            <History className="h-4 w-4" />
            {t("history")}
          </button>
        </div>
      ) : null}
      <IngredientHistoryDialog
        ingredientId={ingredientId}
        categories={categories}
        open={historyOpen}
        onOpenChange={setHistoryOpen}
      />
    </div>
  );
}
