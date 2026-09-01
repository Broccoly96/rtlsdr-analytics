const state = document.querySelector("#state");
const active = document.querySelector("#active");
const position = document.querySelector("#position");
const updated = document.querySelector("#updated");

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const status = await response.json();
    state.textContent = status.ingestion_state === "ok" ? "ONLINE" : status.ingestion_state.toUpperCase();
    active.textContent = status.active_aircraft_count.toLocaleString("ja-JP");
    position.textContent = status.position_aircraft_count.toLocaleString("ja-JP");
    updated.textContent = `更新: ${new Date(status.generated_at).toLocaleString("ja-JP")}`;
  } catch (error) {
    state.textContent = "UNAVAILABLE";
    active.textContent = "—";
    position.textContent = "—";
    updated.textContent = "ステータスを取得できませんでした。";
  }
}

await refresh();
setInterval(refresh, 30_000);
