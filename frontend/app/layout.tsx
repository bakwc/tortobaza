import type { Metadata } from "next";
import { headers } from "next/headers";
import { Cormorant_Garamond, Jost, Montserrat } from "next/font/google";
import "./globals.css";
import { DevBanner } from "@/components/layout/DevBanner";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";
import { Providers } from "./providers";

const jost = Jost({
  variable: "--font-jost",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["italic", "normal"],
});

export const metadata: Metadata = {
  title: {
    default: "Sweet & Chill — Cakes",
    template: "Sweet & Chill | %s",
  },
  description: "Handcrafted cakes, desserts and custom orders.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headerStore = await headers();
  const host = publicHostFromRequest((name) => headerStore.get(name));
  const showDevBanner = isDevSweetChillHost(host);

  return (
    <html
      lang="en"
      className={`${jost.variable} ${montserrat.variable} ${cormorant.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[var(--cream-soft)] text-[var(--ink)]">
        <Providers>
          {showDevBanner ? <DevBanner /> : null}
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
