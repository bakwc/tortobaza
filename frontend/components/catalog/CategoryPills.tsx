"use client";

import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/api/types";

export function CategoryPills({ categories }: { categories: Category[] }) {
  const pathname = usePathname();

  return (
    <div className="sticky top-16 z-30 -mx-6 bg-[var(--cream-soft)]/95 px-6 pt-10 pb-4 backdrop-blur supports-[backdrop-filter]:bg-[var(--cream-soft)]/80">
      <div className="scrollbar-none mx-auto flex max-w-[1400px] gap-2 overflow-x-auto">
        {categories.map((c) => {
          const href = c.page_slug ? `/categories/${c.page_slug}` : "/order";
          const isActive = pathname === `/categories/${c.page_slug}`;
          return (
            <Link
              key={c.slug}
              href={href}
              style={{ fontSize: 16, fontWeight: 500 }}
              className={cn(
                "shrink-0 rounded-full px-4 py-2 transition-colors duration-200",
                isActive
                  ? "bg-pill-active text-white"
                  : "bg-white text-[#666] hover:bg-pill-hover hover:text-[var(--ink)]",
              )}
            >
              {c.name}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
