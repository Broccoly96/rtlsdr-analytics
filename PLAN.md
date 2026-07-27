# ADS-B Analytics MVP 継続実装計画

## 0. この計画の位置づけ

この文書は、初期の `Plan.md` に沿って以下まで実装済みの状態から作業を再開するための計画である。

### 実装済み

- Phase 0環境検査
- Linux x86-64サーバーでの全チェックPASS
- Docker Engine / Docker Compose v2の導入確認
- readsb JSONの疎通・更新確認
- 既存readsb、tar1090、fr24feedへの非干渉確認
- リポジトリとPythonプロジェクトの初期化
- README、`.gitignore`、`.env.example`
- lint、format、testの基本設定
- 匿名化fixture
- collectorの以下のロジック
  - readsb HTTP取得
  - 設定検証
  - readsbデータの内部モデル変換
  - staleデータ除外
  - 距離・方位計算
  - 航跡保存の間引き
  - 1分集計
  - 再試行とバックオフ
  - 正常終了処理
- `app/collector/store.py` のStore Protocol
- InMemoryStoreを利用したcollectorテスト

### 未実装または未完了

- PostgreSQLコンテナ、スキーマ、マイグレーション
- Store Protocolに準拠したPostgreSQL実装
- FastAPI
- MapLibre/EChartsダッシュボード
- 保持期限、DB運用、バックアップ
- Compose全体構成
- 結合・障害・復旧試験
- Linuxサーバーへの本番配置
- 24時間連続稼働試験

第一目標は、Phase 1 MVPを本番サーバー上で完成させることである。Phase 1の受け入れ完了後に着手できるPhase 2候補も末尾に記載する。

---

## 1. Codexエージェント向け最重要ルール

1. 作業開始時に、実際のリポジトリ、Git差分、テスト結果、Store Protocolを確認する。
2. この文書より実コードを優先して現状を判断する。ただし、仕様変更が必要なら理由を記録する。
3. 既存collectorの動作を維持する。PostgreSQL対応のためにcollector全体を書き直さない。
4. InMemoryStoreを残し、単体テストで引き続き利用する。
5. PostgreSQL実装は既存Store Protocolに準拠させる。
6. Protocolが不足する場合は、必要最小限のメソッドだけを追加し、両Storeの契約テストを更新する。
7. readsb、tar1090、fr24feedを停止・再起動・再設定しない。
8. 本番readsbを使った障害試験は行わない。停止・異常試験にはfixtureまたはモックを使う。
9. `.env`、DBパスワード、fr24feed共有キー、精密な受信地点をコミットしない。
10. PostgreSQLポートを外部へ公開しない。
11. 公開ポート、ファイアウォール、TLS、DNSの変更は対象と影響を確認してから行う。
12. 各マイルストーンの終了時に、テスト結果と残課題を本ファイルへ追記する。
13. 既存のユーザー変更を上書きしない。
14. 依存パッケージを追加する前に、既存依存関係で実現できないか確認する。
15. MVP完了までは機能追加より、正確性、復旧性、データ保持、安全な配置を優先する。

---

## 2. ステータスの記法

- `[ ]` 未着手
- `[-]` 作業中
- `[x]` 完了し、テスト済み
- `[!]` ブロック中。直下に原因と必要な判断を記載する

チェックを`[x]`にする条件は、コードを書いたことではなく、対応するテストまたは実環境確認が完了したことである。

---

## 3. 完成時の構成

```text
readsb aircraft.json
        |
        v
 adsb-collector
        |
        v
   PostgreSQL <──── adsb-api ────> Web browser
                                    |       |
                                    |       └─ ECharts
                                    └───────── MapLibre GL JS
```

Docker Composeサービス：

- `adsb-db`
- `adsb-migrate`
- `adsb-collector`
- `adsb-api`

ネットワーク：

- DBはCompose内部ネットワークだけに接続する。
- APIだけをホストへ公開する。
- collectorからreadsbへの経路は、Phase 0で確認済みの接続先を使用する。
- readsbの接続先をコードへ固定しない。

起動順序：

1. DBのhealthcheck成功
2. migrationの正常終了
3. collectorとAPIの起動

migration失敗時にcollectorやAPIが古いスキーマで起動し続けない構成にする。

---

