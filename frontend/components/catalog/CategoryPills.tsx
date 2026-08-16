"use client";

import { useEffect, useState } from "react";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/api/types";

export function CategoryPills({ categories }: { categories: Category[] }) {
  const pathname = usePathname();
  const isCatalogPage = pathname === "/";
  const [activeSlug, setActiveSlug] = useState<string | null>(
    categories[0]?.slug ?? null,
  );

  useEffect(() => {
    if (!isCatalogPage) return;

    const sections = categories
      .map((category) => document.getElementById(`category-${category.slug}`))
      .filter((section): section is HTMLElement => section !== null);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];

        if (visible) {
          setActiveSlug(visible.target.id.replace("category-", ""));
        }
      },
      {
        rootMargin: "-140px 0px -60% 0px",
        threshold: [0, 0.1, 0.5, 1],
      },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [categories, isCatalogPage]);

  return (
    <div className="sticky top-16 z-30 -mx-6 bg-[var(--cream-soft)]/95 px-6 pt-10 pb-4 backdrop-blur supports-[backdrop-filter]:bg-[var(--cream-soft)]/80">
      <div className="scrollbar-none mx-auto flex max-w-[1400px] gap-2 overflow-x-auto">
        {categories.map((c) => {
          const href = c.page_slug ? `/categories/${c.page_slug}` : "/";
          const isActive = isCatalogPage
            ? activeSlug === c.slug
            : pathname === `/categories/${c.page_slug}`;
          return (
            <Link
              key={c.slug}
              href={href}
              onClick={(event) => {
                if (
                  !isCatalogPage ||
                  event.metaKey ||
                  event.ctrlKey ||
                  event.shiftKey ||
                  event.altKey
                ) {
                  return;
                }

                const section = document.getElementById(`category-${c.slug}`);
                if (!section) return;

                event.preventDefault();
                setActiveSlug(c.slug);
                section.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
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
