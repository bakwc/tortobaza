import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { CrmClientOrderView } from "@/components/crm/CrmClientOrderView";
import { ApiError } from "@/lib/api/client";
import { serverApi } from "@/lib/api/server-api";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("crm");
  return {
    title: t("clientPageTitle"),
    robots: {
      index: false,
      follow: false,
      nocache: true,
      noarchive: true,
      nosnippet: true,
      noimageindex: true,
      googleBot: {
        index: false,
        follow: false,
        noimageindex: true,
        nosnippet: true,
        noarchive: true,
      },
    },
    referrer: "no-referrer",
  };
}

export default async function CrmClientOrderPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  if (!/^[0-9a-f]{64}$/.test(token)) {
    notFound();
  }
  try {
    const order = await serverApi.getCrmClientOrder(token);
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-8 md:py-12">
        <CrmClientOrderView order={order} token={token} />
      </div>
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    throw e;
  }
}
