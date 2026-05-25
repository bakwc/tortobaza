import { HeaderBar } from "@/components/layout/HeaderBar";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-[var(--brand)] text-[var(--brand-foreground)] shadow-sm">
      <HeaderBar />
    </header>
  );
}
