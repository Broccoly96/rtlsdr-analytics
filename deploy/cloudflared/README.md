# Cloudflare Named Tunnel deployment

Production hostname: `rtl.broccolynet.com`

The origin is deliberately bound only to `127.0.0.1:18088`. The existing
The existing Tailscale IP mapping remains independent at
`<TAILSCALE_IP>:8088`.

## Required Cloudflare dashboard order

1. Configure One-time PIN (or another identity provider) in Cloudflare Zero
   Trust.
2. Create a Self-hosted Access application for `rtl.broccolynet.com`.
3. Add an `Allow` policy whose `Include` selector is the owner's exact email
   address. Do not use `Everyone`, a broad email domain, `Bypass`, or
   `Login Methods: One-time PIN` by itself.
4. Create a remotely-managed tunnel named `rtl-production` and copy its token.
5. Install and start the connector using the token-file procedure below.
6. Only after the connector is healthy, add a Published application route:
   hostname `rtl.broccolynet.com`, service URL `http://127.0.0.1:18088`.

Do not paste the tunnel token into chat, a shell command argument, the
repository, or a world-readable file.

## Store the token

Run the following and paste only the token at the blank prompt. Press
`Ctrl-D` when finished. The token does not appear in shell history.

```bash
sudo install -d -o root -g root -m 0700 /etc/cloudflared
sudo sh -c 'umask 077; cat > /etc/cloudflared/token'
sudo chown root:root /etc/cloudflared/token
sudo chmod 0600 /etc/cloudflared/token
```

## Install the service

From this repository root:

```bash
sudo install -o root -g root -m 0644 \
  deploy/cloudflared/cloudflared.service \
  /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared.service
sudo systemctl status cloudflared.service --no-pager
```

Systemd reads `/etc/cloudflared/token` as a credential and exposes a temporary,
read-only copy to a dynamically allocated unprivileged service user. The
original remains `0600 root:root`, and neither copy is exposed in the command
line. Package updates remain managed by APT because the service uses
`--no-autoupdate`.

## Verification

```bash
sudo journalctl -u cloudflared.service -n 100 --no-pager
curl -fsS http://127.0.0.1:18088/health/live
curl -I https://rtl.broccolynet.com/
```

Before signing in, the public hostname must show Cloudflare Access rather than
the application. After signing in with the explicitly allowed identity, test
the UI, read-only APIs, and WebSocket pages. Reconfirm that Tailscale HTTPS and
SSH still work and that UFW remains active.

## Emergency rollback

First remove or disable the Published application route (or add a highest
priority `Block / Everyone` Access policy), then stop the connector:

```bash
sudo systemctl disable --now cloudflared.service
```

This leaves Docker, readsb, UFW, and Tailscale untouched. The loopback mapping
can remain in place because it is not reachable from LAN or WAN interfaces.
