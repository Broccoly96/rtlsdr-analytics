# Cloudflare Phase 1 検証レポート

- 実施日: 2026-08-31 (UTC)
- 作業ブランチ: `codex/cloudflare-publication-plan`
- 対象: Cloudflare Quick Tunnel による短時間・非永続の疎通確認
- 結論: HTTP/API/WebSocket/PWAと独立したモバイル回線からの機能検証は成功した。UFWをTailscale限定方針で安全に有効化し、LAN IPv4、グローバルIPv6、WAN IPv4の不要port遮断も確認した。Phase 1とPhase 2前のnetwork境界確認は完了。

## 1. 変更範囲

Quick Tunnel検証中は既存アプリ、Docker Compose、Tailscale Serve、systemd、APT、ルーター、UFWを変更しなかった。公式 `cloudflared` バイナリを一時ディレクトリへ展開し、既存のTailscale IPバインドのAPIをoriginとしてQuick Tunnelを短時間起動した。検証後、別作業としてUFWをTailscale限定方針で有効化した。

Quick Tunnelは検証後にCtrl-Cで正常停止した。一時URLは再利用せず、本レポートにも記録しない。

## 2. 実施前ベースライン

- Docker Compose: 7サービスが稼働。`adsb-api` と `adsb-db` はhealthy。
- API公開先: `<TAILSCALE_IP>:8088` のみ。`127.0.0.1:8088` はlistenなし。
- Tailscale Serve: tailnet内HTTPSから上記APIへのproxyが稼働。
- health: `/health/live`、`/health/ready` ともHTTP 200。
- nginx: 未導入。既存lighttpdはport 80を使用。
- cloudflared: システムには未導入。
- `.env`: mode `0664`。秘密情報保護のため本番移行前に`0600`へ変更が必要。

ホストにはSSH、lighttpd、readsbなど既存のall-interface listenがある。ユーザーが`sudo ufw status verbose`を実行した結果、UFWはinactiveだった。WAN側IPv4/IPv6から到達不能であることの確認と、既存Tailscale/SSHを壊さないfirewall設計をPhase 2前の必須条件とする。

## 3. バックアップと回帰テスト

- `scripts/backup.sh`: 成功
- 生成バックアップ: `backups/adsb-db-20260831T132118Z.dump`（159 MiB）
- `scripts/restore_test.sh`: 使い捨てPostgreSQLへの復元・整合性確認・後片付けまで成功
- Ruff: 成功
- unit: 238 passed
- 非Playwright integration: 131 passed
- Playwright UI integration: 9 passed
- 合計: 378 passed

テスト後も本番Compose、Tailscale Serve、healthに変化なし。

## 4. cloudflared とQuick Tunnel

- 公式GitHub Release: `cloudflared 2026.8.3`
- ダウンロードしたDebian packageのSHA-256を公式asset digestと照合: 一致
- 一時配置: `/tmp/rtlsdr-cloudflared-phase1.Wa8FND/root/usr/bin/cloudflared`
- 通信方式: QUIC
- Cloudflare edgeへの登録: 成功
- ルーターのポート開放: 実施なし
- cloudflared metrics: `127.0.0.1:20241` のみでlisten
- 承認後の本試験終了時metrics: total requests 257、request errors 0

`apt install`、systemd service登録、Named Tunnel作成、DNS変更は実施していない。

## 5. Quick Tunnel経由の確認結果

TLS証明書検証を有効にしたHTTPSアクセスを確認した。最初に実データを含まない範囲を確認し、所有者の明示承認後に読み取り専用APIとWebSocketを追加確認した。レスポンス本文、機体識別情報、raw frameは画面やファイルへ出力していない。

| 対象 | 結果 |
| --- | --- |
| `/` | HTTP/2 200 |
| `/manifest.json` | 200 |
| `/sw.js` | 200 |
| `/health/live` | 200 |
| `/health/ready` | 200 |
| `/docs` | 200 |
| `/redoc` | 200 |
| `/openapi.json` | 200 |
| 存在しないpath | 404 |
| Cloudflare edge識別 | `server: cloudflare`、`cf-ray`あり |

次のHTTP security headerはレスポンスになかった。

- `Strict-Transport-Security`
- `X-Content-Type-Options`
- `Content-Security-Policy`（HTML内meta CSPは別途存在）
- `Referrer-Policy`
- `Permissions-Policy`

`/docs`、`/redoc`、`/openapi.json`、`/health/ready` がQuick Tunnelから未認証で到達できることを確認した。本番公開時は一般公開対象から除外する。

### 読み取り専用API

- dashboard、traffic、ranking、track、aircraft、distribution、receiver、weather、favoritesなどのGET: 45/45成功
- content type: JSON、HTML、JavaScript、manifest、PNGを確認
- 不正query、ICAO、未知pathの負系GET: 期待どおり422または404
- favoritesのPOST/DELETE: 実行なし
- DB URL、readsb URL、PostgreSQL password、webhook URL、receiver座標の禁止マーカー: 検出なし

### WebSocket