## 4. Milestone A：再開前ベースライン確認

### A-1. リポジトリ確認

- [ ] Git statusを確認し、既存変更を記録する。
- [ ] プロジェクト構造を確認する。
- [ ] Pythonバージョンと依存管理方式を確認する。
- [ ] `app/collector/store.py`を読み、Protocolの全メソッドと型を一覧化する。
- [ ] InMemoryStoreの実装とテストを確認する。
- [ ] collectorの起動エントリーポイントを確認する。
- [ ] 設定クラスと環境変数名を確認する。
- [ ] 既存Compose、Dockerfile、migration関連ファイルの有無を確認する。

### A-2. テスト基準線

- [ ] 現在の全テストを実行する。
- [ ] lintを実行する。
- [ ] formatterのcheckモードを実行する。
- [ ] 型チェックが設定済みなら実行する。
- [ ] 失敗があれば「既存失敗」と「今回の変更による失敗」を区別できるよう記録する。

### A-3. 設計差分確認

以下が初期計画と異なる場合は、実装前にこの文書へ記録する。

- [ ] データモデル名
- [ ] Store Protocolの責務
- [ ] 同期/非同期I/O方式
- [ ] ORMまたはSQLライブラリ
- [ ] Web UIの配信方式
- [ ] コンテナ構成

### Milestone A 完了条件

- [ ] 既存テストが通る、または既存失敗が明確に記録されている。
- [ ] PostgreSQL実装に必要なProtocolとデータ型が把握できている。
- [ ] ユーザー作業と競合する変更がない。

---

## 5. Milestone B：PostgreSQL永続化

### B-1. 技術選定

既存プロジェクトの同期/非同期方式に合わせる。新規選定が必要な場合は以下を既定とする。

- PostgreSQL 16系の固定メジャータグ
- SQLAlchemy 2系
- async collector/APIなら`asyncpg`
- migrationはAlembic
- タイムスタンプは`TIMESTAMPTZ`
- DB内時刻はUTC

イメージを`latest`へ固定しない。

### B-2. ComposeのDB定義

- [ ] `adsb-db`を定義する。
- [ ] DBデータをnamed volumeへ保存する。
- [ ] DBポートをホストへ公開しない。
- [ ] DBユーザー、DB名、パスワードを環境変数化する。
- [ ] パスワードに開発用既定値を本番で使わせない。
- [ ] `pg_isready`によるhealthcheckを追加する。
- [ ] ログサイズ上限を設定する。
- [ ] graceful shutdown期間を設定する。

### B-3. 初期スキーマ

実コードのモデルを確認し、少なくとも以下を表現する。

#### `aircraft`

- `icao`：正規化済みICAOアドレス、主キー
- `first_seen_at`
- `last_seen_at`
- `last_callsign`

#### `observations`

- `id`
- `observed_at`
- `icao`
- `callsign`
- `lat`
- `lon`
- `altitude_ft`
- `ground_speed_kt`
- `track_deg`
- `vertical_rate_fpm`
- `rssi`
- `distance_km`
- `bearing_deg`
- `source_age_seconds`
- 必要ならcollectorが使用する追加列

#### `traffic_minute`

- `bucket_at`：主キー
- `active_aircraft_count`
- `position_aircraft_count`
- `message_count_delta`

#### `ingestion_status`

- `id`または`checked_at`を一意キーとする。
- `checked_at`
- `success`
- `latency_ms`
- `aircraft_count`
- `error_code`

### B-4. 制約とインデックス

- [ ] ICAOアドレスの形式または長さを制約する。
- [ ] 緯度は`-90..90`、経度は`-180..180`を制約する。
- [ ] 距離、速度、方位など明らかな不正値を防ぐ。
- [ ] `observations (icao, observed_at DESC)`を作る。
- [ ] `observations (observed_at DESC)`を作る。
- [ ] `observations (distance_km, observed_at DESC)`を作る。
- [ ] `aircraft (last_seen_at DESC)`を作る。
- [ ] `ingestion_status (checked_at DESC)`を作る。
- [ ] 1回のpoll再処理で観測が不当に重複しない一意性を検討する。
- [ ] APIの実クエリを確認し、不要なインデックスを増やさない。

### B-5. migration

