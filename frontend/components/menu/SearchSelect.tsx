"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export type SearchSelectOption = { value: string; label: string };

function listPlacement(anchor: HTMLElement): { upward: boolean; maxHeight: number } {
  const margin = 8;
  const preferred = 240;
  let clipTop = 0;
  let clipBottom = window.innerHeight;
  let node: HTMLElement | null = anchor.parentElement;
  while (node) {
    const overflowY = getComputedStyle(node).overflowY;
    if (overflowY === "auto" || overflowY === "scroll" || overflowY === "hidden") {
      const rect = node.getBoundingClientRect();
      clipTop = rect.top;
      clipBottom = rect.bottom;
      break;
    }
    node = node.parentElement;
  }
  const rect = anchor.getBoundingClientRect();
  const spaceBelow = clipBottom - rect.bottom - margin;
  const spaceAbove = rect.top - clipTop - margin;
  const upward = spaceBelow < 160 && spaceAbove > spaceBelow;
  const available = upward ? spaceAbove : spaceBelow;
  return { upward, maxHeight: Math.max(80, Math.min(preferred, available)) };
}

export function SearchSelect({
  options,
  value,
  onChange,
  placeholder,
  required,
  className,
}: {
  options: SearchSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  required: boolean;
  className: string;
}) {
  const t = useTranslations("stock");
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingSelect = useRef(false);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [edited, setEdited] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [placement, setPlacement] = useState({ upward: false, maxHeight: 240 });
  const selectedLabel = options.find((option) => option.value === value)?.label ?? "";
  const needle = open && edited ? query.trim().toLowerCase() : "";
  const filtered =
    needle === "" ? options : options.filter((option) => option.label.toLowerCase().includes(needle));
  const highlightIndex = filtered.length === 0 ? 0 : Math.min(highlight, filtered.length - 1);
  const active = filtered[highlightIndex] ?? null;

  const close = () => {
    pendingSelect.current = document.activeElement === inputRef.current;
    setOpen(false);
    setEdited(false);
    setQuery("");
  };

  const choose = (next: string) => {
    onChange(next);
    close();
  };

  const openList = () => {
    const index = options.findIndex((option) => option.value === value);
    pendingSelect.current = true;
    setQuery(selectedLabel);
    setEdited(false);
    setHighlight(index >= 0 ? index : 0);
    setOpen(true);
  };

  useLayoutEffect(() => {
    if (!pendingSelect.current) return;
    pendingSelect.current = false;
    inputRef.current?.select();
  }, [open, query]);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!open || !root) return;
    const update = () => {
      const next = listPlacement(root);
      setPlacement((current) =>
        current.upward === next.upward && current.maxHeight === next.maxHeight ? current : next,
      );
    };
    update();
    const scrollers: HTMLElement[] = [];
    let node: HTMLElement | null = root.parentElement;
    while (node) {
      const overflowY = getComputedStyle(node).overflowY;
      if (overflowY === "auto" || overflowY === "scroll" || overflowY === "hidden") scrollers.push(node);
      node = node.parentElement;
    }
    for (const scroller of scrollers) scroller.addEventListener("scroll", update);
    window.addEventListener("resize", update);
    return () => {
      for (const scroller of scrollers) scroller.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const list = listRef.current;
    const item = list?.querySelector(`[data-index="${highlightIndex}"]`);
    if (!list || !(item instanceof HTMLElement)) return;
    const itemTop = item.offsetTop;
    const itemBottom = itemTop + item.offsetHeight;
    if (itemTop < list.scrollTop) list.scrollTop = itemTop;
    else if (itemBottom > list.scrollTop + list.clientHeight) list.scrollTop = itemBottom - list.clientHeight;
  }, [highlightIndex, open, needle]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const root = rootRef.current;
      if (!root || !(event.target instanceof Node) || root.contains(event.target)) return;
      close();
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  return (
    <div
      ref={rootRef}
      className={cn("relative", className)}
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (next instanceof Node && rootRef.current?.contains(next)) return;
        close();
      }}
    >
      {required ? (
        <input
          tabIndex={-1}
          aria-hidden="true"
          required
          value={value}
          onChange={() => undefined}
          className="pointer-events-none absolute bottom-0 left-5 h-px w-px opacity-0"
        />
      ) : null}
      <input
        ref={inputRef}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && active ? `${listId}-${highlightIndex}` : undefined}
        autoComplete="off"
        placeholder={placeholder}
        value={open ? query : selectedLabel}
        onChange={(event) => {
          setQuery(event.target.value);
          setEdited(true);
          setHighlight(0);
          setOpen(true);
        }}
        onMouseDown={(event) => {
          if (open) return;
          event.preventDefault();
          event.currentTarget.focus();
          openList();
        }}
        onMouseUp={() => {
          if (!edited) inputRef.current?.select();
        }}
        onFocus={() => {
          if (!open) openList();
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            if (!open) {
              openList();
              return;
            }
            setHighlight(Math.min(highlightIndex + 1, Math.max(filtered.length - 1, 0)));
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            if (!open) {
              openList();
              return;
            }
            setHighlight((current) => Math.max(current - 1, 0));
            return;
          }
          if (event.key === "Enter" && open) {
            event.preventDefault();
            if (active) choose(active.value);
            return;
          }
          if (event.key === "Escape" && open) {
            event.preventDefault();
            event.stopPropagation();
            close();
          }
        }}
        className="h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] placeholder:text-[var(--muted-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30"
      />
      {open ? (
        <div
          ref={listRef}
          id={listId}
          role="listbox"
          style={{ maxHeight: placement.maxHeight }}
          className={cn(
            "absolute z-30 w-full overflow-y-auto rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg",
            placement.upward ? "bottom-full mb-1" : "top-full mt-1",
          )}
        >
          {filtered.length === 0 ? (
            <p className="px-4 py-2 text-sm text-[var(--muted-2)]">{t("noMatches")}</p>
          ) : (
            filtered.map((option, index) => (
              <button
                key={option.value}
                id={`${listId}-${index}`}
                type="button"
                role="option"
                aria-selected={option.value === value}
                data-index={index}
                tabIndex={-1}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setHighlight(index)}
                onClick={() => choose(option.value)}
                className={cn(
                  "block w-full px-4 py-2 text-left text-sm text-[var(--ink)]",
                  index === highlightIndex ? "bg-[var(--cream)]" : "hover:bg-[var(--cream)]",
                )}
              >
                {option.label}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
