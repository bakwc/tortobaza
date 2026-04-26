"use client";

import { cn } from "@/lib/utils";
import type { FulfillmentType } from "@/lib/api/types";

export function FulfillmentToggle({
  value,
  onChange,
}: {
  value: FulfillmentType;
  onChange: (value: FulfillmentType) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-1 rounded-full border border-[var(--line)] bg-white p-1">
      {(["delivery", "pickup"] as const).map((type) => (
        <button
          key={type}
          type="button"
          onClick={() => onChange(type)}
          className={cn(
            "h-11 rounded-full text-sm transition-colors",
            value === type
              ? "bg-[var(--brand)] text-[var(--brand-foreground)]"
              : "text-[var(--ink)]/70 hover:bg-[var(--cream)]",
          )}
        >
          {type === "delivery" ? "Delivery" : "Pick up"}
        </button>
      ))}
    </div>
  );
}