- [ ] 初期migrationを作成する。
- [ ] 空DBへのupgradeをテストする。
- [ ] 同じDBへの再実行が安全であることを確認する。
- [ ] downgradeまたはロールバック方針を文書化する。
- [ ] migration専用Composeサービスを追加する。
- [ ] migrationの失敗を起動ログで明確に確認できるようにする。

### B-6. PostgresStore

- [ ] Store Protocolに準拠する`PostgresStore`を作成する。
- [ ] 接続プールを設定する。
- [ ] 起動時接続と終了時closeを実装する。
- [ ] 1回のpollに関係する更新を適切なトランザクションへまとめる。
- [ ] `aircraft`のupsertを実装する。
- [ ] `observations`のバルクinsertを実装する。
- [ ] `traffic_minute`のupsertを実装する。
- [ ] `ingestion_status`の保存を実装する。
- [ ] 一部保存後の例外で不整合が残らないことを確認する。
- [ ] DB停止時に無制限のメモリキューを作らない。
- [ ] DB復旧後にcollectorが再接続できるようにする。
- [ ] SQLパラメータを必ずバインドし、文字列連結でSQLを組み立てない。

### B-7. Store契約テスト

同じテストケースをInMemoryStoreとPostgresStoreへ適用できる形にする。

- [ ] aircraftの新規作成
- [ ] aircraftのlast seen更新
- [ ] callsignが空の観測で有効な既存callsignを不用意に消さない
- [ ] observation保存
- [ ] 同一観測の再処理
- [ ] 1分集計のupsert
- [ ] ingestion成功/失敗状態の保存
- [ ] トランザクションロールバック
- [ ] UTCタイムスタンプ
- [ ] close後の接続解放

### Milestone B 完了条件

- [ ] Compose上の空DBへmigrationできる。
- [ ] collectorがfixtureをPostgreSQLへ保存できる。
- [ ] Store契約テストがInMemoryStoreとPostgresStoreの両方で通る。
- [ ] PostgreSQLポートがホスト外部へ公開されていない。
- [ ] コンテナ再作成後もデータが残る。

---

## 6. Milestone C：FastAPIと分析クエリ

### C-1. API構成

- [ ] FastAPIアプリのfactoryまたは明確なentry pointを作る。
- [ ] 起動時に設定を検証する。
- [ ] DB接続をdependencyとして注入する。
- [ ] API用のread repositoryを作る。
- [ ] collectorのwrite StoreとAPIのread queryを密結合させない。
- [ ] 例外を秘密情報のない統一JSONへ変換する。
- [ ] OpenAPI上でレスポンス型を確認できるようにする。
- [ ] CORSは不要なら有効化しない。

### C-2. Health API

#### `GET /health/live`

- Webプロセスが応答できれば200を返す。
- DBやreadsbの一時障害だけでlivenessを失敗させない。

#### `GET /health/ready`

- DBへ軽量クエリを実行する。
- 最終取得成功時刻を確認する。
- 最終成功が閾値より古ければ503を返す。
- 応答に秘密情報やreadsb URLを含めない。

- [ ] liveの正常・異常テスト
- [ ] readyのDB停止テスト
- [ ] readyのデータstaleテスト
- [ ] 復旧後にreadyが200へ戻るテスト

### C-3. Status API

`GET /api/status`

- `generated_at`
- `last_ingestion_at`
- `ingestion_state`
- `active_aircraft_count`
- `position_aircraft_count`
- `data_age_seconds`
- `display_timezone`

- [ ] データがまだない状態を正常に表現する。
- [ ] staleデータを正常表示しない。
- [ ] 現在受信中の定義をcollectorと一致させる。

### C-4. Traffic API

`GET /api/traffic?hours=24`

- `hours`は1～168時間へ制限する。
- 1分集計を時系列で返す。
- 空の時間帯をUIが扱える形式にする。
- `active_aircraft_count`
- `position_aircraft_count`
- 可能なら期間ユニーク機体数も返す。

- [ ] 1時間、24時間、168時間
- [ ] 範囲外入力
- [ ] データなし
- [ ] UTCと表示タイムゾーン境界

### C-5. Tracks API

`GET /api/tracks?hours=6`

