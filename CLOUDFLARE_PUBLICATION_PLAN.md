# Cloudflare Tunnel による安全なインターネット公開 Plan

- 作成日: 2026-08-31
- 対象ブランチ: `codex/cloudflare-publication-plan`
- 対象ホスト: 現在 `rtlsdr-analytics` と Tailscale Serve が稼働している Linux サーバー
- この文書のスコープ: 調査・設計・作業手順・検証・ロールバック。現時点では実装しない。

## 基本方針と判定ゲート

1. Cloudflare 導入は既存の Docker Compose、readsb、tar1090、lighttpd、Tailscale Serve、Tailscale SSH に対して**追加だけ**で開始する。
2. Phase 1 では `.env`、Compose、Tailscale Serve、UFW、ルーターを変更しない。`cloudflared` をフォアグラウンド実行し、停止すれば即座に公開が終わる構成にする。
3. Quick Tunnel はプロトコル互換性と基本負荷を確認する検証環境であり、本番可用性の証明には使わない。Cloudflare は Quick Tunnel を開発・テスト専用、SLA なし、同時 200 in-flight request 上限、SSE 非対応としている。[Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)
4. 現在のアプリは未認証で、書込み API と負荷増幅可能な WebSocket を含む。このため、Phase 2 の初回公開は必ず Cloudflare Access でサイト全体を本人限定にする。
5. 一般公開は、公開データの合意、公開専用 allowlist、Host/Origin 検証、アプリ側レート/接続制限が実装・検証された後の別ゲートとする。UI のリンクを隠すだけでは分離とみなさない。
6. どの段階でも WAN 側ポート転送は追加しない。SSH、readsb、DB、ホスト管理は Cloudflare Tunnel の ingress に含めない。

推奨する段階は次のとおり。

```text
Phase 1: 一時 Quick Tunnel（非共有 URL、短時間）
  ↓ 互換性・負荷・情報露出の合格
Phase 2A: rtl.<domain> を Named Tunnel + Access で本人限定公開
  ↓ 公開専用境界の実装・セキュリティ試験の合格
Phase 2B: rtl.<domain> の承認済み read-only 機能だけ一般公開

管理経路は全段階で:
My PC → Tailscale → Linux Server / SSH / Tailscale Serve
```

## 1. 現状構成

### リポジトリとアプリ

- Docker Compose の 7 サービス構成。PostgreSQL、migration、collector、retention、daily rollup、aircraft type lookup、FastAPI が分離されている（[compose.yaml](compose.yaml) 13–158 行）。
- `adsb-api` はコンテナ内 `0.0.0.0:8088` で Uvicorn を実行し、ホスト側では `${APP_BIND_HOST}:${APP_PORT}:8088` のみを publish する（[compose.yaml](compose.yaml) 119–155 行）。
- 現在の実値は `APP_BIND_HOST=<TAILSCALE_IP>`、`APP_PORT=8088`。実 IP は公開 repository に残さず、作業時にローカルの `.env` から取得する。これは Tailscale IP だけへの bind であり、`127.0.0.1:8088` では待ち受けていない。
- PostgreSQL はホストポートを公開せず、Docker 内部ネットワークだけで利用される（[compose.yaml](compose.yaml) 1–33 行）。この方針は変更しない。
- collector と API は `host.docker.internal` 経由で既存 readsb を参照する。Quick/Named Tunnel の接続先は readsb や lighttpd ではなく、必ず `adsb-api` の 8088 とする。
- Compose コンテナは約 4 週間稼働中で、`adsb-api` と `adsb-db` は healthy。アプリの `/health/live` と `/health/ready` はともに 200 を返している。
- 起動は `./setup.sh` または `docker compose build` + `docker compose up -d`。API の Docker healthcheck はコンテナ内 `/health/live` を使用する（[setup.sh](setup.sh) 169–247 行、[compose.yaml](compose.yaml) 139–149 行）。
- アプリイメージは Python 3.12 slim、実行ユーザーは非 root の `appuser`（[Dockerfile](Dockerfile) 10–30 行）。一方、read-only root filesystem や capability drop は未設定で、将来のコンテナ hardening 候補である。

### 既存ネットワークとサービス

- Docker と Tailscale は systemd で enabled/active。
- Tailscale Serve は次の tailnet 限定 HTTPS を提供しており、現在正常に利用できる。

  ```text
  https://<TAILNET_HOSTNAME>
    / → http://<TAILSCALE_IP>:8088
  ```

- `cloudflared` は未導入で、ユーザーの `~/.cloudflared/config.yaml` / `config.yml` も存在しない。
- nginx は未導入。80 番は既存 lighttpd/readsb/tar1090 系が利用しているため、Cloudflare 用に使用・変更しない。
- ホストは Ubuntu 26.04 x86-64。UFW は active だが、現在の権限ではルール内容を確認できていない。
- `ss` 上では、8088 は Tailscale IP のみ。一方、22、80、readsb の 30001–30005/30104 等は全インターフェースで listen している。これは WAN 公開を意味するとは限らないが、ルーター転送・UPnP・UFW を含めた外部到達性確認を Phase 1 の必須ゲートにする。既存 feeder を壊すおそれがあるため、readsb の bind やポートは調査なしに変更しない。

