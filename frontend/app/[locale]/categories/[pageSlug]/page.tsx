import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { CategoryPills } from "@/components/catalog/CategoryPills";
import { ProductCard } from "@/components/catalog/ProductCard";
import { CartSidebar } from "@/components/catalog/CartSidebar";
import { MobileCartBar } from "@/components/catalog/MobileCartBar";
import { Breadcrumbs } from "@/components/seo/Breadcrumbs";
import { JsonLd } from "@/components/seo/JsonLd";
import { LocaleAlternatesProvider } from "@/lib/locale-alternates";
import { ApiError } from "@/lib/api/client";
import { getAllProducts } from "@/lib/api/catalog";
import { publicApi } from "@/lib/api/public-api";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import {
  breadcrumbJsonLd,
  itemListJsonLd,
  languageAlternates,
  localePath,
} from "@/lib/seo";
import { getPublicSiteOrigin } from "@/lib/site-origin";

export const revalidate = 3600;

async function loadCategory(pageSlug: string) {
  try {
    return await publicApi.getCategory(pageSlug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; pageSlug: string }>;
}): Promise<Metadata> {
  const { locale, pageSlug } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "metadata" });
  const category = await loadCategory(pageSlug);
  if (!category) {
    return { title: t("orderTitle") };
  }

  const origin = await getPublicSiteOrigin();
  const title = category.seo_title || category.page_heading || category.name;
  const description =
    category.seo_description ||
    category.page_description ||
    t("categoryFallbackDescription", { name: category.name });
  const path = `/categories/${category.page_slug}`;
  const pathsByLocale: Partial<Record<Locale, string>> = {};
  for (const loc of routing.locales) {
    const slug = category.page_slugs[loc];
    if (slug) {
      pathsByLocale[loc] = `/categories/${slug}`;
    }
  }

  return {
    title,
    description,
    alternates: {
      canonical: localePath(locale as Locale, path),
      ...languageAlternates(origin, pathsByLocale),
    },
    openGraph: {
      title,
      description,
      url: localePath(locale as Locale, path),
      images: category.image
        ? [{ url: category.image.src, alt: title }]
        : undefined,
    },
  };
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ locale: string; pageSlug: string }>;
}) {
  const { locale, pageSlug } = await params;
  setRequestLocale(locale);

  const category = await loadCategory(pageSlug);
  if (!category) {
    notFound();
  }

  const [categories, products, origin, tBreadcrumbs, tCatalog] = await Promise.all([
    publicApi.getCategories(),
    getAllProducts({ category: category.slug }),
    getPublicSiteOrigin(),
    getTranslations("breadcrumbs"),
    getTranslations("catalog"),
  ]);

  const heading = category.page_heading || category.name;
  const description = category.page_description;
  const tier = category.delivery_schedule_tier;
  const localeTyped = locale as Locale;
  const categoryPath = localePath(localeTyped, `/categories/${category.page_slug}`);
  const orderPath = localePath(localeTyped, "/order");
  const homePath = localePath(localeTyped, "/");

  const alternates: Partial<Record<Locale, string>> = {};
  for (const loc of routing.locales) {
    const slug = category.page_slugs[loc];
    if (slug) {
      alternates[loc] = `/categories/${slug}`;
    }
  }

  const pillCategories = categories.filter((item) => item.page_slug);

  return (
    <LocaleAlternatesProvider alternates={alternates}>
      <div className="mx-auto max-w-[1400px] px-6">
        <JsonLd
          data={[
            breadcrumbJsonLd(origin, [
              { name: tBreadcrumbs("home"), path: homePath },
              { name: tBreadcrumbs("catalog"), path: orderPath },
              { name: heading, path: categoryPath },
            ]),
            itemListJsonLd(
              origin,
              heading,
              products.map((product) => ({
                name: product.name,
                path: localePath(localeTyped, `/order/${product.slug}`),
              })),
            ),
          ]}
        />

        <div className="pt-8">
          <Breadcrumbs
            items={[
              { name: tBreadcrumbs("home"), href: "/" },
              { name: tBreadcrumbs("catalog"), href: "/order" },
              { name: heading },
            ]}
          />
        </div>

        <CategoryPills categories={pillCategories} />

        <div className="grid gap-8 pb-32 lg:grid-cols-[1fr_360px] lg:gap-10 lg:pb-20">
          <section className="py-6">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-[32px] font-bold leading-[1.05] text-[#666]">
                {heading}
              </h1>
              <span className="inline-flex shrink-0 items-center rounded-full bg-product-price-btn px-4 py-1.5 text-[16px] font-bold text-white">
                {tCatalog(`deliveryTier.${tier}`)}
              </span>
            </div>
            {tier === "same_day" ? (
              <p className="mt-2 text-sm text-[var(--muted-2)]">
                {tCatalog("deliveryTierSameDayCutoff")}
              </p>
            ) : null}
            {description ? (
              <p className="mt-4 max-w-3xl text-base leading-relaxed text-[var(--ink)]/75">
                {description}
              </p>
            ) : null}
            <div className="mt-8 grid grid-cols-2 gap-6 xl:grid-cols-3">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </section>
          <div className="hidden lg:block">
            <CartSidebar />
          </div>
        </div>

        <div className="fixed inset-x-0 bottom-0 z-30 px-4 pb-4 lg:hidden">
          <MobileCartBar />
        </div>
      </div>
    </LocaleAlternatesProvider>
  );
}
