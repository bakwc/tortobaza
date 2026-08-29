import type { Metadata } from "next";
import { headers } from "next/headers";
import Script from "next/script";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { DevBanner } from "@/components/layout/DevBanner";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { SiteChrome } from "@/components/layout/SiteChrome";
import { JsonLd } from "@/components/seo/JsonLd";
import { routing } from "@/i18n/routing";
import { localBusinessJsonLd } from "@/lib/seo";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";
import { buildRootMetadata } from "@/lib/site-metadata";
import { getPublicSiteOrigin } from "@/lib/site-origin";
import { Providers } from "./providers";

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
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col bg-[var(--cream-soft)] text-[var(--ink)]">
        <script
          dangerouslySetInnerHTML={{
            __html: `window.umamiBeforeSend = function(type, payload) {
  var pathname = new URL(payload.url, window.location.origin).pathname;
  var isInternal = /^\\/(en|ka|ru)\\/(attendance|crm|login)(\\/|$)/i;
  if (isInternal.test(pathname)) {
    return false;
  }
  return payload;
};`,
          }}
        />
        <Script
          defer
          src="https://analytics.q7.su/script.js"
          data-website-id="b5412135-037c-4f9e-a31d-d7eb820b28a3"
          data-before-send="umamiBeforeSend"
        />
        <JsonLd data={localBusinessJsonLd(origin)} />
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers>
            {showDevBanner ? <DevBanner /> : null}
            <SiteChrome header={<Header />} footer={<Footer />}>
              {children}
              {modal}
            </SiteChrome>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
