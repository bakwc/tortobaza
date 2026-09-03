import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";
import path from "node:path";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  turbopack: {
    root: path.resolve(__dirname),
  },
  skipTrailingSlashRedirect: true,
  async headers() {
    return [
      {
        source: "/:locale/crm/client/:token",
        headers: [
          {
            key: "Cache-Control",
            value: "private, no-store, no-cache, must-revalidate",
          },
          { key: "Pragma", value: "no-cache" },
          {
            key: "X-Robots-Tag",
            value: "noindex, nofollow, noarchive, nosnippet, noimageindex",
          },
          { key: "Referrer-Policy", value: "no-referrer" },
        ],
      },
      {
        source: "/:locale/crm/client/:token/",
        headers: [
          {
            key: "Cache-Control",
            value: "private, no-store, no-cache, must-revalidate",
          },
          { key: "Pragma", value: "no-cache" },
          {
            key: "X-Robots-Tag",
            value: "noindex, nofollow, noarchive, nosnippet, noimageindex",
          },
          { key: "Referrer-Policy", value: "no-referrer" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/:locale/constructor",
        destination: "/:locale/cake-constructor",
      },
      {
        source: "/:locale/constructor/",
        destination: "/:locale/cake-constructor",
      },
      {
        source: "/api/:path*/",
        destination: `${backendOrigin}/api/:path*/`,
      },
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${backendOrigin}/media/:path*`,
      },
    ];
  },
};

export default withNextIntl(nextConfig);

