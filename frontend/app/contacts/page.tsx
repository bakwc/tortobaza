import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import ContactsContentEn from "@/content/contacts/en";
import ContactsContentKa from "@/content/contacts/ka";
import ContactsContentRu from "@/content/contacts/ru";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("static");
  return {
    title: t("contactsTitle"),
    description: t("contactsDescription"),
  };
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
