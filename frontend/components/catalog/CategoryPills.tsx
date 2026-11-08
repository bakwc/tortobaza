"use client";

import { useEffect, useRef, useState } from "react";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/api/types";

const FADE_WIDTH = 48;

export function CategoryPills({
  categories,
  activePageSlug,
}: {
  categories: Category[];
  activePageSlug?: string;
}) {
  const pathname = usePathname();
  const isCatalogPage = pathname === "/";
  const [activeSlug, setActiveSlug] = useState<string | null>(
    categories[0]?.slug ?? null,
  );
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pillRefs = useRef(new Map<string, HTMLAnchorElement>());
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const isPillActive = (c: Category) =>
    isCatalogPage
      ? activeSlug === c.slug
      : activePageSlug
        ? activePageSlug === c.page_slug
        : pathname === `/categories/${c.page_slug}`;
  const activePillSlug = categories.find(isPillActive)?.slug ?? null;

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

  useEffect(() => {
    const scroller = scrollerRef.current!;

    const updateEdges = () => {
      setCanScrollLeft(scroller.scrollLeft > 1);
      setCanScrollRight(
        scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 1,
      );
    };

    updateEdges();
    scroller.addEventListener("scroll", updateEdges, { passive: true });
    const resizeObserver = new ResizeObserver(updateEdges);
    resizeObserver.observe(scroller);
    return () => {
      scroller.removeEventListener("scroll", updateEdges);
      resizeObserver.disconnect();
    };
  }, [categories]);

  useEffect(() => {
    if (!activePillSlug) return;

    const scroller = scrollerRef.current!;
    const pill = pillRefs.current.get(activePillSlug)!;
    const scrollerRect = scroller.getBoundingClientRect();
    const pillRect = pill.getBoundingClientRect();
    const offset =
      pillRect.left - scrollerRect.left - (scrollerRect.width - pillRect.width) / 2;

    scroller.scrollBy({ left: offset, behavior: "smooth" });
  }, [activePillSlug]);

  const maskImage = `linear-gradient(to right, ${
    canScrollLeft ? `transparent 0, #000 ${FADE_WIDTH}px` : "#000 0"
  }, ${
    canScrollRight
      ? `#000 calc(100% - ${FADE_WIDTH}px), transparent 100%`
      : "#000 100%"
  })`;

  return (
    <div className="sticky top-16 z-30 -mx-6 bg-[var(--cream-soft)]/95 pt-10 pb-4 backdrop-blur supports-[backdrop-filter]:bg-[var(--cream-soft)]/80">
      <div
        ref={scrollerRef}
        style={{ maskImage, WebkitMaskImage: maskImage }}
        className="scrollbar-none mx-auto flex max-w-[1400px] scroll-px-6 gap-2 overflow-x-auto px-6"
      >
        {categories.map((c) => {
          const href = c.page_slug ? `/categories/${c.page_slug}` : "/";
          const isActive = isPillActive(c);
          return (
            <Link
              key={c.slug}
              ref={(node) => {
                pillRefs.current.set(c.slug, node!);
                return () => {
                  pillRefs.current.delete(c.slug);
                };
              }}
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
