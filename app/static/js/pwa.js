// pwa.js -- registers sw.js (see that file for why it's a no-op) so
// Android Chrome considers this app installable. Called once from every
// page's main(), same "small duplicated call per entrypoint" convention
// this app already uses for renderVersion(config).

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch((err) => {
    console.error("service worker registration failed", err);
  });
}
