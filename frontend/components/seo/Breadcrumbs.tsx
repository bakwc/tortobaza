import { Link } from "@/i18n/navigation";

export type BreadcrumbItem = {
  name: string;
  href?: string;
};

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-[var(--ink)]/60">
      <ol className="flex flex-wrap items-center gap-2">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={`${item.name}-${index}`} className="flex items-center gap-2">
              {index > 0 ? <span aria-hidden="true">/</span> : null}
              {item.href && !isLast ? (
                <Link href={item.href} className="hover:text-[var(--ink)]">
                  {item.name}
                </Link>
              ) : (
                <span className={isLast ? "text-[var(--ink)]" : undefined}>
                  {item.name}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
