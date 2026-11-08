import * as React from "react";
import { cn } from "@/lib/utils";

export function selectZeroOnFocus(event: React.FocusEvent<HTMLInputElement>) {
  const input = event.currentTarget;
  if (input.value !== "" && Number(input.value) === 0) {
    requestAnimationFrame(() => input.select());
  }
}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "text", inputMode, onFocus, onChange, pattern, ...props }, ref) => {
    const resolvedPattern =
      pattern ??
      (inputMode === "decimal" ? "-?\\d+(\\.\\d+)?" : inputMode === "numeric" ? "\\d+" : undefined);
    return (
      <input
        ref={ref}
        type={type}
        inputMode={inputMode}
        pattern={resolvedPattern}
        onChange={(event) => {
          if (
            (inputMode === "decimal" || inputMode === "numeric") &&
            event.currentTarget.value.includes(",")
          ) {
            const input = event.currentTarget;
            const next = input.value.replace(/,/g, ".");
            Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, next);
          }
          onChange?.(event);
        }}
        onFocus={(event) => {
          if (inputMode === "decimal" || inputMode === "numeric") {
            selectZeroOnFocus(event);
          }
          onFocus?.(event);
        }}
        className={cn(
          "flex h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] placeholder:text-[var(--muted-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";