| 対象 | 結果 |
| --- | --- |
| `/ws/aircraft-positions` | 初回JSON受信、切断後の再接続とも成功 |
| positions fast mode | 有効化後の受信と無効化に成功 |
| `/ws/rawdata` | frame受信成功。内容は非表示・未保存 |
| `/ws/aircraft/000000` | JSON response受信成功 |
| `/ws/aircraft/{current_icao}` | 現在受信中の機体をメモリ内で選択し、JSON response受信成功 |
| 不正なOrigin | 接続が受理された。Origin検証が未実装 |

### ブラウザ/PWA

headless ChromiumをQuick Tunnel経由で使用した。

- dashboard、fullmap、globe、rawdata、receiver: 全画面でHTTP 200、body表示成功
- console error、page error、request failure、HTTP 4xx/5xx: すべて0
- fullmap、globe、rawdata: 画面内WebSocket frame受信成功
- Service Worker: active

### 60秒安定性

- live/ready health: 12周期成功、エラー0
- aircraft positions: 13 frame、エラー0
- rawdata: 2,156 frame、エラー0
- 終了時cloudflared request errors: 0
- 終了時`adsb-api`: CPU約0.8%、memory約74 MiB

### 外部モバイル回線

Wi-Fiを切ったモバイル回線から、dashboard、機体情報、graph、Full Map、Globe、Raw Data、ページ更新後の再接続をユーザーが確認し、すべて正常だった。

## 6. Phase 2へ持ち越す検証

Phase 1のアプリ機能試験、UFW有効化、WAN境界確認は完了した。次はNamed TunnelをCloudflare Accessで本人限定公開してから実施する。

- 高同時接続・長時間soakは既存サービスへ負荷を与えるためPhase 1では未実施。Named Tunnelの本人限定公開後に上限を定めて実施する

状態変更を伴うfavoritesのPOST/DELETEは実行していない。

## 7. セキュリティ所見

Phase 2で一般公開する前に、少なくとも次を解消する。

1. Cloudflare Accessでサイト全体を本人限定にした状態から開始する。
2. 公開hostname専用のdeny-by-defaultなHost/path/method allowlistを実装する。
3. docs、OpenAPI、ready health、favorites、管理・詳細系APIを一般公開しない。
4. WebSocketは初期状態で一般公開しない。公開する場合は`accept()`前のOrigin検証、接続数上限、message size、fast mode頻度制限を追加する。
5. security headerを追加する。HSTSはCloudflare edge、CSPはページごとの既存要件を検証して設定する。
6. API originとして、既存Tailscale mappingを残したまま`127.0.0.1:18088`のloopback mappingを追加する。
7. `.env`を`0600`にし、Tunnel tokenはrootのみ読み取り可能な別ファイルに置く。
8. UFWのdefault deny、Tailscale限定許可、内部readsb限定許可を維持し、WAN到達不能を定期確認する。

## 8. 停止後確認とロールバック状態

- Quick Tunnel process: 停止済み
- metrics port `127.0.0.1:20241`: 消滅
- API listen: 従来どおり`<TAILSCALE_IP>:8088`のみ
- `/health/live`: 200
- `/health/ready`: 200
- Tailscale Serve: 従来どおり稼働
- Compose: 全常駐サービス稼働、healthy状態維持
- cloudflaredのsystemd登録、APT、DNS、ルーター変更: なし

今回のPhase 1試行とUFW有効化について追加ロールバックは不要。Phase 2のNamed Tunnel・Access・アプリ境界実装へ移行できる状態になった。

## 9. UFW実装結果

UFWは当初inactiveで、SSH、lighttpd、readsbがIPv4/IPv6の全interfaceでlistenしていた。Tailscale経由の第2〜第4 SSHセッションと自動ロールバックtimerを確保してから有効化した。

- 変更前`/etc/ufw`: `/root/ufw-backup/`配下へroot専用で保存
- default: deny incoming、allow outgoing、deny routed
- `tailscale0`: IPv4/IPv6のincomingを許可
- Compose `<ADS_B_DOCKER_SUBNET>`からhost
  `<READSB_HOST_GATEWAY>:80/tcp`: readsb HTTP用に限定許可
- WAN向けOpenSSH profile: 削除
- IPv6 filtering: 有効
- logging: low
- boot時のUFW自動有効化: enabled

初回有効化直後、UFWがCompose containerからhost readsb HTTPへの通信を遮断し、collector fetch failureとready health 503を検出した。上記の内部限定ルールを追加後、ready healthは200へ復旧した。WAN向けport 80は許可していない。

検証結果:

- 新規Tailscale SSH: 成功
- Tailscale接続: direct
- PC browserのTailnet URL表示: 成功
- Tailnet HTTPS、live health、ready health: すべて200
- Compose常駐service: 正常、API/DB healthy
- 自動ロールバックtimer: 検証後に停止
- LAN IPv4: 22、80、8088、5432、8504、8542、8754、30001-30005、30104がすべてtimeout
- グローバルIPv6: 22、80、8504、8542、8754、30001-30005、30104がすべてtimeout
- モバイルhotspot経由WAN IPv4: 22、80、443、8088、5432、8504、8542、8754、30001、30005、30104がすべてtimeout
- 対照試験のTailscale IPv4: 22、443、8088がすべて接続成功

Cloudflare Tunnelはoutbound接続だけを使用するため、WAN向け80/443は許可していない。
