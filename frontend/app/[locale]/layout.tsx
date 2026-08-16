import type { Metadata } from "next";
import { headers } from "next/headers";
import Script from "next/script";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { Cormorant_Garamond, Jost, Montserrat } from "next/font/google";
import { DevBanner } from "@/components/layout/DevBanner";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { JsonLd } from "@/components/seo/JsonLd";
import { routing } from "@/i18n/routing";
import { localBusinessJsonLd } from "@/lib/seo";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";
import { buildRootMetadata } from "@/lib/site-metadata";
import { getPublicSiteOrigin } from "@/lib/site-origin";
import { Providers } from "./providers";

const jost = Jost({
  variable: "--font-jost",
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["300", "400", "500", "600", "700"],
});

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["300", "400", "500", "600", "700"],
});

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin", "latin-ext", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  style: ["italic", "normal"],
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata(): Promise<Metadata> {
  return buildRootMetadata();
}

export default async function LocaleLayout({
  children,
  modal,
  params,
}: Readonly<{
  children: React.ReactNode;
  modal: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const [messages, headerStore, origin] = await Promise.all([
    getMessages(),
    headers(),
    getPublicSiteOrigin(),
  ]);
  const host = publicHostFromRequest((name) => headerStore.get(name));
  const showDevBanner = isDevSweetChillHost(host);

  return (
    <html
      lang={locale}
      className={`${jost.variable} ${montserrat.variable} ${cormorant.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--cream-soft)] text-[var(--ink)]">
        <Script
          defer
          src="https://analytics.q7.su/script.js"
          data-website-id="b5412135-037c-4f9e-a31d-d7eb820b28a3"
        />
        <JsonLd data={localBusinessJsonLd(origin)} />
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>
            {showDevBanner ? <DevBanner /> : null}
            <Header />
            <main className="flex-1">{children}</main>
            {modal}
            <Footer />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
