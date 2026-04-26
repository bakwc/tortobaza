"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { formatAed } from "@/lib/format";
import type { PromoValidation } from "@/lib/api/types";

export function PromoCodeBox({
  value,
  onApplied,
}: {
  value: string;
  onApplied: (code: string, validation: PromoValidation | null) => void;
}) {
  const [code, setCode] = useState(value);
  const [validation, setValidation] = useState<PromoValidation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApply = async () => {
    if (!code.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.validatePromoCode(code.trim());
      setValidation(result);
      onApplied(code.trim(), result);
    } catch (e) {
      let message = "Invalid promo code";
      if (e instanceof ApiError) {
        const parsed = e.parsed<{ detail?: string }>();
        if (parsed?.detail) message = parsed.detail;
      }
      setError(message);
      setValidation(null);
      onApplied("", null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemove = () => {
    setCode("");
    setValidation(null);
    setError(null);
    onApplied("", null);
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Promo code"
          disabled={Boolean(validation)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (!validation) handleApply();
            }
          }}
        />
        {validation ? (
          <Button type="button" variant="outline" onClick={handleRemove}>
            <X className="mr-1 h-4 w-4" /> Remove
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            onClick={handleApply}
            disabled={isLoading || !code.trim()}
          >
            {isLoading ? <Spinner className="mr-2" /> : null}
            Apply
          </Button>
        )}
      </div>
      {error ? <p className="text-xs text-[var(--danger)]">{error}</p> : null}
      {validation ? (
        <p className="inline-flex items-center gap-1 text-xs text-[var(--brand)]">
          <Check className="h-3.5 w-3.5" />
          Promo applied — saving {formatAed(validation.discount_total)}
        </p>
      ) : null}
    </div>
  );
}