- `hours`は1～24時間へ制限する。
- GeoJSON `FeatureCollection`を返す。
- 1機を1つの`LineString`または複数segmentとして表現する。
- ICAO、callsign、最終高度、最終速度、最終観測時刻をpropertiesへ含める。
- 長い受信空白や不自然な位置ジャンプを同じ線で結ばない。
- 航空機数、点数、レスポンスサイズへ上限を設ける。
- 既定の総点数上限を設定し、超過時は時間方向に間引く。

安全な初期上限例：

- 最大100機
- 最大10,000点
- 最大24時間

実測に応じて調整する。

### C-6. Rankings API

`GET /api/rankings?hours=24&limit=10`

- `hours`は1～168時間へ制限する。
- `limit`は1～100へ制限する。
- 最遠と最接近を分けて返す。
- 同一機体がランキングを独占しないよう、機体ごとの期間内最大/最小を使う。
- ICAO、callsign、距離、方位、高度、観測時刻を返す。
- 無効位置を除外する。

### C-7. Recent aircraft API

`GET /api/aircraft/recent`

- 期間、件数、ページングを制限する。
- 最終観測の新しい順に返す。
- ICAO、callsign、first seen、last seenを返す。

### C-8. クエリ性能

- [ ] 代表データ量を生成する。
- [ ] traffic、tracks、rankingsの実行計画を確認する。
- [ ] N+1 queryがないことを確認する。
- [ ] APIのタイムアウトを設定する。

初期目標：

- status/health：200ms以内
- traffic/rankings：500ms以内
- tracks：2秒以内

同一LAN・通常負荷での目安とし、サーバー性能に応じて実測値を記録する。

### Milestone C 完了条件

- [ ] 全APIがOpenAPIと一致する。
- [ ] 入力値上限が機能する。
- [ ] DB・データ未取得・stale状態を区別できる。
- [ ] 代表データ量で性能目標を満たすか、実測と改善案が記録されている。
- [ ] APIの自動テストが通る。

---

## 7. Milestone D：モダンなMapLibreダッシュボード

### D-1. デザイン方針

航空管制画面の模倣ではなく、読みやすい分析ダッシュボードにする。

- ダークテーマを既定とする。
- 背景は完全な黒ではなく、濃い青灰色を使う。
- ベースマップは情報量を抑え、航跡を主役にする。
- アクセントはシアンまたは青。
- 警告は黄、異常は赤、正常は緑に固定する。
- カードは控えめな境界線と角丸を使う。
- 強い発光、過剰な影、過剰なアニメーションを避ける。
- 数字には桁幅が安定するフォント設定を使う。
- PC、タブレット、スマートフォンで主要情報が読める。

推奨カラートークン例：

```text
--bg:             #08111f
--surface:        #101b2d
--surface-raised: #162338
--border:         #263750
--text:           #e8f0fa
--text-muted:     #8fa3bd
--accent:         #22d3ee
--accent-2:       #60a5fa
--success:        #34d399
--warning:        #fbbf24
--danger:         #fb7185
```

実装時はWCAGコントラストを確認し、色だけで状態を表現しない。

### D-2. 地図スタイル

- [ ] MapLibre GL JSを利用する。
- [ ] `MAP_STYLE_URL`でstyle URLを切り替えられるようにする。
- [ ] MapTiler等のAPIキーをコードへ埋め込まない。
- [ ] 開発用スタイルと本番用スタイルを設定で分けられるようにする。
- [ ] attributionを隠さない。
- [ ] 日本語ラベル表示を確認する。
- [ ] `localIdeographFontFamily`を適切に設定する。
- [ ] style/tile取得失敗を検出し、地図部分だけにエラー表示する。
- [ ] 地図失敗時もグラフとランキングを利用可能にする。

初期選択：

- 素早いMVP：OpenFreeMap等の公開style URL
- 見た目優先：MapTiler Dataviz Dark等
- プライバシー/自立運用優先：Phase 2でProtomaps/PMTilesをセルフホスト

どの提供元でも、利用条件、APIキー、リクエスト上限、attributionを確認する。

### D-3. 地図上の航跡

