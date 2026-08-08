import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import ConstructorClient from "./ConstructorClient";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("static");
  return {
    title: t("constructorTitle"),
    description: t("constructorDescription"),
  };
}

export default function ConstructorPage() {
  return (
    <div className="bg-[var(--cream)]">
      <ConstructorClient />
    </div>
  );
}
