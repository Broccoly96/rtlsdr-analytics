// highlight-image.js -- client-side Canvas rendering of daily.html's key
// stats into a shareable PNG (Milestone OO). Deliberately client-side:
// server-side generation would need Pillow promoted from a dev-only extra
// to a runtime dependency (see scripts/generate_pwa_icons.py's own
// docstring), bloating the Docker image for a "nice to have" export.
// Reads already-rendered DOM text rather than re-fetching anything, so the
// image always matches what's on screen.

import { t } from "./i18n.js";

const WIDTH = 900;
const HEIGHT = 640;
const BG_COLOR = "#08111f";
const TEXT_COLOR = "#e8f0fa";
const MUTED_COLOR = "#8fa3bd";
const ACCENT_COLOR = "#22d3ee";

function drawText(ctx, text, x, y, options = {}) {
  const { size = 20, color = TEXT_COLOR, weight = "400", align = "left" } = options;
  ctx.fillStyle = color;
  ctx.font = `${weight} ${size}px sans-serif`;
  ctx.textAlign = align;
  ctx.fillText(text, x, y);
}

function textOf(id) {
  const el = document.getElementById(id);
  return el ? el.textContent.trim() : "--";
}

export function generateHighlightCanvas() {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  let y = 56;
  drawText(ctx, t("highlightImage.title"), WIDTH / 2, y, {
    size: 34,
    weight: "700",
    align: "center",
  });
  y += 34;
  drawText(ctx, textOf("summary-day"), WIDTH / 2, y, {
    size: 18,
    color: MUTED_COLOR,
    align: "center",
  });
  y += 60;

  const cards = [
    [t("daily.card.unique"), textOf("card-unique")],
    [t("daily.card.concurrent"), textOf("card-concurrent")],
    [t("daily.card.messages"), textOf("card-messages")],
    [t("daily.card.positionMax"), textOf("card-position-max")],
  ];
  const cardWidth = WIDTH / cards.length;
  for (let i = 0; i < cards.length; i++) {
    const cx = cardWidth * i + cardWidth / 2;
    drawText(ctx, cards[i][1], cx, y, {
      size: 28,
      weight: "700",
      align: "center",
      color: ACCENT_COLOR,
    });
    drawText(ctx, cards[i][0], cx, y + 26, { size: 13, align: "center", color: MUTED_COLOR });
  }
  y += 100;

  ctx.strokeStyle = "#263750";
  ctx.beginPath();
  ctx.moveTo(60, y);
  ctx.lineTo(WIDTH - 60, y);
  ctx.stroke();
  y += 44;

  const highlights = [
    [t("daily.farthest"), textOf("highlight-farthest")],
    [t("daily.closest"), textOf("highlight-closest")],
    [t("daily.mostObserved"), textOf("highlight-most-observed")],
    [t("daily.fastest"), textOf("highlight-fastest")],
    [t("daily.highest"), textOf("highlight-highest")],
  ];
  for (const [label, value] of highlights) {
    drawText(ctx, label, 60, y, { size: 17, weight: "600" });
    drawText(ctx, value, WIDTH - 60, y, { size: 17, align: "right" });
    y += 42;
  }

  drawText(ctx, "ADS-B Analytics", WIDTH / 2, HEIGHT - 24, {
    size: 13,
    color: MUTED_COLOR,
    align: "center",
  });

  return canvas;
}

export function downloadHighlightImage() {
  const canvas = generateHighlightCanvas();
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `adsb-highlights-${textOf("summary-day") || "today"}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, "image/png");
}
