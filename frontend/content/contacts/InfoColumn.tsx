import type { ReactNode } from "react";

export function InfoColumn({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-4 text-[var(--ink)]">
      <div className="text-[var(--ink)]/80">{icon}</div>
      <h2 className="text-lg font-bold tracking-[0.06em] uppercase md:text-xl">{title}</h2>
      <div className="space-y-1 text-sm md:text-base">{children}</div>
    </div>
  );
}
