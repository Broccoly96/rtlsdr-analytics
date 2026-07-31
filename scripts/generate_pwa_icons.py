"""One-off generator for this app's PWA icons and favicon
(app/static/icons/) -- not part of the runtime app, just a dev-time
asset-generation tool (Pillow is a `dev` extra in pyproject.toml, not a
runtime dependency of the deployed image). Re-run this script and commit
its output if the icon design ever changes; nothing at runtime
regenerates these.

Reuses the exact same "jet" silhouette polygon app/static/js/aircraft-icons.js
draws for the track map's live-mode icons (scaled up), so the PWA icon
visually matches this app's own aircraft iconography instead of being an
unrelated logo.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"

BG_COLOR = "#08111f"  # style.css's --bg
FG_COLOR = "#22d3ee"  # style.css's --accent

# Same polygon aircraft-icons.js's SHAPE_BODIES.jet draws (24x24 viewBox,
# nose pointing up).
JET_POINTS_24 = [
    (12, 1), (15, 10), (23, 16), (23, 18), (15, 15), (15, 20), (19, 23),
    (19, 24), (12, 22), (5, 24), (5, 23), (9, 20), (9, 15), (1, 18),
    (1, 16), (9, 10),
]  # fmt: skip

# Maskable-icon safe zone: an OS may crop to any mask shape (circle,
# squircle, rounded square, ...), but content within the centered
# 40%-of-size-radius circle always survives it -- kept well inside that
# (0.6 of the full size, not the max 0.8) since the jet shape's wingtips
# reach all the way to its own bounding box corners.
SAFE_ZONE_FRACTION = 0.6


def render_icon(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)
    scale = (size * SAFE_ZONE_FRACTION) / 24
    offset = (size - 24 * scale) / 2
    points = [(offset + x * scale, offset + y * scale) for x, y in JET_POINTS_24]
    draw.polygon(points, fill=FG_COLOR)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_icon(512).save(OUT_DIR / "icon-512.png")
    render_icon(192).save(OUT_DIR / "icon-192.png")
    render_icon(32).save(OUT_DIR / "favicon-32.png")
    print(f"wrote icon-512.png, icon-192.png, favicon-32.png to {OUT_DIR}")


if __name__ == "__main__":
    main()