- [ ] GeoJSON sourceとして航跡を追加する。
- [ ] 高度に応じて航跡色を変える。
- [ ] 不明高度は灰色にする。
- [ ] 航跡へ適度な透明度を設定する。
- [ ] 選択中の航跡を太く表示する。
- [ ] ホバーまたはクリックで機体情報を表示する。
- [ ] callsign、ICAO、高度、速度、最終観測、距離を表示する。
- [ ] 長い空白を跨いだ直線を描かない。
- [ ] 受信地点は初期状態で精密表示しない。
- [ ] 自動ズーム時も自宅位置を過度に強調しない。
- [ ] 点数が多い場合にブラウザーを固めない。

高度色の初期案：

```text
地上/低高度      黄
10,000 ft未満   緑
10,000–25,000   シアン
25,000–35,000   青
35,000 ft以上   紫
高度不明         灰
```

色覚多様性とダーク背景での識別性を目視確認し、必要なら凡例と線種を併用する。

### D-4. 画面構成

#### ヘッダー

- アプリ名
- 取得状態
- 最終更新時刻
- 期間切替

#### ステータスカード

- 現在受信中
- 位置取得中
- 24時間ユニーク機体数
- 最終成功取得

#### メイン領域

- 航跡地図
- 24時間交通量グラフ

#### 下部

- 最遠ランキング
- 最接近ランキング
- 最近観測した機体

- [ ] 読み込み中skeletonを実装する。
- [ ] データなし表示を実装する。
- [ ] API異常表示を実装する。
- [ ] stale表示を実装する。
- [ ] 最終更新を定期更新する。
- [ ] ブラウザータブ非表示時に過剰なpollをしない。

### D-5. ECharts

- [ ] UTCデータを指定タイムゾーンで表示する。
- [ ] activeとpositionを区別して描画する。
- [ ] tooltipへ時刻と値を表示する。
- [ ] 欠測をゼロと誤認させない。
- [ ] 1h、6h、24hの表示切替を検討する。
- [ ] ウィンドウサイズ変更時にresizeする。
- [ ] グラフ描画失敗が画面全体を壊さない。

### D-6. レスポンシブ・アクセシビリティ

- [ ] 1440px前後のデスクトップで確認する。
- [ ] 768px前後のタブレットで確認する。
- [ ] 375px前後のスマートフォンで確認する。
- [ ] キーボードで主要操作ができる。
- [ ] フォーカス表示が見える。
- [ ] 状態を色だけで表現しない。
- [ ] 表に見出しと適切なラベルを付ける。
- [ ] `prefers-reduced-motion`へ対応する。

### D-7. フロントエンド方針

初期計画どおり、不要なSPAフレームワークは追加しない。既存構成を確認し、FastAPIから静的ファイルまたはテンプレートを配信する。

- [ ] JavaScriptをAPI、map、chart、UIの責務に分ける。
- [ ] npmを使う場合はlockfileをコミットする。
- [ ] CDN依存を採用する場合はバージョン固定とCSPを検討する。
- [ ] 任意HTMLをAPIデータから挿入しない。
- [ ] callsignなど外部入力を安全にテキスト表示する。

### Milestone D 完了条件

- [ ] 全MVP情報が1画面で確認できる。
- [ ] MapLibreの地図がモダンで、航跡とラベルを読み分けられる。
- [ ] 地図タイル障害時も他機能が使える。
- [ ] PCとスマートフォンで主要情報が読める。
- [ ] stale/異常/データなしを正常状態と誤認しない。
- [ ] ブラウザーで重大なconsole errorがない。

---

## 8. Milestone E：保持、バックアップ、運用

### E-1. 保持期限

- [ ] `RAW_RETENTION_DAYS`を設定可能にする。
- [ ] 既定30日より古いobservationsを削除する。
- [ ] 削除は小さなbatchで行う。
- [ ] 1分集計を削除対象に含めない。
- [ ] 削除件数と所要時間をログへ出す。
- [ ] 同時実行を防止する。
- [ ] 保持処理のdry-runを用意する。
- [ ] 境界時刻をUTCでテストする。

### E-2. DB状態確認

管理コマンドで以下を確認できるようにする。

- DB総サイズ
- テーブル別サイズ
- observations件数
- 最古・最新観測時刻
- 過去24時間の増加件数
- 1日当たり推定増加容量
- 30日後の推定容量
- 最終ingestion成功時刻

