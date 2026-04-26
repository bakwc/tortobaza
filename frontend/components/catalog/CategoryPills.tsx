"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/api/types";

export function CategoryPills({ categories }: { categories: Category[] }) {
  const [active, setActive] = useState<string | null>(categories[0]?.slug ?? null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lockUntilRef = useRef<number>(0);
  const scrollEndTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const sections = categories
      .map((c) => document.getElementById(`category-${c.slug}`))
      .filter((el): el is HTMLElement => Boolean(el));
    if (sections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (Date.now() < lockUntilRef.current) return;
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) {
          const slug = visible.target.id.replace("category-", "");
          setActive(slug);
        }
      },
      { rootMargin: "-200px 0px -60% 0px", threshold: [0, 0.1, 0.5, 1] },
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, [categories]);

  const handleClick = (slug: string) => {
    const el = document.getElementById(`category-${slug}`);
    if (!el) return;
    setActive(slug);
    lockUntilRef.current = Date.now() + 1200;
    const top = el.getBoundingClientRect().top + window.scrollY - 140;
    window.scrollTo({ top, behavior: "smooth" });

    if (scrollEndTimerRef.current) clearTimeout(scrollEndTimerRef.current);
    let lastY = window.scrollY;
    let stableCount = 0;
    const tick = () => {
      const y = window.scrollY;
      if (Math.abs(y - lastY) < 1) {
        stableCount += 1;
      } else {
        stableCount = 0;
      }
      lastY = y;
      if (stableCount >= 3) {
        lockUntilRef.current = 0;
        return;
      }
      scrollEndTimerRef.current = setTimeout(tick, 80);
    };
    scrollEndTimerRef.current = setTimeout(tick, 80);
  };

  return (
    <div className="sticky top-16 z-30 -mx-6 bg-[var(--cream-soft)]/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-[var(--cream-soft)]/80">
      <div
        ref={containerRef}
        className="scrollbar-none mx-auto flex max-w-[1400px] gap-3 overflow-x-auto"
      >
        {categories.map((c) => (
          <button
            key={c.slug}
            type="button"
            onClick={() => handleClick(c.slug)}
            className={cn(
              "shrink-0 rounded-full px-5 py-2 text-sm font-semibold transition-colors",
              active === c.slug
                ? "bg-[#4a4a4a] text-white hover:bg-[#4a4a4a]"
                : "bg-white text-[var(--ink)] hover:bg-[#a8a8a8] hover:text-white",
            )}
          >
            {c.name}
          </button>
        ))}
      </div>
    </div>
  );
}
