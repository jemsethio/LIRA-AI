import type { NextConfig } from "next";
import withBundleAnalyzerFactory from "@next/bundle-analyzer";
import withSerwistInit from "@serwist/next";
import createNextIntlPlugin from "next-intl/plugin";

const withBundleAnalyzer = withBundleAnalyzerFactory({ enabled: process.env.ANALYZE === "true" });

const withNextIntl = createNextIntlPlugin(); // auto-discovers src/i18n/request.ts

const withSerwist = withSerwistInit({
  swSrc: "src/app/sw.ts",
  swDest: "public/sw.js",
  // Disable in dev — prevents cache thrash when code changes constantly
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  transpilePackages: ["@react-pdf/renderer"],
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    // Allow local /public images (default) + any remote domains
    unoptimized: true,   // simplest for self-hosted deployment
  },
};

export default withBundleAnalyzer(withSerwist(withNextIntl(nextConfig)));
