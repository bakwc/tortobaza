import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[88px] w-full rounded-2xl border border-[var(--line)] bg-white px-5 py-3 text-sm text-[var(--ink)] placeholder:text-[var(--muted-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
});
Textarea.displayName = "Textarea";
