import { getLocale, getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import { localizedPageMetadata } from "@/lib/seo";
import AboutContentEn from "@/content/about/en";
import AboutContentKa from "@/content/about/ka";
import AboutContentRu from "@/content/about/ru";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "static" });
  return localizedPageMetadata(
    locale as Locale,
    "/about",
    t("aboutTitle"),
    t("aboutDescription"),
  );
}

export default async function AboutPage() {
  const locale = await getLocale();
  const Content =
    locale === "ka" ? AboutContentKa : locale === "ru" ? AboutContentRu : AboutContentEn;
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <Content />
      </article>
    </div>
  );
}
