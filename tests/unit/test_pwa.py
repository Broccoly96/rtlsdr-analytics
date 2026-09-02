from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[2] / "app" / "static"
MANIFEST_LINK = '<link rel="manifest" href="/manifest.json" crossorigin="use-credentials">'


def test_every_pwa_page_fetches_manifest_with_credentials():
    pwa_pages = []

    for path in sorted(STATIC_DIR.glob("*.html")):
        html = path.read_text()
        if 'rel="manifest"' not in html:
            continue
        pwa_pages.append(path.name)
        assert MANIFEST_LINK in html, (
            f"{path.name} must include credentials when fetching the manifest; "
            "Cloudflare Access otherwise redirects the unauthenticated request"
        )

    assert pwa_pages
