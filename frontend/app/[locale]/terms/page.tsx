import { getLocale, getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import { localizedPageMetadata } from "@/lib/seo";
import TermsContentEn from "@/content/terms/en";
import TermsContentKa from "@/content/terms/ka";
import TermsContentRu from "@/content/terms/ru";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "static" });
  return localizedPageMetadata(
    locale as Locale,
    "/terms",
    t("termsTitle"),
    t("termsDescription"),
  );
}

export default async function TermsPage() {
  const locale = await getLocale();
  const t = await getTranslations("static");
  const iso = new Date().toISOString().slice(0, 10);
  const updatedLine = t("lastUpdated", { date: iso });
  const Content =
    locale === "ka" ? TermsContentKa : locale === "ru" ? TermsContentRu : TermsContentEn;
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <Content updatedLine={updatedLine} />
      </article>
    </div>
  );
}
