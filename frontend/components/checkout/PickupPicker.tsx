"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

export function PickupPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number) => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["pickup-locations"],
    queryFn: () => api.getPickupLocations(),
  });

  const locations = data ?? [];

  useEffect(() => {
    if (value === null && locations.length > 0) {
      onChange(locations[0].id);
    }
  }, [value, locations, onChange]);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--ink)]/60">
        <Spinner /> Loading pickup locations…
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-[var(--danger)]">Could not load pickup locations.</p>
    );
  }

  if (locations.length === 0) {
    return (
      <p className="text-sm text-[var(--ink)]/60">No pickup locations are available.</p>
    );
  }

  return (
    <ul className="grid gap-3">
      {locations.map((loc) => (
        <li key={loc.id}>
          <button
            type="button"
            onClick={() => onChange(loc.id)}
            className={cn(
              "flex w-full items-start gap-3 rounded-2xl border p-4 text-left transition",
              value === loc.id
                ? "border-[var(--brand)] bg-[var(--cream)]"
                : "border-[var(--line)] bg-white hover:border-[var(--muted-2)]",
            )}
          >
            <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-[var(--brand)]" />
            <span className="flex flex-col gap-0.5">
              <span className="font-medium">{loc.name}</span>
              <span className="text-sm text-[var(--ink)]/60">{loc.address}</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
