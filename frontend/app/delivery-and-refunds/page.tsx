import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import DeliveryContentEn from "@/content/delivery/en";
import DeliveryContentKa from "@/content/delivery/ka";
import DeliveryContentRu from "@/content/delivery/ru";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("static");
  return {
    title: t("deliveryTitle"),
    description: t("deliveryDescription"),
  };
}

export default async function DeliveryAndRefundsPage() {
  const locale = await getLocale();
  const t = await getTranslations("static");
  const iso = new Date().toISOString().slice(0, 10);
  const updatedLine = t("lastUpdated", { date: iso });
  const Content =
    locale === "ka"
      ? DeliveryContentKa
      : locale === "ru"
        ? DeliveryContentRu
        : DeliveryContentEn;
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <Content updatedLine={updatedLine} />
      </article>
    </div>
  );
}