- [ ] コマンドをREADMEへ記載する。
- [ ] 秘密情報を出力しない。

### E-3. バックアップ

- [ ] `pg_dump`による論理バックアップを実装する。
- [ ] バックアップ先を設定可能にする。
- [ ] ファイル名にUTC日時を含める。
- [ ] 一時ファイルを安全に扱う。
- [ ] 失敗時に不完全ファイルを正常バックアップとして残さない。
- [ ] 保持世代数を設定可能にする。
- [ ] バックアップファイル権限を確認する。
- [ ] 本番とは別の一時DBへ復元試験する。
- [ ] 復元後の件数と代表クエリを確認する。

### E-4. ログ

- [ ] JSONまたは一貫した構造化ログを使用する。
- [ ] 正常pollごとの過剰ログを避ける。
- [ ] 接続失敗と回復を記録する。
- [ ] 不正データ除外件数を記録する。
- [ ] Dockerログの`max-size`と`max-file`を設定する。
- [ ] パスワード、完全な接続URL、レスポンス本文をログへ出さない。

### Milestone E 完了条件

- [ ] 保持期限処理がテストデータで機能する。
- [ ] DB増加量を確認できる。
- [ ] backupと別DBへのrestoreが成功する。
- [ ] ログが容量無制限に増えない。

---

## 9. Milestone F：Compose統合と障害試験

### F-1. イメージ

- [ ] x86-64でビルドできる。
- [ ] Pythonベースイメージを固定する。
- [ ] multi-stage buildまたは不要ファイル除外でサイズを抑える。
- [ ] `.dockerignore`を用意する。
- [ ] 非rootユーザーでcollector/APIを実行する。
- [ ] healthcheckに不要な大型ツールを追加しない。
- [ ] イメージに`.env`や実データを含めない。

### F-2. Compose

- [ ] `adsb-db`
- [ ] `adsb-migrate`
- [ ] `adsb-collector`
- [ ] `adsb-api`
- [ ] named volume
- [ ] internal network
- [ ] APIだけのポート公開
- [ ] restart policy
- [ ] healthcheck
- [ ] ログ上限
- [ ] graceful shutdown

collectorは1インスタンスだけ起動する。将来APIを複数化してもcollectorが重複起動しないよう責務を分ける。

### F-3. readsbへのコンテナ内疎通

- [ ] Phase 0で確認済みのURLをコンテナ内から取得できるか確認する。
- [ ] `127.0.0.1`がホストではなくコンテナ自身を指す点を考慮する。
- [ ] `host.docker.internal`、host gateway、LAN IP等を環境に合わせて検証する。
- [ ] readsbがホストloopbackにしかbindしていない場合、勝手にbind先を変更しない。
- [ ] 疎通できない場合は以下を比較してユーザーへ提示する。
  - readsb既存HTTP公開範囲の最小変更
  - collectorのネットワーク方式変更
  - localhost限定の安全な中継
- [ ] 採用経路がreadsbをインターネットへ公開しないことを確認する。

### F-4. 結合テスト

- [ ] 空DBから全サービスを起動する。
- [ ] migrationが一度だけ成功する。
- [ ] fixtureサーバーからcollectorが取得する。
- [ ] DBへデータが保存される。
- [ ] 全APIがデータを返す。
- [ ] Web UIが表示される。
- [ ] Compose再起動後もデータが残る。

### F-5. 障害試験

本番readsbではなくモックとテストDBで行う。

#### readsb停止

- [ ] collectorがクラッシュループしない。
- [ ] バックオフする。
- [ ] ready/status/UIがstaleを示す。
- [ ] 復旧後に自動回復する。

#### DB停止

- [ ] collector/APIが秘密情報のないエラーを出す。
- [ ] メモリが無制限に増えない。
- [ ] readinessが503になる。
- [ ] DB復旧後に再接続する。

#### 不正JSON

- [ ] JSON構文エラー
- [ ] `aircraft`欠損
- [ ] 巨大レスポンス
- [ ] 部分的な型不正
- [ ] 不正座標
- [ ] `alt_baro: "ground"`

#### 地図障害

- [ ] style URL失敗
- [ ] tile失敗
- [ ] 地図以外の機能が継続する。

### Milestone F 完了条件

