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
  async rewrites() {
    return [
      {
        source: "/constructor",
        destination: "/cake-constructor",
      },
      {
        source: "/constructor/",
        destination: "/cake-constructor",
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