### HTTP/API/WebSocket の公開面

- FastAPI が UI、静的ファイル、API、OpenAPI を同じ 8088 で提供する（[app/api/main.py](app/api/main.py) 65–100 行）。`/docs`、`/redoc`、`/openapi.json` もデフォルトで有効。
- HTTP API は大部分が GET だが、共有 favorites を変更する未認証の `POST /api/favorites/{icao}` と `DELETE /api/favorites/{icao}` がある（[app/api/routers/favorites.py](app/api/routers/favorites.py) 46–69 行）。
- WebSocket は 3 系統ある。

  | 経路 | 特性 | 公開時の主なリスク |
  |---|---|---|
  | `/ws/rawdata` | 接続ごとに readsb Beast TCP 接続 | 接続増加、raw ADS-B 配信 |
  | `/ws/aircraft/{icao}` | 接続ごとに readsb HTTP poll | upstream/CPU 負荷、詳細 live data |
  | `/ws/aircraft-positions` | 共有 broadcaster | 任意クライアントの `{"fast": true}` で全体を 1 秒 poll に変更可能 |

- Cloudflare は WebSocket をサポートするが、WAF が検査するのは最初の HTTP 101 upgrade までで、確立後のメッセージは検査しない。また Cloudflare 側再起動や idle timeout で切断され得る。[Cloudflare WebSockets](https://developers.cloudflare.com/network/websockets/)
- `/api/config` は DB URL、readsb URL、受信機の精密座標を返さない（[app/api/routers/config.py](app/api/routers/config.py) 1–36 行）。ただし、履歴、航跡、距離、方位、受信性能、basemap、callsign/ICAO の組み合わせから受信地点や行動範囲を推測される可能性がある。
- アプリに認証、CSRF 対策、WebSocket Origin 検証、Host allowlist はない。現在の origin は任意の Host ヘッダーへ 200 を返す。
- HTML には meta CSP があるが、HTTP レスポンスの HSTS、`X-Content-Type-Options`、`Referrer-Policy`、`Permissions-Policy`、frame 制御等は未設定。応答は `server: uvicorn` も公開している。
- root と静的ファイルは `Cache-Control: no-store`。HTTP の `/api/*` と `/health/*` は Cloudflare 側でも cache bypass を明示し、`/ws/*` は cache ではなく Upgrade を妨げない設定として別に検証する。
- リポジトリには、過去に cloudflared の Compose profile を導入後、Tailscale Serve へ戻した履歴がある。今回はその旧実装をそのまま復活させず、未認証公開・token 管理・proxy header 信頼範囲を改めて設計する。

## 2. Phase 1 の作業 Plan

### 2.1 変更前スナップショット

作業時間帯を決め、二つ目の Tailscale SSH セッションを開いたまま次を記録する。秘密値、メールアドレス、受信機座標、Tunnel URL は成果物や Git に保存しない。

```bash
git status --short --branch
docker compose ps
docker compose logs --tail=100 adsb-api adsb-collector adsb-db
tailscale serve status
ss -ltnp
cf_snapshot_host="$(sed -n 's/^APP_BIND_HOST=//p' .env)"
cf_snapshot_port="$(sed -n 's/^APP_PORT=//p' .env)"
cf_snapshot_origin="http://${cf_snapshot_host}:${cf_snapshot_port}"
curl -fsS "${cf_snapshot_origin}/health/live"
curl -fsS "${cf_snapshot_origin}/health/ready"
```

管理者権限で、変更せずに次を確認する。

```bash
sudo ufw status numbered
sudo nft list ruleset
```

ルーター管理画面で、80/443/8088/22/readsb ポートの手動 port forward がないこと、UPnP に意図しない転送がないことを確認する。Cloudflare Tunnel のための inbound 許可は追加しない。

DB を変更する試験に備え、既存手順でバックアップと復元テストを行う。

```bash
scripts/backup.sh
scripts/restore_test.sh
```

バックアップは repo 内 `backups/` に 600、ディレクトリは 700 で保存される（[scripts/backup.sh](scripts/backup.sh) 13–40 行）。復元テストは使い捨て DB を使い、本番 DB に触れない（[scripts/restore_test.sh](scripts/restore_test.sh) 1–70 行）。

### 2.2 cloudflared の導入

Cloudflare 公式 APT repository から package として導入する。実行時点で公式手順と署名鍵 URL を再確認する。[cloudflared downloads](https://developers.cloudflare.com/tunnel/downloads/) / [Ubuntu/Debian installation](https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/)

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update
sudo apt-get install cloudflared
```

package manager で署名検証・更新経路を固定し、任意の非公式 binary や `latest` container tag は Phase 1 で使わない。

導入後は次だけを確認し、Phase 1 では service install や systemd enable を行わない。

```bash
command -v cloudflared
cloudflared --version
systemctl status cloudflared  # unit が未作成または inactive であること
```

`~/.cloudflared/config.yaml` が後から作られていた場合は作業を止めて内容と所有者を確認する。Quick Tunnel は同ファイルがある構成をサポートしないため、無断で上書き・削除しない。[Quick Tunnel configuration note](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)

### 2.3 Quick Tunnel の起動

現在の bind を変えず、専用ターミナルで次をフォアグラウンド実行する。

```bash
cf_quick_host="$(sed -n 's/^APP_BIND_HOST=//p' .env)"
cf_quick_port="$(sed -n 's/^APP_PORT=//p' .env)"
cf_quick_origin="http://${cf_quick_host}:${cf_quick_port}"
cloudflared tunnel --url "${cf_quick_origin}"
```

- `127.0.0.1:8088` は現在 listen していないため使用しない。
- 発行された `https://<random>.trycloudflare.com` はパスワードではなく、URL を知る誰でもアクセスできる。共有せず、検証担当者だけが短時間使用する。
- Quick Tunnel を systemd/Compose で常駐化しない。
- `--loglevel debug` は request/response header 等を記録し得るため通常は使わず、必要時だけ短時間に限定する。[Tunnel run parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/)
- Quick Tunnel URL、ブラウザ screenshot、ログを issue、チャット、Git に残さない。

### 2.4 段階的な試験

1. サーバー自身から Quick URL の `/health/live`、`/`、代表 API を確認する。
2. Wi-Fi を切ったスマートフォン等、サーバー LAN/Tailscale に属さない回線から同じ確認を行う。
3. UI、API、WebSocket を一つずつ有効にし、各段階で `docker stats`、Compose logs、readsb の接続数、CPU、メモリ、DB ready を観測する。
4. 同時利用は 1 接続から始め、少数クライアントまで増やす。稼働 DB/readsb に対して 200 接続上限を意図的に踏む負荷試験は行わない。
5. `POST/DELETE /api/favorites` は、試験前の状態を記録した一つの ICAO だけで往復確認し、直ちに元の状態へ戻す。
6. 最低 30 分の WebSocket 継続、ネットワーク切替、ブラウザ sleep/resume、`cloudflared` の一度の停止・再起動で再接続を確認する。
7. 検証終了後は Quick Tunnel のプロセスだけを `Ctrl-C` で停止する。Compose や Tailscale を停止しない。

## 3. Phase 1 の検証項目

### 機能・互換性

- [ ] Quick URL が HTTPS で開き、証明書エラー、mixed content、redirect loop がない。
- [ ] `/` と全静的ページ、`/manifest.json`、`/sw.js` が取得でき、PWA installability に異常がない。
- [ ] `/health/live`、`/health/ready`、`/api/status` と代表 read-only API が origin と同じ結果を返す。
- [ ] CSV、GPX、KML、PNG、機体写真 proxy、METAR、地図 tile、Cesium imagery が取得できる。
- [ ] 正常クエリ、上限値、範囲外値（422）、存在しない path（404）、DB/readsb 一時不調時（503/安全な error）が期待どおり。
- [ ] `POST/DELETE /api/favorites/{icao}` が機能し、試験後に元の状態へ戻る。
- [ ] `/ws/rawdata` が `wss://` で 101 となり、frame を受信して切断・再接続できる。
- [ ] `/ws/aircraft/{icao}` が live field を更新し、sidebar を閉じると接続が閉じる。
- [ ] `/ws/aircraft-positions` が通常周期と 1 秒 mode で動き、最後の fast client 切断後に通常周期へ戻る。
- [ ] index/daily/history/archive 等、meta CSP の `connect-src` が異なる各ページから aircraft detail WebSocket がブラウザで遮断されない。
- [ ] 30 分継続、idle、端末 sleep、回線切替、Quick Tunnel 再起動後に UI が自動回復または明確な再読込で回復する。

### セキュリティ・非干渉

- [ ] Quick URL が未認証である事実と、アクセス可能な全 path を棚卸しできた。
- [ ] `/api/config`、error body、OpenAPI、HTML、response header、cloudflared/app logs に `.env`、DB URL/password、Webhook URL、Tunnel credential、精密な受信機座標が出ない。
- [ ] `MAP_SHOW_RECEIVER_MARKER=false` を維持する。
- [ ] `/docs`、`/redoc`、`/openapi.json`、`/health/ready`、favorites、履歴、receiver data、raw/live WebSocket が現状では外部到達可能であることをリスク台帳に記録する。
- [ ] 外部 IPv4/IPv6 の双方からサーバーの WAN address を明示的に検査し、22/80/443/8088/30001–30005/30104 等に意図しない到達がない。検査は所有する IP にだけ実施する。到達可能な port が一つでもあれば、所有者承認の是正が完了するまで Phase 2 は不合格とする。
- [ ] Quick Tunnel 起動前後で `ss -ltnp` を比較し、新しい WAN listen port が増えていない。
- [ ] `adsb-api`、collector、DB、readsb、tar1090、lighttpd、Tailscale Serve/SSH にエラー率、接続数、latency の悪化がない。
- [ ] 少数同時 API/WS 接続で CPU、memory、DB pool、readsb TCP 接続が安定し、切断後に解放される。
- [ ] Quick Tunnel 停止後に URL が使用不能となり、Tailscale Serve と変更前スナップショットの Tailscale origin は継続して正常。

### Phase 1 合格条件

- Critical UI/API が通り、3 種の WebSocket が再接続を含めて動作する。
- Cloudflare 以外の意図しない既存/新規 WAN 公開、secret 漏えい、既存サービス/Tailscale の劣化がない。既存 port の到達が判明した場合は Phase 2 へ進まない。
- 公開データ一覧と一般公開可否が所有者により承認される。
- 負荷試験で app/readsb/DB が安定し、接続上限案を決められる。
- Quick Tunnel の制約を受容しつつ、本番は Named Tunnel + Access/WAF/app hardening で再検証することに合意する。

一つでも満たさない場合、Phase 2 へ進まない。特に「Quick URL で動いた」だけでは一般公開可と判定しない。

## 4. Phase 2 の作業 Plan

### 4.1 ドメイン・アカウント基盤

1. Cloudflare account の MFA、recovery code、管理者メール、監査担当を設定する。
2. Cloudflare Registrar でドメインを取得する。Registrar のドメインは Cloudflare nameserver を使用する。[Registrar setup](https://developers.cloudflare.com/registrar/get-started/register-domain/)
3. registrar lock、auto-renew、期限通知、DNSSEC を有効化し、zone/DNS/Tunnel 用 API token は用途別の最小権限にする。Global API key は使わない。
4. DNS zone の既存/import record を精査し、自宅の origin IP を指す A/AAAA、不要な DNS-only record を作らない。
5. 本番 hostname は `rtl.<domain>`。初回は必ず Access で本人だけを Allow し、Everyone/Bypass policy は作らない。[Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)

### 4.2 Named Tunnel の作成

1. Cloudflare dashboard で remotely-managed Tunnel `rtlsdr-analytics-prod` を作成する。Cloudflare は production で remotely-managed Tunnel を推奨している。[Create a remotely-managed tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
2. Public hostname `rtl.<domain>` を Tunnel に route する。Dashboard の Published application route を使う場合は Dashboard が提示する DNS 設定を確認する。API/manual 方式では `proxied: true` の CNAME を同名で 1 件だけ作り、既存 record と重複させない。origin IP の A/AAAA は作らない。[Published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)
3. Phase 2A の Named Tunnel は Tailscale の起動状態へ依存させない。maintenance window で、既存 `${APP_BIND_HOST}:${APP_PORT}:8088` を残したまま次の secondary loopback-only mapping を追加する。事前に 18088 の未使用を `ss -ltn` で確認する。

```yaml
ports:
  - "${APP_BIND_HOST}:${APP_PORT}:8088"
  - "127.0.0.1:${CLOUDFLARE_ORIGIN_PORT:-18088}:8088"
```

`docker compose config -q` で検証後、`docker compose up -d --no-deps --build adsb-api` のように API だけを再作成する。
4. `adsb-api` だけを再作成し、loopback origin、Tailscale IP direct、Tailscale Serve、live/ready を順に確認する。一つでも失敗したら mapping の commit/config だけを戻して `adsb-api` のみ再作成する。`0.0.0.0` や LAN IP へは広げない。
5. Named Tunnel の origin は `http://127.0.0.1:18088` とする。Phase 1 の Quick Tunnel は引き続き既存 Tailscale bind を使い、Phase 2 の loopback 追加と混在させない。
6. catch-all は HTTP 404 とし、SSH、80 番、readsb port、PostgreSQL、Docker socket を ingress に追加しない。

### 4.3 cloudflared の systemd 常駐化

1. Cloudflare 公式 package の unit をベースにし、実行時に `cloudflared tunnel run --help` でその version の引数を確認する。
2. Tunnel token は repository や `.env` ではなく、root/専用ユーザーだけが読める repo 外の token file に 600 で保存する。token を command line、Git、shell history、journal message に残さない。token 保有者は connector を実行できるため、漏えい時は rotation が必要。[Tunnel tokens](https://developers.cloudflare.com/tunnel/advanced/tunnel-tokens/)
3. `cloudflared --version` が `2025.4.0` 以上であることを確認してから `--token-file` を使う systemd unit/drop-in とし、`Restart=on-failure`、`RestartSec=5s`、`network-online.target`、Docker の起動順を設定する。古い場合は先に更新する。[Tunnel run parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/)
4. metrics は事前に `ss -ltn` で衝突しない固定 port を選び、`127.0.0.1:<固定ポート>` だけで listen させる。unit 適用前に foreground/dry-run 相当で token file 権限と起動を確認し、metrics を外部公開しない。[Tunnel metrics](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/metrics/)
5. baseline unit で正常接続を確認後、`NoNewPrivileges`、`ProtectSystem`、`ProtectHome`、限定 write path 等の systemd sandboxing を一項目ずつ適用する。一括適用で起動不能にしない。
6. `systemctl enable --now cloudflared` 後、Healthy 表示だけで合格にせず、local origin、Tunnel connector、外部 hostname の 3 層を別々に確認する。
7. package update は connector restart を伴うため、maintenance window で実施する。無停止更新が必要になった場合のみ、二つ目の connector/host を検討する。[Update cloudflared](https://developers.cloudflare.com/tunnel/downloads/update-cloudflared/)

### 4.4 HTTPS と edge 設定

1. Universal SSL の Active を待ってから hostname を利用する。full DNS setup では通常 15 分～24 時間を見込む。[Universal SSL](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/enable-universal-ssl/)
2. HTTP → HTTPS redirect と minimum TLS を段階的に有効化する。HSTS は HTTPS/WSS、Access、外部 dependency が安定してから短い `max-age` で開始し、`includeSubDomains`/preload は別判断にする。
3. origin が HTTP の場合、利用者～Cloudflare edge は HTTPS、cloudflared～Cloudflare は Tunnel で暗号化される。origin を HTTPS 化する場合は service URL を `https://...` にし、`originServerName` と必要な `caPool` を設定し、`noTLSVerify: false`（既定）を維持する。zone の Full (strict) は通常の origin TLS mode として別途確認する。[Tunnel origin parameters](https://developers.cloudflare.com/tunnel/advanced/origin-parameters/)
4. HTTP の `/api/*`、`/health/*`、Access 管理面は cache bypass。`/ws/*` は cache rule ではなく Upgrade を妨げないことを確認する。現在の `no-store` を尊重し、個人/リアルタイム data を Cache Everything にしない。
5. HTTP header で CSP、`frame-ancestors`、HSTS、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、`Permissions-Policy` を設定する。Cesium の `unsafe-eval`/`blob:` と外部 tile/photo/weather domain を実ブラウザで回帰確認する。
6. `Server` header、error body、version/git revision の公開要否を決め、不要な fingerprint を減らす。

### 4.5 一般公開部分と管理・高リスク機能の分離

Phase 2A は `rtl.<domain>` 全体を Access で本人限定とする。その状態で次の Phase 2B 実装を行い、完了するまで Access を外さない。

推奨境界:

- `rtl.<domain>`: 承認済み read-only UI/API の allowlist のみ。
- `admin.rtl.<domain>`: 必要な場合だけ作り、hostname 全体を Cloudflare Access で本人/管理グループ限定。より安全な既定は、アプリ管理・SSH を Tailscale だけに残すこと。
- Tailscale Serve hostname/Tailscale IP: 現在の全機能を継続。Cloudflare 障害時の独立した管理経路。

必要なアプリ/edge 実装:

Phase 2B 実装前に、各静的 page が呼ぶ API を自動収集し、次の初期 matrix を owner 承認付きで確定する。`/api/config` は多くの page が依存し version/git revision を含むため、公開値も明示的に決める。

| 初期区分 | path/method | 方針 |
|---|---|---|
| public shell 候補 | `GET/HEAD /`、dashboard に必要な個別 asset、`/manifest.json`、`/sw.js` | `/static/*` を一括許可せず、必要 asset を列挙 |
| public API 候補 | `GET /api/config`、status、traffic/daily、tracks、rankings、recent、hour/altitude/speed distribution、heatmap | tracks/rankings/recent を含め、位置・callsign の privacy 承認後だけ許可 |
| protected/deny | `/docs`、`/redoc`、`/openapi.json`、`/health/ready` | public host から origin へ通さない |
| protected/deny | favorites 全 method、aircraft history/positions/photo/GPX/KML、receiver detail/basemap | owner 承認なしに公開しない |
| protected/deny | `/ws/rawdata`、`/ws/aircraft/{icao}`、`/ws/aircraft-positions` | app 側 resource limit 完了まで公開しない |
| protected UI | fullmap、globe、rawdata、history、archive、receiver 等の HTML | page 単位の依存 API review 後に個別昇格 |

`settings.html` は主に browser localStorage の表示設定であり、サーバー管理画面または認証境界として扱わない。

1. Cloudflare Published application の origin Host は `httpHostHeader=rtl.<domain>` として明示し、public 入口では `rtl.<domain>` だけを許可する。Tailscale hostname/IP と localhost healthcheck は別の内部入口として許可し、public/admin の権限を user-supplied Host だけで決めない。
2. public host は path 正規化後に deny-by-default とし、最初は `GET/HEAD` の `/`、dashboard が実際に必要とする個別 static asset、`/manifest.json`、`/sw.js`、owner 承認済み API だけを許可する。
3. public host では最低限 `/docs`、`/redoc`、`/openapi.json`、`/health/ready`、favorites の全 method、rawdata、live detail、全 WebSocket、詳細履歴/GPX/KML、receiver basemap/詳細統計を deny または Access 保護する。
4. full map/globe/live detail を一般公開する場合は、個別に privacy review を通し、WebSocket Origin allowlist、接続数上限、message size/rate、idle timeout、再接続 backoff、1 秒 mode の権限制御をアプリ側へ実装する。
5. favorites の POST/DELETE は public host で拒否する。admin host で使う場合も Access だけに依存せず、Origin/CSRF と監査 log を追加する。
6. UI は公開 host で到達できない機能を nav から除外し、API deny による壊れた画面を出さない。表示制御だけをアクセス制御の代わりにはしない。
7. `CF-Connecting-IP` 等は、request が信頼済み local cloudflared 経路から来た場合だけ採用する。Uvicorn の `--forwarded-allow-ips=*` は使わない。
8. 正規/未知 Host、port 付き Host、大小文字、IPv6 表記、alternate/admin hostname、encoded path、二重 slash、query 付き deny path、正規/不正 WebSocket Origin を negative test し、迂回できないことを確認する。

### 4.6 Access、WAF、Rate Limit

1. Phase 2A では self-hosted Access application を hostname 全体に設定し、自分の identity の明示 Allow、それ以外 deny を確認する。Access は origin 到達前に適用される。
2. Phase 2B で public host を開ける場合、Access Bypass を広く設定するのではなく、public hostname/app を分ける。Bypass は Access security と request logging を無効にするため、使用時も path を最小化する。[Common Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/common-policies/)
3. Free Managed Ruleset を有効化し、最初は false positive を観測してから block/challenge を強化する。WebSocket の 101、map/Cesium、API export が誤検知されないか確認する。
4. Free plan の Rate Limiting は 1 rule、10 秒 period 等の制約があるため、最も高コストな public API 群へ使用する。正確な上限は Phase 1 の計測値から決める。[Rate limiting plan limits](https://developers.cloudflare.com/waf/rate-limiting-rules/)
5. Cloudflare rate limit だけでは WebSocket 確立後の message や厳密な resource limit を制御できない。アプリ側の connection semaphore、per-IP/session limit、query cost/timeout を併用する。
6. `/api/receiver/basemap.png`、photo proxy、CSV/GPX/KML、heatmap/tracks/archive、WebSocket handshake を優先して abuse test する。特に archive/recent の巨大 `offset`（例 `2147483647`）、同時 request による DB pool 枯渇、5xx/429 後の UI 回復を確認し、必要なら public host で保護または上限を実装する。

### 4.7 Firewall と監視

1. UFW と router の既存ルールを export してから、WAN inbound deny を確認する。SSH は `tailscale0` からのみ許可する方針だが、既存 LAN/readsb feeder の送受信を洗い出すまで一括変更しない。
2. Tunnel に必要な outbound は QUIC の UDP 7844、fallback の TCP 7844。既存 egress を厳格化する場合だけ許可先を Cloudflare 公式要件に合わせる。[Tunnel firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)
3. `cloudflared` journal、Tunnel status/metrics、Cloudflare analytics、Access/WAF event、app 5xx/latency、WebSocket count、DB pool、readsb connection count を監視する。
4. loglevel は通常 `info`。log rotation、保存期間、IP/URL の個人情報、token/header の非記録を確認する。
5. 定期的に `cloudflared` の supported version（latest から 1 年以内）と security update を確認する。[cloudflared support policy](https://developers.cloudflare.com/tunnel/downloads/)

## 5. Phase 2 の検証項目

### DNS/TLS/Tunnel

- [ ] `dig rtl.<domain>` で Cloudflare edge address が返り、自宅 origin IP の A/AAAA が返らない。
- [ ] Cloudflare Dashboard/API で record が `<UUID>.cfargotunnel.com` 向けの proxied CNAME 1 件であることを確認する。proxy/flattening により `dig` で CNAME 自体が見えない場合があるため、`dig` は origin IP 非露出の確認に使う。不要な DNS-only/過去 record もない。
- [ ] Universal SSL が Active、hostname 一致、chain 正常。HTTP は HTTPS へ移行し、TLS policy/HSTS が意図どおり。
- [ ] `cloudflared` は Healthy で、local origin、Tunnel、外部 hostname がそれぞれ正常。
- [ ] WAN の IPv4/IPv6 から 22/80/443/8088/readsb port に直接到達せず、Cloudflare hostname だけが到達可能。
- [ ] Cloudflare 側から SSH、readsb、PostgreSQL、Docker API に route が存在しない。

### Access と公開境界

- [ ] Phase 2A: 未ログイン、許可外 identity、期限切れ session は拒否され、許可 identity だけが利用できる。
- [ ] Phase 2B: public host は allowlist の UI/GET/HEAD だけが成功する。未知 path、非許可 API、変更 method は設計どおり login redirect または 4xx で拒否され、origin に到達しない。実測 status を test の期待値として固定する。
- [ ] `/docs`、`/redoc`、`/openapi.json`、ready、favorites、raw/live/detail/history/receiver の各方針が自動 negative test で固定される。
- [ ] admin hostname を作った場合、Access なしでは一つも route が origin に届かず、public hostname から Host/path を変えて迂回できない。
- [ ] Tailscale SSH/Serve/Tailscale IP は Cloudflare の cookie、DNS、障害に依存せず継続利用できる。

### アプリ機能と耐障害性

- [ ] Phase 1 の HTTP/API/UI/PWA/3 WebSocket matrix を正式 hostname で再実行する。
- [ ] WAF/Access/security header 導入後も CSP、地図、Cesium、service worker、photo/weather、download が動く。
- [ ] WebSocket の 101、30 分継続、idle、回線切替、再接続、Cloudflare edge restart 相当の切断に耐える。
- [ ] `systemctl stop/restart cloudflared` 中も Tailscale access、collector、DB、readsb が継続し、再起動後に hostname が復旧する。
- [ ] `adsb-api` 再起動中は一時的な失敗が発生し得るが、完了後に外部 hostname が自動復旧し、他 service と Tailscale 経路に影響しない。個別 HTTP status は実測値として記録する。
- [ ] planned host reboot 後、Tailscale、Docker、adsb-api、cloudflared が自動復旧し、`/health/ready` と外部 hostname が戻る。reboot 前に out-of-band/二つ目の SSH 経路を確保する。
- [ ] token rotation 後も既存 connector は再起動まで継続し得ることを確認する。旧 token で再起動した connector は新規接続に失敗し、新 token で再導入した connector だけが復旧することを maintenance window で確認する。

### 性能・セキュリティ

- [ ] baseline と比較して p50/p95 latency、CPU、memory、DB pool、readsb 接続数、5xx/429 が許容範囲。
- [ ] public API rate limit と app limit が期待どおりで、正規 UI の burst を誤遮断しない。
- [ ] WebSocket connection/message limit、Origin 検証、fast mode 制御が迂回不能。
- [ ] cache に API、health、Access response、個人 data が保存されない。
- [ ] security header scanner と手動 browser test が合格し、secret/精密座標/stack trace が response/log に出ない。
- [ ] backup/restore test、監視 alert、障害時 runbook、credential owner/rotation 日が記録されている。

### Phase 2 合格条件

- Phase 2A は Access deny-by-default、systemd 自動復旧、Cloudflare 以外の意図しない IPv4/IPv6 WAN direct access 不可、Tailscale 非干渉が揃えば本人限定本番として合格。既存 WAN 到達面が一つでも残る場合は不合格。
- Phase 2B は public allowlist と negative test、アプリ側の WS/API resource limit、privacy approval、WAF/rate limit の実測調整が揃うまで開始しない。

## 6. セキュリティ上の注意点

1. **Quick Tunnel URL は認証ではない。** URL を知る第三者は、favorites の変更を含む現在の全機能へ到達できる。短時間・非共有で使う。
2. **公開データ自体が機微になり得る。** 精密な受信機座標を直接返さなくても、航空機の航跡、方位、最大受信距離、basemap、時系列から設置地点や生活パターンを推測できる。
3. **WebSocket は edge WAF だけで守れない。** handshake 後の message は検査されず、rawdata/aircraft-live は client ごとに upstream resource を消費する。アプリ側制限が必要。
4. **Access と一般公開を同一 hostname/path の広い Bypass で混在させない。** hostname 分離、deny-by-default、アプリ側 Host/path enforcement を併用する。
5. **Cloudflare header を無条件に信頼しない。** origin へ直接到達できる経路では `CF-Connecting-IP` や forwarded header は偽装できる。信頼済み connector 経路に限定する。
6. **Tunnel token は secret。** repository、`.env`、Compose command、journal、shell history に残さず、600 の token file を用いる。漏えい時は即時 rotation。
7. **origin IP を DNS で公開しない。** Tunnel CNAME だけを使い、A/AAAA、DNS-only record、過去 record、メール header 等の露出も確認する。[Protect origin server](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/)
8. **HTTPS は edge だけ見て終わらせない。** certificate、redirect、HSTS、WebSocket、外部 resource、service worker を一体で検証する。HSTS preload は容易に戻せないため初期導入しない。
9. **キャッシュ禁止範囲を明示する。** API、health、Access/admin、個人 data を edge cache に載せない。WebSocket は cache ではなく Upgrade と接続後制御を検証する。
10. **既存ポートを別タスクで監査する。** 現在 22/80/readsb ports は all-interface listen。Tunnel 導入と同時に無計画な firewall/bind 変更をせず、feeder/LAN 依存を調べた上で Tailscale-only SSH と WAN deny を実現する。
11. **既存 `.env` の権限も確認する。** secret を含むため所有者/必要 group 以外から読めない 600/640 相当を検討し、変更前に Compose 実行ユーザーとの互換性を確認する。
12. **Cloudflare は単独の認証・resource control ではない。** Access/WAF/Rate Limit に加え、アプリの認可、CSRF/Origin、入力上限、timeout、connection limit を defense in depth で実装する。

## 7. 想定される問題とロールバック方法

| 問題 | 切り分け | ロールバック/緩和 |
|---|---|---|
| Quick Tunnel が起動しない | `cloudflared --version`、既存 `~/.cloudflared/config.*`、DNS、UDP/TCP 7844、時刻を確認 | config を削除せず停止。必要なら reviewed backup 後に一時退避。UDP 制限時は公式手順で HTTP/2 fallback を確認 |
| Quick URL が 502 | 変更前スナップショットの origin health、Compose health、cloudflared log を別々に確認 | Quick process を停止。アプリ/Tailscale は触らない |
| WebSocket が切れる/403 | browser DevTools の 101/CSP/Origin、cloudflared/app log、idle、client reconnect を確認。WAF/Security Events は Phase 2 だけで確認 | 問題 route の一般公開を止め Access 配下へ戻す。app reconnect/heartbeat 完了まで公開しない |
| API/WS で CPU/readsb/DB が過負荷 | `docker stats`、DB pool、readsb connection、route 別 log を確認 | 最初に Access の `Block / Include Everyone` または rate rule、次に Tunnel route 停止。Compose/readsb を停止しない |
| WAF false positive | Security Events の rule ID と path を確認 | 全 WAF を外さず、対象 rule/path だけを時間限定 skip。直後に回帰試験 |
| Universal SSL 未発行 | Edge Certificates/DCV/proxy status を確認し最大 24 時間待つ | DNS を焦って origin A record に変えない。Access/Tunnel は閉じたまま待つ |
| systemd 起動順で origin unreachable | loopback mapping、Docker/API health、journal を確認 | cloudflared だけ再起動。`After=network-online.target docker.service` と API 自動復旧を修正。Tailscale は変更しない |
| host reboot 後に adsb-api bind 失敗 | Tailscale interface と Docker journal、Compose status を確認 | Tailscale 起動後に `adsb-api` だけ再作成。readsb/DB volume/Tailscale config は触らない |
| Tunnel token 漏えい | Cloudflare audit、connector 一覧、secret 出現箇所を確認 | token rotation 後、必要に応じ既存 connection を明示切断。旧 token は新規接続不可、新 token file で全 connector を再導入。Git history に入った場合は別途 incident 対応 |
| Cloudflare 障害 | Cloudflare status、Tunnel status と Tailscale direct health を比較 | 公開は停止状態として扱い、管理は Tailscale SSH/Serve で継続。WAN port を代替公開しない |
| public/admin 境界の迂回 | Host/path/method 変形、直接 API、WebSocket、encoded path を negative test | 即座に対象 Access application へ `Block / Include Everyone` を適用し、app allowlist を修正するまで再公開しない |

### Phase 1 の即時ロールバック

1. Quick Tunnel を起動した専用ターミナルで `Ctrl-C`。PID を使う場合は起動時に記録した**その PID だけ**を停止し、`pkill cloudflared` のような広い停止をしない。
2. Quick URL が到達不能になったことを外部回線で確認する。
3. `docker compose ps`、origin の live/ready、Tailscale Serve URL、Tailscale SSH、readsb を確認する。
4. Phase 1 では設定を変更していないため、Compose down、Tailscale reset、DB restore は行わない。

### Phase 2 の緊急停止とロールバック

開始前に、変更前の `APP_BIND_HOST`/`APP_PORT`、Tailscale Serve upstream、loopback mapping、Named Tunnel ingress、systemd unit/drop-in、DNS/Access/WAF、UFW/nftables を secret を除いて保存し、各 rollback はこの snapshot を正とする。

1. 最速の封鎖は、対象 Access application の最優先に `Block / Include Everyone` policy を一時適用するか、Published application route を無効化する。実際の dashboard/API 操作を runbook に記録し、まず edge で新規到達を止める。
2. `sudo systemctl stop cloudflared` で connector だけを止める。必要なら復旧方針決定後に disable する。
3. Tailscale SSH/Serve、変更前スナップショットの origin、collector、DB、readsb が正常なことを確認する。
4. DNS/Access/WAF は保存した直前の正常 export へ戻す。DNS 伝播中も `Block / Include Everyone` を維持する。
5. Tunnel 自体は調査が終わるまで削除しない。remotely-managed Tunnel の削除は不可逆である。[Tunnel FAQ](https://developers.cloudflare.com/cloudflare-one/faq/cloudflare-tunnels-faq/)
6. app/Compose を変更していた場合は、対象 commit を revert し、`adsb-api` だけを build/recreate する。全 Compose を down しない。
7. `.env`、bind、loopback mapping を変更していた場合だけ snapshot を戻し、`adsb-api` のみ再作成して loopback と Tailscale を再検証する。systemd unit/drop-in と ingress も snapshot へ戻す。
8. DB migration は Tunnel 導入に不要。`docker compose down -v`、DB volume 削除、`scripts/reset_db.py`、readsb/tar1090/fr24feed の停止・再設定はロールバックに使用しない。

## 実装開始前に所有者が決める事項

- 一般公開するのは dashboard の集計だけか、履歴/航跡/callsign/live position まで含めるか。
- `rtl.<domain>` を最終的に完全公開するか、恒久的に Access 本人限定にするか。
- public WebSocket を許可するか。許可する場合の最大接続数、1 秒 mode、rawdata の扱い。
- `admin.rtl.<domain>` を作るか、管理 Web UI も Tailscale のみにするか。
- Cloudflare Free plan の範囲で運用するか、追加 WAF/rate/log/HA 要件に応じて plan を上げるか。
- 監視通知先、ログ保存期間、token rotation 担当、maintenance window。

これらの判断が未確定でも Phase 1 は短時間・非共有で実施可能だが、Phase 2B の一般公開は開始しない。
