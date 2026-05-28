import { defaultCache } from "@serwist/next/worker";
import { Serwist, NetworkFirst, CacheFirst, StaleWhileRevalidate, ExpirationPlugin } from "serwist";

declare global {
  interface ServiceWorkerGlobalScope {
    __SW_MANIFEST: (string | { url: string; revision: string | null })[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

// Cross-origin backend origin — must match NEXT_PUBLIC_API_URL at build time
// SW scope is same-origin (localhost:3000); backend is localhost:8000.
// Cross-origin requests are NOT intercepted by default. We match by full URL.
// API_ORIGIN is documented for future env substitution via next.config.ts env injection.

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // 1. Next.js static chunks — CacheFirst (content-hash busting handles staleness)
    {
      matcher: /^\/_next\/static\/.*/i,
      handler: new CacheFirst({
        cacheName: "next-static",
        plugins: [new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 })],
      }),
    },
    // 2. Basin GeoJSON — StaleWhileRevalidate (changes rarely; serve cached, update async)
    {
      matcher: ({ url }: { url: URL }) =>
        url.pathname === "/spatial/basin/geojson",
      handler: new StaleWhileRevalidate({
        cacheName: "lira-geojson",
        plugins: [new ExpirationPlugin({ maxEntries: 5, maxAgeSeconds: 60 * 60 * 24 })],
      }),
    },
    // 3. Diagnosis + agent + omo-ghibe endpoints — NetworkFirst with 6s timeout
    //    Matches both same-origin (/diagnosis/...) and cross-origin backend
    {
      matcher: ({ url }: { url: URL }) =>
        url.pathname.startsWith("/diagnosis/") ||
        url.pathname.startsWith("/agents/") ||
        url.pathname.startsWith("/omo-ghibe/") ||
        url.pathname.startsWith("/spatial/zone/"),
      handler: new NetworkFirst({
        cacheName: "lira-api",
        networkTimeoutSeconds: 6,
        plugins: [new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 7 })],
      }),
    },
    // 3b. Cross-origin backend — matches full URL when NEXT_PUBLIC_API_URL is an external host
    {
      matcher: ({ url }: { url: URL }) => {
        const isBackend = url.hostname !== self.location.hostname;
        if (!isBackend) return false;
        return (
          url.pathname.startsWith("/diagnosis/") ||
          url.pathname.startsWith("/agents/") ||
          url.pathname.startsWith("/omo-ghibe/") ||
          url.pathname.startsWith("/spatial/")
        );
      },
      handler: new NetworkFirst({
        cacheName: "lira-api-cross",
        networkTimeoutSeconds: 6,
        plugins: [new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 7 })],
      }),
    },
    // 4. Health check — NetworkFirst with short timeout (used by useOnlineStatus heartbeat)
    {
      matcher: ({ url }: { url: URL }) => url.pathname === "/health/ready",
      handler: new NetworkFirst({
        cacheName: "lira-health",
        networkTimeoutSeconds: 4,
        plugins: [new ExpirationPlugin({ maxEntries: 1, maxAgeSeconds: 60 })],
      }),
    },
    // 5. Serwist defaults for everything else (images, fonts, etc.)
    ...defaultCache,
  ],
});

serwist.addEventListeners();