- [ ] Composeだけで空環境から再現できる。
- [ ] 正常、停止、復旧シナリオが自動または再現可能な手順で確認済み。
- [ ] readsbへの接続経路が安全。
- [ ] DBとreadsbを外部公開していない。

---

## 10. Milestone G：Linuxサーバー配置

### G-1. 配置前

- [ ] Phase 0レポートを再確認する。
- [ ] サーバー上のGit差分と配置済みファイルを確認する。
- [ ] 使用予定ポートが空いていることを再確認する。
- [ ] ディスク空き容量を再確認する。
- [ ] 既存3サービスの状態を記録する。
- [ ] rollback手順を準備する。
- [ ] 本番`.env`をサーバー上だけに作る。
- [ ] 受信地点をログや公開画面で精密表示しない設定にする。

### G-2. 配置

- [ ] x86-64用イメージをサーバーでビルドまたは取得する。
- [ ] DBとmigrationを起動する。
- [ ] migration成功を確認する。
- [ ] collectorを起動する。
- [ ] 実readsbから取得できることを確認する。
- [ ] APIを起動する。
- [ ] localhostからhealth/API/UIを確認する。
- [ ] 既存readsb、tar1090、fr24feedが継続稼働していることを確認する。

### G-3. 公開範囲

初期はlocalhostまたはLAN内を既定とする。

- [ ] 希望する公開範囲を確認する。
- [ ] LAN公開ならLANインターフェースとファイアウォールを確認する。
- [ ] インターネット公開ならリバースプロキシを使用する。
- [ ] インターネット公開ならTLSを必須にする。
- [ ] 必要に応じて認証を追加する。
- [ ] PostgreSQLを公開しない。
- [ ] readsb JSONの直接公開を増やさない。
- [ ] 精密な受信地点や管理情報を公開しない。

### G-4. 再起動試験

既存サービスへの影響を避けるため、最初はアプリのCompose再起動だけを行う。

- [ ] アプリCompose再起動後に自動復旧する。
- [ ] DBデータが残る。
- [ ] collectorが重複起動しない。
- [ ] 既存サービスが継続稼働する。

OS再起動試験はユーザーの明示的な許可と実施時間帯を確認してから行う。

- [ ] OS再起動の許可を得る。
- [ ] 再起動後にDockerが起動する。
- [ ] アプリが自動復旧する。
- [ ] readsb、tar1090、fr24feedも正常復旧する。

### G-5. 24時間soak test

- [ ] 24時間連続稼働する。
- [ ] コンテナ再起動回数を確認する。
- [ ] メモリ推移を確認する。
- [ ] CPU負荷を確認する。
- [ ] DB増加量を確認する。
- [ ] readsb取得失敗率を確認する。
- [ ] API応答時間を確認する。
- [ ] 地図とグラフに実データが表示される。
- [ ] 最遠・最接近ランキングを確認する。
- [ ] 既存サービスに負荷増大や異常がない。

### Milestone G 完了条件

- [ ] Linux x86-64サーバー上で24時間安定稼働する。
- [ ] 再起動後に復旧する。
- [ ] 既存サービスへ影響しない。
- [ ] ディスク使用量から保持期間が妥当と確認できる。
- [ ] READMEだけで起動、停止、更新、ログ確認、backup、restoreができる。

---

## 11. Phase 1 最終受け入れ条件

- [ ] Linux x86-64サーバー上で稼働している。
- [ ] readsb、tar1090、fr24feedを変更または停止していない。
- [ ] PostgreSQLへ観測・集計・取得状態が保存される。
- [ ] 現在受信中と位置取得中の機体数を表示できる。
- [ ] 24時間交通量グラフを表示できる。
- [ ] 最近の航跡をMapLibreで表示できる。
- [ ] 最遠・最接近ランキングを表示できる。
- [ ] データなし、stale、readsb異常、DB異常を区別できる。
- [ ] 詳細観測の保持期限が機能する。
- [ ] PostgreSQLが外部公開されていない。
- [ ] 地図障害がアプリ全体を停止させない。
- [ ] backupとrestoreをテスト済みである。
- [ ] Compose再起動後に自動復旧する。
- [ ] 許可された場合、OS再起動後にも自動復旧する。
- [ ] 24時間連続稼働試験を完了している。
- [ ] 自動テスト、lint、format checkが通る。
- [ ] READMEが実環境に合っている。

