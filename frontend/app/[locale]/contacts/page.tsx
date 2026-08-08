import { getLocale, getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import { localizedPageMetadata } from "@/lib/seo";
import ContactsContentEn from "@/content/contacts/en";
import ContactsContentKa from "@/content/contacts/ka";
import ContactsContentRu from "@/content/contacts/ru";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "static" });
  return localizedPageMetadata(
    locale as Locale,
    "/contacts",
    t("contactsTitle"),
    t("contactsDescription"),
  );
}

export default async function ContactsPage() {
  const locale = await getLocale();
  const Content =
    locale === "ka" ? ContactsContentKa : locale === "ru" ? ContactsContentRu : ContactsContentEn;
  return (
    <div className="bg-[var(--cream)]">
      <Content />
    </div>
  );
}
