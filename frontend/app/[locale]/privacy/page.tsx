import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import PrivacyContentEn from "@/content/privacy/en";
import PrivacyContentKa from "@/content/privacy/ka";
import PrivacyContentRu from "@/content/privacy/ru";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("static");
  return {
    title: t("privacyTitle"),
    description: t("privacyDescription"),
  };
}

export default async function PrivacyPage() {
  const locale = await getLocale();
  const t = await getTranslations("static");
  const iso = new Date().toISOString().slice(0, 10);
  const updatedLine = t("lastUpdated", { date: iso });
  const Content =
    locale === "ka"
      ? PrivacyContentKa
      : locale === "ru"
        ? PrivacyContentRu
        : PrivacyContentEn;
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <Content updatedLine={updatedLine} />
      </article>
    </div>
  );
}
