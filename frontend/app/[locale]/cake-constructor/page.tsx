import { getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import { localizedPageMetadata } from "@/lib/seo";
import ConstructorClient from "./ConstructorClient";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "static" });
  return localizedPageMetadata(
    locale as Locale,
    "/cake-constructor",
    t("constructorTitle"),
    t("constructorDescription"),
  );
}

export default function ConstructorPage() {
  return (
    <div className="bg-[var(--cream)]">
      <ConstructorClient />
    </div>
  );
}