すべて完了した時点で、リリースタグまたは明確なMVP完了コミットを作成する。Gitへのpushや外部公開は、ユーザーが依頼した場合にのみ行う。

---

## 12. 推奨実装順序

1. Milestone A：ベースライン確認
2. Milestone B：PostgreSQL永続化
3. Milestone C：FastAPI
4. Milestone D：MapLibre/ECharts UI
5. Milestone E：保持とbackup
6. Milestone F：Compose統合・障害試験
7. Milestone G：サーバー配置・24時間試験

小さなコミット単位の例：

1. `db: add schema and migrations`
2. `db: implement postgres store`
3. `api: add health and status endpoints`
4. `api: add traffic tracks and rankings`
5. `ui: add dashboard shell and status cards`
6. `ui: add maplibre tracks map`
7. `ui: add traffic charts and rankings`
8. `ops: add retention backup and log limits`
9. `test: add compose recovery scenarios`
10. `deploy: document production setup`

コミットはユーザーの既存運用方針に従い、許可なくpushしない。

---

## 13. Phase 2候補

Phase 1受け入れ完了後、次の順で価値を追加する。

### Phase 2A：期間比較

- 日、週、月の交通量
- 前日、前週同曜日との比較
- 時間帯別ユニーク機体数
- 高度・速度分布
- CSVエクスポート

### Phase 2B：受信局性能

- 方角別最大受信距離
- 方位×距離の極座標チャート
- 高度帯別受信範囲
- メッセージ数・位置取得率の時系列
- アンテナ設定変更前後の比較

### Phase 2C：ヒートマップ

- MapLibre上の航跡密度
- 高度帯別ヒートマップ
- 曜日・時間帯フィルター
- 大量点をブラウザーへ直接返さないサーバー集計

### Phase 2D：機体の再訪履歴

- 機体ごとの初観測・最終観測
- 観測日数と通過回数
- callsign履歴
- よく見る機体ランキング
- お気に入り機体

### Phase 2E：今日の空

- 日次サマリー
- 最遠・最接近・最多観測
- 交通量の前日/前週比較
- 日報画面
- 明示的に希望された場合のみ外部通知

### Phase 2F：地図セルフホスト

- Protomaps/PMTilesの地域抽出
- MapLibre styleのセルフホスト
- 外部タイル障害への依存削減
- 地図閲覧情報を第三者へ送らない構成
- 地図データ更新手順

Phase 2では、PostGISやTimescaleDBの導入を機能要件と実測性能から再評価する。導入自体を目的にしない。

---

## 14. 作業再開時に必要な情報

実装を続けるエージェントは、まずリポジトリから取得できる情報を確認する。次の項目だけは、未決定ならユーザーへ確認する。

### Phase 1実装中に必要

1. 実際のプロジェクトディレクトリまたはリポジトリ
2. PostgreSQLの本番パスワードをサーバー上でどう管理するか
3. MapLibreの地図スタイル選択
   - 公開無料スタイル
   - MapTiler等のAPIキースタイル
   - 後でセルフホスト
4. 初期公開範囲
   - localhost
   - LAN
   - インターネット

### 配置時までに必要

5. 本番APIポート
6. インターネット公開の場合のドメイン
7. TLSと認証の方針
8. OS再起動試験を実施してよい時間帯
9. backup保存先と保持世代数

未決定の非危険項目には以下の既定値を使用して作業を進められる。

```text
DISPLAY_TIMEZONE=Asia/Tokyo
POLL_INTERVAL_SECONDS=5
TRACK_SAMPLE_SECONDS=30
RAW_RETENTION_DAYS=30
APP_BIND_HOST=127.0.0.1
APP_PORT=8088
地図テーマ=dark
公開範囲=localhost
backup保持=7世代
```

---

## 15. 進捗記録

各作業セッションの終了時に以下を追記する。

```text
日付:
完了したMilestone/Task:
変更した主要ファイル:
実行したテスト:
テスト結果:
実環境で確認したこと:
残課題:
次に行うTask:
ユーザー判断が必要な事項:
```

最初の再開セッションでは、Milestone Aを完了し、Milestone BのmigrationとPostgresStoreから着手する。
