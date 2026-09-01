# Cloudflare Phase 2A Validation Report

## 1. Current status

- Date: 2026-09-01 UTC
- Public hostname: `rtl.broccolynet.com`
- Anonymous read-only hostname: `public.broccolynet.com`
- Exposure mode: `rtl` is Access-authenticated; `public` is anonymous
  minimal read-only status
- Origin: `http://127.0.0.1:18088`
- Existing Tailscale origin: `<TAILSCALE_IP>:8088` (unchanged)
- Result: Phase 2A authenticated publication and Phase 2B minimal anonymous
  read-only publication succeeded.

## 2. Cloudflare controls

- Remotely-managed Named Tunnel connected over four ready connections.
- Published application route maps only `rtl.broccolynet.com` to the loopback
  origin.
- Cloudflare Access application protects the entire hostname with an explicit
  owner allow policy.
- Tunnel-side Access JWT validation is required. Requests without a valid JWT
  are rejected before the origin.
- HTTP redirects to HTTPS with `301`.
- TLS 1.1 is rejected; TLS 1.2 and TLS 1.3 succeed.
- Unauthenticated UI, API, write API, unknown paths, and WebSocket handshakes
  redirect to Access and do not reach the application.
- Cloudflare Free Managed Ruleset is provided by default on the Free plan.
- The single Free-plan rate limiting rule is reserved for Phase 2B. A broad
  path-only rule is not enabled while this hostname is Access-only, because
  Free-plan expressions cannot scope the rule by both host and method.
- HSTS is not enabled yet. It is a zone-level commitment that could affect
  future `broccolynet.com` projects and should be evaluated after those
  hostnames are known.

## 3. Origin and host controls

- Docker publishes the Cloudflare origin only on `127.0.0.1:18088`.
- The existing Tailscale mapping remains available and healthy.
- UFW remains deny-incoming with Tailscale and the documented internal readsb
  exception only. No router port forwarding was added.
- Database host ports remain unpublished.
- The original database password was rotated to a random 64-character
  hexadecimal value. The old network credential is rejected.
- Pre-rotation logical backup:
  `backups/adsb-db-20260901T134918Z.dump`.
- HTTP security headers are present on successful and handled error responses:
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
  `Permissions-Policy`.

## 4. cloudflared service

- Service is enabled and active under systemd.
- `DynamicUser=yes`; the process does not run as root.
- The tunnel token remains `/etc/cloudflared/token`, `0600 root:root`.
- `LoadCredential` provides a temporary read-only token copy to the dynamic
  service user; the token is absent from the command line and journal.
- systemd sandbox exposure improved from `8.7 EXPOSED` to `2.8 OK`.
- Manual restart succeeded with the route and JWT validation configuration
  restored automatically.
- Automatic failure restart passed: an intentional `SIGKILL` changed the PID,
  incremented `NRestarts` to 1, restored four ready Tunnel connections, and
  preserved Access and Tailscale operation.
- Full host reboot recovery passed. A new boot restored UFW, Tailscale, SSH
  socket activation, Docker and every long-running application container,
  readsb/lighttpd, the hardened cloudflared service, four Tunnel connections,
  Access enforcement, HTTP readiness, and both tested WebSocket paths.

## 5. Functional validation

- Access One-time PIN login: passed.
- Desktop UI and API: passed.
- Main realtime WebSocket features: passed.
- Independent mobile-network login and UI: passed.
- Independent mobile-network anonymous public status page: passed.
- Cloudflare Security Events review after public traffic: no suspicious
  access or unexpected blocks observed.
- Loopback and Tailscale HTTP health after deployment: passed.
- Loopback and Tailscale aircraft-position WebSocket after deployment: passed.
- API integration suite: 112 passed.
- Public-boundary unit/config suite: 41 passed.

## 6. Phase 2B staging boundary

- Anonymous hostname: `public.broccolynet.com`.
- Its dedicated Published Application route points to the same loopback-only
  origin. The existing `rtl.broccolynet.com` route retains mandatory Access
  JWT validation.
- Exact-Host matching uses the ASGI `Host` header only. Forwarded headers
  are not trusted for authorization decisions.
- Duplicate Host headers mentioning the public hostname fail closed, and
  encoded/non-ASCII path aliases are covered by negative tests.
- The public hostname is deny-by-default and currently permits only:
  - `GET /` (a separate minimal status page)
  - `GET /api/status`
  - the exact CSS, JavaScript, and favicon assets required by that page
- All write methods are rejected before routing.
- OpenAPI/docs, health readiness, favorites, aircraft history/positions,
  receiver/location data, private static pages, and unknown paths return
  `404`.
- Every WebSocket path is rejected before acceptance. Public WebSockets stay
  disabled until connection limits, message limits, privacy, and load are
  reviewed.
- The Tailscale hostname and Access-protected `rtl.broccolynet.com` bypass
  this public-only policy and remain functionally unchanged.
- Deployed origin checks passed: public root/status `200`, OpenAPI `404`,
  write attempt `405`, WebSocket handshake `403`, Tailscale health
  `200`, Tunnel ready with four connections, and unauthenticated Access
  request `302`.
- External Cloudflare checks passed:
  - DNS resolves only to Cloudflare edge addresses.
  - HTTP redirects to HTTPS with `301`.
  - Public root and status API return `200`.
  - OpenAPI, docs, readiness, favorites, receiver API, unknown paths return
    `404`.
  - A public write attempt returns `405`; public WebSocket handshake returns
    `403`.
  - TLS 1.1 is rejected; TLS 1.2 and TLS 1.3 return `200`.
  - Successful and denied responses contain the expected security headers and
    `Cache-Control: no-store`.
  - `rtl.broccolynet.com` remains Access-protected (`302` unauthenticated);
    Tailscale health and four Tunnel connections remain healthy.

## 7. Deferred known issue

The authenticated raw-data page does not currently receive data through the
Named Tunnel. Other tested WebSocket features work. Per owner direction, root
cause analysis is deferred until the web-publication work is complete. Do not
remove Access, weaken JWT validation, expose readsb ports, or add firewall
rules as a workaround.

Android Chrome does not offer a new PWA installation from the
Access-protected `rtl.broccolynet.com` origin. The same deployed application
is installable from its Tailscale origin, and an already-installed copy
continues to launch. The manifest, icons, HTTPS, and service worker were
validated. Two mitigations were tested without success: credentialed manifest
fetches and a narrowly scoped anonymous `/pwa/*` asset path. The ineffective
origin changes were rolled back. The temporary Cloudflare `/pwa/*` Published
Application route and matching Access Bypass application must also be removed
during closing; after the origin rollback they expose only `404` responses.
Further Android/Access PWA investigation is deferred.

## 8. Ongoing operating constraints

1. Keep `rtl.broccolynet.com` Access-protected.
2. Continue periodic Security Events review.
3. Keep the temporary `noindex` directive until search-engine indexing is
   explicitly desired.
4. Repeat privacy, load, and negative testing before expanding the public API
   allowlist or enabling any public WebSocket.
