// sw.js -- minimal service worker, registered by app/static/js/pwa.js on
// every page, purely so Android Chrome considers this app installable
// ("Add to Home Screen" -> standalone, no browser chrome). Deliberately
// does NOT cache anything or intercept fetches: this app's data is
// inherently live (WebSocket broadcasts, frequent polling), so serving a
// cached response would just show stale/broken data instead of "offline
// support" -- a no-op fetch listener (falling through to the network) is
// the correct behavior here, not a placeholder to fill in later.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // Intentionally empty -- no respondWith() means the browser handles
  // the request exactly as it would with no service worker at all.
});
