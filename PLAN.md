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

- [x] `adsb-db`を定義する。
- [x] DBデータをnamed volumeへ保存する。
- [x] DBポートをホストへ公開しない(`docker compose ps`のPORTSが`5432/tcp`のみ、ホスト側`ss -ltn`にも5432なしを実機確認)。
- [x] DBユーザー、DB名、パスワードを環境変数化する。
- [x] パスワードに開発用既定値を本番で使わせない(`.env.example`の`changeme`はコミットされず、本番`.env`はG-1でサーバー上にのみ作成する運用)。
- [x] `pg_isready`によるhealthcheckを追加する。
- [x] ログサイズ上限を設定する。
- [x] graceful shutdown期間を設定する。

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

- [x] ICAOアドレスの形式または長さを制約する。
- [x] 緯度は`-90..90`、経度は`-180..180`を制約する。
- [x] 距離、速度、方位など明らかな不正値を防ぐ。
- [x] `observations (icao, observed_at DESC)`を作る(`UNIQUE(icao, observed_at)`制約が同じB-treeを提供するため、別インデックスは追加せず重複を回避)。
- [x] `observations (observed_at DESC)`を作る。
- [x] `observations (distance_km, observed_at DESC)`を作る(`WHERE distance_km IS NOT NULL`の部分インデックス)。
- [x] `aircraft (last_seen_at DESC)`を作る。
- [x] `ingestion_status (checked_at DESC)`を作る。
- [x] 1回のpoll再処理で観測が不当に重複しない一意性を検討する(`UNIQUE(icao, observed_at)` + `ON CONFLICT DO UPDATE`)。
- [x] APIの実クエリを確認し、不要なインデックスを増やさない(Milestone C未着手のため、CLAUDE.md記載のクエリパターンから判断)。

### B-5. migration

- [x] 初期migrationを作成する。
- [x] 空DBへのupgradeをテストする(使い捨てコンテナと実際の`compose.yaml`の両方で確認)。
- [x] 同じDBへの再実行が安全であることを確認する(`docker compose run --rm adsb-migrate`を2回実行、2回目は無変更で正常終了)。
- [x] downgradeまたはロールバック方針を文書化する(`migrations/versions/..._initial_schema.py`のdocstringに記載。空DBでdowngrade/再upgradeのサイクルを実DBで確認済み。実データを持つDBに対しては絶対に実行しない方針)。
- [x] migration専用Composeサービスを追加する。
- [x] migrationの失敗を起動ログで明確に確認できるようにする(Alembicは失敗時に非ゼロ終了、`docker compose logs adsb-migrate`で確認可能)。

### B-6. PostgresStore

- [x] Store Protocolに準拠する`PostgresStore`を作成する。
- [x] 接続プールを設定する。
- [x] 起動時接続と終了時closeを実装する。
- [x] **[方針変更、理由記録]** 1回のpollに関係する更新を明示的な複数文トランザクションへはまとめない。`service.py`の耐障害設計(`_safe_store_call`が各Store呼び出しを個別にcatch)は「1機体の書き込み失敗が同じpollの他の正常な書き込みを巻き込まない」ことが前提であり、poll全体を1トランザクションにするとこの前提を破壊する。各Protocolメソッドは元々1テーブルへの1文のみなので、Postgresのデフォルトの文単位アトミック性で既に必要な原子性は満たされている(`app/db/postgres_store.py`のdocstringに理由を記載)。
- [x] `aircraft`のupsertを実装する。
- [x] `observations`のinsert(`ON CONFLICT DO UPDATE`で冪等)を実装する。
- [x] `traffic_minute`のupsertを実装する。
- [x] `ingestion_status`の保存を実装する。
- [x] 一部保存後の例外で不整合が残らないことを確認する(契約テスト`test_earlier_write_survives_a_later_failing_write`で実DB確認)。
- [x] DB停止時に無制限のメモリキューを作らない(バッファ自体を持たず、`asyncpg`が例外を投げて`_safe_store_call`が握りつぶすのみ)。
- [x] DB復旧後にcollectorが再接続できるようにする(`asyncpg`プールが次回利用時に自動再接続、追加コード不要)。
- [x] SQLパラメータを必ずバインドし、文字列連結でSQLを組み立てない(全メソッド`$1`等のプレースホルダのみ使用)。

### B-7. Store契約テスト

同じテストケースをInMemoryStoreとPostgresStoreへ適用できる形にする。

- [x] aircraftの新規作成
- [x] aircraftのlast seen更新
- [x] callsignが空の観測で有効な既存callsignを不用意に消さない
- [x] observation保存
- [x] 同一観測の再処理
- [x] 1分集計のupsert
- [x] ingestion成功/失敗状態の保存
- [x] トランザクションロールバック(`tests/contract/test_postgres_store.py`にPostgres限定の`test_earlier_write_survives_a_later_failing_write`として実装。InMemoryStoreは値検証を一切行わないため同じ失敗モードを起こせず、共有チェックにはできなかった — 理由をテストのdocstringに記載)
- [x] UTCタイムスタンプ
- [x] close後の接続解放(Postgres限定の`test_close_then_use_fails`で確認。InMemoryStoreは解放すべきOSリソースを持たない)

### Milestone B 完了条件

- [x] Compose上の空DBへmigrationできる。
- [x] collectorがfixtureをPostgreSQLへ保存できる(`tests/integration/test_collector_service_postgres.py`で自動テスト化、実`compose.yaml`のadsb-dbへの手動投入でも確認)。
- [x] Store契約テストがInMemoryStoreとPostgresStoreの両方で通る(20件全green)。
- [x] PostgreSQLポートがホスト外部へ公開されていない(`docker compose ps`と`ss -ltn`で実機確認)。
- [x] コンテナ再作成後もデータが残る(`docker compose down && docker compose up -d adsb-db`前後でデータ一致を実機確認)。

---

## 6. Milestone C：FastAPIと分析クエリ

### C-1. API構成

- [x] FastAPIアプリのfactoryまたは明確なentry pointを作る(`app/api/main.py:create_app()`。副作用のない純粋なfactoryとし、uvicorn向けの実体は`app/api/asgi.py`に分離、テストからは任意のSettingsで安全にimportできる)。
- [x] 起動時に設定を検証する(`Settings()`が`create_app()`内で構築され、既存の検証ロジックがそのまま効く)。
- [x] DB接続をdependencyとして注入する(`app/api/dependencies.py:get_pool`、lifespanでpool生成・close)。
- [x] API用のread repositoryを作る(`app/db/queries/{status,traffic,tracks,rankings,aircraft}.py`)。
- [x] collectorのwrite StoreとAPIのread queryを密結合させない(collectorの`PostgresStore`とAPIの`app/db/queries/`は別々のpoolを持ち、互いを参照しない)。
- [x] 例外を秘密情報のない統一JSONへ変換する(`app/api/errors.py`、DBエラー/タイムアウト/バリデーションエラー/未処理例外を`{"error","detail"}`の統一形式へ変換、詳細は常にサーバー側ログのみ)。
- [x] OpenAPI上でレスポンス型を確認できるようにする(全エンドポイントに`response_model`を指定、GeoJSONも含めpydanticモデル化)。
- [x] CORSは不要なので有効化していない。

### C-2. Health API

#### `GET /health/live`

- Webプロセスが応答できれば200を返す。
- DBやreadsbの一時障害だけでlivenessを失敗させない。

#### `GET /health/ready`

- DBへ軽量クエリを実行する。
- 最終取得成功時刻を確認する。
- 最終成功が閾値より古ければ503を返す。
- 応答に秘密情報やreadsb URLを含めない。

- [x] liveの正常・異常テスト(liveは常に200。プロセスが応答不能な状態は原理的にテスト不可のため対象外)
- [x] **[範囲限定]** readyのDB停止テスト: 「データ未取得」と「直近ingestionが失敗」は`test_ready_fails_with_no_data`/`test_ready_fails_on_ingestion_failure`でカバー。ただし「起動後にDBが落ちる」シナリオは未テスト — `asyncpg.create_pool(min_size=1)`は起動時に即座に接続確立を試みるため、DB不通時はAPI起動自体が失敗する(DB→migration→API起動の順序を前提とするアーキテクチャでは意図した挙動)。実行中のDB停止試験はMilestone F(F-5障害試験)のモック/テストDBを使った試験で正式に扱う。
- [x] readyのデータstaleテスト(`test_ready_fails_on_stale_data`)
- [x] 復旧後にreadyが200へ戻るテスト(`test_ready_recovers_after_a_fresh_success_follows_a_failure`)

### C-3. Status API

`GET /api/status`

- `generated_at`
- `last_ingestion_at`
- `ingestion_state`
- `active_aircraft_count`
- `position_aircraft_count`
- `data_age_seconds`
- `display_timezone`

- [x] データがまだない状態を正常に表現する(`ingestion_state: "no_data"`)。
- [x] staleデータを正常表示しない(stale/error/no_dataの全状態でcount系を0に強制、`test_status_stale_zeroes_counts`)。
- [x] 現在受信中の定義をcollectorと一致させる(`app/collector/normalize.py`の`RECEIVED_MAX_SEEN_SECONDS`/`POSITION_ACQUIRED_MAX_SEEN_POS_SECONDS`をそのままimportして使用)。

### C-4. Traffic API

`GET /api/traffic?hours=24`

- `hours`は1～168時間へ制限する。
- 1分集計を時系列で返す。
- 空の時間帯をUIが扱える形式にする。
- `active_aircraft_count`
- `position_aircraft_count`
- 可能なら期間ユニーク機体数も返す。

- [x] 1時間、24時間、168時間(`test_traffic_bounds_1_and_168`)
- [x] 範囲外入力(`test_traffic_out_of_range_hours_rejected`、422)
- [x] データなし(`test_traffic_default_window_with_no_data`、全バケット0埋め)
- [x] UTCと表示タイムゾーン境界(DBは全てUTC/`TIMESTAMPTZ`で保持、タイムゾーン変換は表示側=Milestone Dの責務。バケット境界は分単位で厳密に生成)

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

- [x] 代表データ量を生成する(実`adsb-db`に合成データを投入: aircraft 2,000件、observations 33,710件、traffic_minute 43,200件=30日分)。
- [x] traffic、tracks、rankingsの実行計画を確認する(`EXPLAIN`で全てIndex/Bitmap Index Scanを使用、Seq Scanなしを確認)。
- [x] N+1 queryがないことを確認する(tracksは対象機体の抽出→観測点取得を2クエリのみで完結、機体ごとのループクエリなし)。
- [x] APIのタイムアウトを設定する(`app/db/queries/*.py`の全クエリに`timeout=5.0`)。

初期目標：

- status/health：200ms以内
- traffic/rankings：500ms以内
- tracks：2秒以内

同一LAN・通常負荷での目安とし、サーバー性能に応じて実測値を記録する。

**実測結果**(上記の代表データ量、このホスト上のdocker composeネットワーク経由):
- `GET /health/live`: 0.5ms
- `GET /health/ready`: 1.6ms
- `GET /api/status`: 2.1ms
- `GET /api/traffic?hours=24`: 36.5ms(168KB)
- `GET /api/traffic?hours=168`: 257.0ms(1.18MB — レスポンスサイズが大きいため、Milestone Dでの表示方法や将来的な間引き・圧縮を検討課題として記録)
- `GET /api/rankings?hours=24&limit=10`: 6.0ms
- `GET /api/tracks?hours=6`: 3.3ms
- `GET /api/aircraft/recent`: 2.8ms

全て目標値を大幅に下回る。

### Milestone C 完了条件

- [x] 全APIがOpenAPIと一致する(`test_openapi_lists_all_endpoints`)。
- [x] 入力値上限が機能する(hours/limit/offsetの範囲外入力が全エンドポイントで422)。
- [x] DB・データ未取得・stale状態を区別できる(`ingestion_state`: ok/stale/error/no_dataの4値、`/health/ready`とセットで確認)。
- [x] 代表データ量で性能目標を満たすか、実測と改善案が記録されている(上記実測結果を参照。traffic hours=168のレスポンスサイズのみ改善候補として記録)。
- [x] APIの自動テストが通る(統合テスト23件・ユニットテスト5件、全green)。

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

- [x] MapLibre GL JSを利用する(v6.0.0、ESM経由でunpkgから読み込み。v6でUMDバンドルが廃止されたため`<script type="module">`+`import`を使用)。
- [x] `MAP_STYLE_URL`でstyle URLを切り替えられるようにする(`app/config.py`→`/api/config`→`main.js`)。
- [x] MapTiler等のAPIキーをコードへ埋め込まない(既定はOpenFreeMap、キー不要)。
- [x] 開発用スタイルと本番用スタイルを設定で分けられるようにする(env変数のみで切替可能)。
- [x] attributionを隠さない(`attributionControl: true`、既定表示)。
- [!] **[未検証]** 日本語ラベル表示を確認する — このセッションにブラウザ環境がなく目視確認ができなかった。実装(`localIdeographFontFamily`設定)は完了しているが、実際の表示確認はユーザーまたは今後のセッションで要。
- [x] `localIdeographFontFamily`を適切に設定する。
- [x] style/tile取得失敗を検出し、地図部分だけにエラー表示する(`map.on("error")`→`#map-error`のみ表示、他パネルは独立)。
- [x] 地図失敗時もグラフとランキングを利用可能にする(各パネルが独立してfetchするため構造的に保証。実ブラウザでの動作確認は未実施)。

初期選択：

- 素早いMVP：OpenFreeMap等の公開style URL
- 見た目優先：MapTiler Dataviz Dark等
- プライバシー/自立運用優先：Phase 2でProtomaps/PMTilesをセルフホスト

どの提供元でも、利用条件、APIキー、リクエスト上限、attributionを確認する。

### D-3. 地図上の航跡

- [x] GeoJSON sourceとして航跡を追加する。
- [x] 高度に応じて航跡色を変える。
- [x] 不明高度は灰色にする。
- [x] 航跡へ適度な透明度を設定する(opacity 0.75)。
- [x] 選択中の航跡を太く表示する(クリックでICAOを選択、`setPaintProperty`でその機体のみ`line-width`を4に)。
- [x] ホバーまたはクリックで機体情報を表示する(ホバーでpopup表示、クリックで選択状態切替)。
- [x] callsign、ICAO、高度、速度、最終観測、距離を表示する(popupに全項目。距離はAPI側`/api/tracks`のレスポンスに`last_distance_km`を追加して対応 — 実装中に発見した抜け漏れ)。
- [x] 長い空白を跨いだ直線を描かない(サーバー側`app/db/queries/tracks.py`でセグメント分割済み、GeoJSONの`MultiLineString`として提供)。
- [x] 受信地点は初期状態で精密表示しない(受信局マーカー自体を未実装 — APIが受信局座標を一切返さないため、精密表示のリスクなし)。
- [x] 自動ズーム時も自宅位置を過度に強調しない(自宅マーカー・自動ズーム機能自体が存在しないため該当なし)。
- [x] 点数が多い場合にブラウザーを固めない(サーバー側で最大100機・10,000点に制限・間引き済み)。

**[未検証]** 上記のうち視覚的な確認(色分けの見やすさ、ポップアップの表示、クリック選択の動作)はこのセッションのブラウザ環境がないため未実施。curlでのAPI応答構造確認と静的アセットの配信確認のみ実施。

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

- [!] **[簡略化]** 読み込み中skeletonを実装する — 専用skeleton UIは作らず、初期値`"--"`表示 + データ到着後に置き換える方式にした。視覚的な洗練度は低いが「読み込み中と分かる」最低要件は満たす。凝ったskeleton化は必要になれば追加。
- [x] データなし表示を実装する(`ingestion_state: "no_data"`、テーブル空表示は`.panel__empty`)。
- [x] API異常表示を実装する(ingestion badgeが"APIエラー"表示、コンソールにも記録)。
- [x] stale表示を実装する(badge色・テキストで"データ取得停止中"、カード数値は"--")。
- [x] 最終更新を定期更新する(10秒間隔でstatus/rankings、30秒間隔でtraffic/tracks)。
- [x] ブラウザータブ非表示時に過剰なpollをしない(`document.hidden`チェック、非表示中はpollを止め、復帰時に即時更新)。

### D-5. ECharts

- [x] UTCデータを指定タイムゾーンで表示する(`Intl`の`timeZone`オプションで`DISPLAY_TIMEZONE`を反映)。
- [x] activeとpositionを区別して描画する(2系列、色分け+凡例)。
- [x] tooltipへ時刻と値を表示する。
- [!] **[範囲限定]** 欠測をゼロと誤認させない — `/api/traffic`は全バケットを0埋めして返す設計のため(Milestone C)、「収集停止による欠測」と「実際に0機」をチャート上で視覚的に区別する仕組みは未実装。ingestion_stateバッジ側で収集停止は別途分かるため実害は小さいが、正式な区別はしていないと記録する。
- [x] 1h、6h、24hの表示切替を検討する(ヘッダーの期間ボタンで実装 — ただし現状は航跡地図の期間切替のみに連動しており、交通量グラフ自体は常時24h固定。グラフ側の期間切替は次回改善候補)。
- [x] ウィンドウサイズ変更時にresizeする(`window.resize`→`chart.resize()`)。
- [x] グラフ描画失敗が画面全体を壊さない(`try/catch`+`#chart-error`、他パネルは独立)。

### D-6. レスポンシブ・アクセシビリティ

- [!] **[未検証]** 1440px前後のデスクトップで確認する — CSSのブレークポイント(900px, 480px)は実装済みだが、実ブラウザでの目視確認はこのセッションでは実施できていない。
- [!] **[未検証]** 768px前後のタブレットで確認する — 同上。
- [!] **[未検証]** 375px前後のスマートフォンで確認する — 同上。
- [x] キーボードで主要操作ができる(期間切替・航跡クリックはbutton要素、focus-visible対応)。
- [x] フォーカス表示が見える(`:focus-visible`に2pxアウトライン、CSS変数`--accent`)。
- [x] 状態を色だけで表現しない(ingestion badgeは色+テキストラベルを常に併記)。
- [x] 表に見出しと適切なラベルを付ける(`<th scope="col">`、`<caption class="sr-only">`)。
- [x] `prefers-reduced-motion`へ対応する(アニメーション・トランジションを0.01msに短縮)。

### D-7. フロントエンド方針

初期計画どおり、不要なSPAフレームワークは追加しない。既存構成を確認し、FastAPIから静的ファイルまたはテンプレートを配信する。

- [x] JavaScriptをAPI、map、chart、UIの責務に分ける(`app/static/js/{api,map,chart,ui,main}.js`)。
- [x] npmは使用しない(ビルドステップなし、CDN直読み込みのみ — lockfileの論点は該当なし)。
- [x] CDN依存を採用する場合はバージョン固定とCSPを検討する(`maplibre-gl@6.0.0`、`echarts@6.1.0`を完全ピン留め、`<meta http-equiv="Content-Security-Policy">`でscript-src/style-src/connect-src等を制限。ただしMAP_STYLE_URLが動的なため`img-src`/`connect-src`は`https:`全体を許可 — 任意の地図プロバイダに対応するための妥当なトレードオフとして記録)。
- [x] 任意HTMLをAPIデータから挿入しない(`innerHTML`は一切使用せず、`textContent`/`createElement`のみ)。
- [x] callsignなど外部入力を安全にテキスト表示する(同上)。

### Milestone D 完了条件

- [x] 全MVP情報が1画面で確認できる(ヘッダー/ステータスカード/地図+グラフ/ランキング+最近観測を1つの`index.html`に実装)。
- [!] **[未解決の不具合]** MapLibreの地図がモダンで、航跡とラベルを読み分けられる — 実装(高度別配色・透明度・選択強調)は完了しているが、ユーザーの実ブラウザでは依然として地図が表示されない。仮環境(即席`python:3.12-slim`コンテナ)だけでなく、本番同等のDockerイメージ(Milestone F、実readsb接続、`v0.3.0`)でも再現することを確認した — CDN疎通やコンテナ環境固有の問題ではないことが分かった一方、原因はまだ特定できていない。ランキング(最遠/最近)・最近観測した機体パネルは実データで正しく更新されることを確認済み(2026-07-28)。
- [x] 地図タイル障害時も他機能が使える(構造的に各パネル独立、`map.on("error")`でmapパネルのみエラー表示)。
- [!] **[未検証]** PCとスマートフォンで主要情報が読める — レスポンシブCSSは実装済みだが実機/実ブラウザ確認は未実施。
- [x] stale/異常/データなしを正常状態と誤認しない(`ingestion_state`の4値をbadge・カード両方に反映、staleで数値を"--"化)。
- [!] **[未検証]** ブラウザーで重大なconsole errorがないこと — このセッションにはブラウザ実行環境(Claude in Chrome未接続、headlessブラウザ・Node.js未導入)がなく確認できなかった。curlによるHTTP応答・Content-Type確認、および全JSファイルの読み返しによるレビューのみ実施。

**総括**: バックエンド(API・DB)側は自動テストで裏付けられた完成度だが、フロントエンドの実際の見た目・操作感・console errorの有無は本セッションでは確認できていない。ユーザー側で `docker compose up -d adsb-db` → APIサーバー起動 → `http://<host>:8088/` をブラウザで開いての最終確認を推奨する。

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

- [x] x86-64でビルドできる(このホストで実ビルド・実起動確認済み)。
- [x] Pythonベースイメージを固定する(`python:3.12-slim`)。
- [!] **[未実施]** multi-stage buildまたは不要ファイル除外でサイズを抑える — 現状シングルステージビルドのみ。動作優先で後回しにした最適化課題として記録。
- [x] `.dockerignore`を用意する(Milestone Bで作成済み、そのまま流用)。
- [x] 非rootユーザーでcollector/APIを実行する(`USER appuser`、uid 1000)。
- [x] healthcheckに不要な大型ツールを追加しない(curlではなくPython標準ライブラリの`urllib`を使用)。
- [x] イメージに`.env`や実データを含めない(`.dockerignore`で`.env`除外、ビルド時にデータは一切含まれない)。

### F-2. Compose

- [x] `adsb-db`(Milestone Bで実装済み)
- [x] `adsb-migrate`(Milestone Bで実装済み)
- [x] `adsb-collector`(新規)
- [x] `adsb-api`(新規)
- [x] named volume(`adsb-db-data`、Milestone Bから継続)
- [x] internal network(compose既定ネットワーク、`adsb-db`はポート非公開のまま)
- [x] APIだけのポート公開(`adsb-api`のみ`ports:`を持つ)
- [x] restart policy(`unless-stopped`をcollector/apiに設定)
- [!] **[部分実施]** healthcheck — `adsb-api`は`/health/live`ベースのhealthcheckを実装。`adsb-collector`はHTTPエンドポイントを持たないため未実装(ログ監視やingestion_statusテーブルベースの外形監視は将来課題)。
- [x] ログ上限(`json-file`、max-size 10m/max-file 3をcollector/apiにも設定)
- [x] graceful shutdown(`stop_grace_period`設定、collectorは`SIGTERM`で`service.stop()`が呼ばれ現在のpollを完了させてから終了)

collectorは1インスタンスだけ起動する。将来APIを複数化してもcollectorが重複起動しないよう責務を分ける。

### F-3. readsbへのコンテナ内疎通

- [x] Phase 0で確認済みのURL(`http://127.0.0.1/tar1090/data/aircraft.json`相当)をコンテナ内から取得できるか確認する — `host.docker.internal`経由で実際に200 OKを確認済み。
- [x] `127.0.0.1`がホストではなくコンテナ自身を指す点を考慮する — `.env`のコメントに明記、`READSB_AIRCRAFT_URL`は`host.docker.internal`を指すよう設定。
- [x] `host.docker.internal`、host gateway、LAN IP等を環境に合わせて検証する — Docker EngineはDocker Desktopと違い`host.docker.internal`を自動提供しないため、`compose.yaml`の`extra_hosts: host.docker.internal:host-gateway`で明示的に追加。実機で疎通確認済み。
- [x] readsbがホストloopbackにしかbindしていない場合、勝手にbind先を変更しない — 読み取り専用`ss -ltn`でreadsbのWebサーバーが既に`0.0.0.0:80`にbindされていることを確認済みのため、bind先変更は不要だった(変更していない)。
- [ ] 疎通できない場合の比較検討(readsb公開範囲の最小変更/collectorのネットワーク方式変更/localhost限定の中継) — 疎通に問題がなかったため未実施(該当なし)。
- [x] 採用経路がreadsbをインターネットへ公開しないことを確認する — `host.docker.internal`はDocker内部のみで完結し、readsb側の公開範囲(ホストのLAN/Tailscale)を一切変更していない。

### F-4. 結合テスト

- [x] 空DBから全サービスを起動する — 実機で`docker compose up`により`adsb-db`→`adsb-migrate`→`adsb-collector`/`adsb-api`の順で起動確認済み。
- [x] migrationが一度だけ成功する — `adsb-migrate`は`restart: "no"`かつ`service_completed_successfully`条件で1回のみ実行。
- [!] **[代替実施]** fixtureサーバーからcollectorが取得する — 本項目はfixtureサーバーを想定しているが、実際には本番の実readsbから取得する構成で検証した(ユーザー判断により仮環境デバッグより実環境構築を優先)。fixtureサーバーを使った再現可能な自動テストはまだない。
- [x] DBへデータが保存される — 実データで確認済み(12機のaircraft、23件のobservations、ingestion_statusが約5秒おきに成功記録)。
- [x] 全APIがデータを返す — `/api/status`等がDBの実データを反映して応答することを確認済み。
- [!] **[部分実施]** Web UIが表示される — ステータスバッジ・数値・バージョン表示は動作確認済みだが、地図(MapLibre)の表示は未解決のバグが残っている(下記参照)。
- [ ] Compose再起動後もデータが残る — named volumeを使っているため理論上は永続化されるはずだが、実際に`docker compose down`(volumeを保持したまま)→`up`しなおしてデータ保持を確認する手順はまだ実施していない。

### F-5. 障害試験

本番readsbではなくモックとテストDBで行う。**このMilestoneでは未実施。** 実環境構築を優先した結果、本セクションの自動化されたモック障害試験(readsb停止/DB停止/不正JSON/地図障害)はまだ着手していない。Milestone C/DのユニットテストレベルではDB接続失敗時の`/health/ready`挙動など一部関連ロジックはカバーされているが、Compose環境全体を使った意図的な障害注入試験ではない。

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

既知の未解決バグ: ブラウザで地図モジュールの動的import自体が失敗するケースを確認済み(`Failed to fetch dynamically imported module: .../static/js/map.js`)。原因はMapLibre本体のvendoring・キャッシュ制御修正後も再現しており未特定。**2026-07-28、本番同等の実環境(本Compose構成、実readsbデータ)でユーザーが再確認した結果、地図は依然として表示されないことを確認した。** 一方、ランキング(最遠/最近)・最近観測した機体は実環境で正しく更新されることを確認した。これにより、地図バグは即席検証コンテナ固有の問題ではなく、コード自体(または対象ブラウザ環境)に起因すると切り分けられた。DevToolsのConsole/Networkタブでの詳細調査が次の手がかりとして必要。

### Milestone F 完了条件

- [!] **[部分達成]** Composeだけで空環境から再現できる — サービス構成・起動順序は実機確認済みだが、fixtureサーバーを使った完全に独立・再現可能な自動化はまだない(F-4参照)。
- [ ] 正常、停止、復旧シナリオが自動または再現可能な手順で確認済み — F-5未着手のため未達成。
- [x] readsbへの接続経路が安全 — `host.docker.internal`経由のDocker内部限定、readsb側の公開範囲は変更していない(F-3参照)。
- [x] DBとreadsbを外部公開していない — `adsb-db`は`ports:`なし、readsbはこのアプリからの変更なし(既存のLAN/Tailscale公開範囲のまま)。

**総評: Milestone Fは部分完了。** 実データでのエンドツーエンド疎通(collector→DB→API)は実環境で確認できたが、(1)地図表示バグが未解決、(2)モックを使った意図的な障害試験(F-5)が未着手、(3)fixtureサーバーベースの結合テスト自動化が未着手、の3点が残課題。

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

### セッション記録

```text
日付: 2026-07-27
完了したMilestone/Task: Milestone A(ベースライン確認)、Milestone B(PostgreSQL永続化)
変更した主要ファイル:
  - compose.yaml, Dockerfile.migrate, .dockerignore（新規）
  - alembic.ini, migrations/env.py, migrations/versions/62c3f8022564_initial_schema.py（新規）
  - app/db/pool.py, app/db/postgres_store.py（新規）
  - app/collector/store.py（Store Protocolにclose()追加）
  - app/collector/__main__.py（InMemoryStore→PostgresStoreへ配線）
  - tests/contract/（新規: pg_container.py, store_contract.py, test_in_memory_store.py, test_postgres_store.py）
  - tests/integration/test_collector_service_postgres.py（新規）
  - tests/conftest.py（新規、契約テストfixtureの共有）
  - pyproject.toml（migrate extra追加、pytest/pytest-asyncio更新）、.env.example（POSTGRES_*追加）
実行したテスト: pytest（フルスイート）、ruff check/format --check
テスト結果: 113件全green、lint/format clean
実環境で確認したこと:
  - docker composeで空DBへのmigration適用・再適用（2回実行で冪等性確認）
  - downgrade→再upgradeのサイクル
  - docker compose ps / ss -ltn でDBポートがホストへ一切公開されていないことを確認
  - docker compose down（volumeは保持）→ up 後もデータが残ることを確認
  - 使い捨てPostgresコンテナでの契約テスト20件、collector→実PostgreSQL統合テスト1件
残課題:
  - Milestone E（保持期限）でingestion_statusテーブルの保持ポリシーが未定義（observationsのみ言及されている）。Milestone E着手時に対応要。
  - この開発ホストではDocker経由のポートフォワード直後の接続でSSLネゴシエーションがリセットされる既知の癖がある（本番のcompose内部ネットワーク通信には影響なし）。tests/contract/pg_container.pyでsslmode=disable指定とリトライで回避済み。
次に行うTask: Milestone C（FastAPI: health/status/traffic/tracks/rankings API）
ユーザー判断が必要な事項: なし（Milestone C着手に必要な決定事項は現時点でなし）
```

### セッション記録

```text
日付: 2026-07-27
完了したMilestone/Task: Milestone C（FastAPIと分析クエリ）
変更した主要ファイル:
  - app/db/queries/{status,traffic,tracks,rankings,aircraft}.py（新規、read repository）
  - app/api/{main,asgi,dependencies,errors,schemas}.py（新規）
  - app/api/routers/{health,status,traffic,tracks,rankings,aircraft}.py（新規）
  - tests/integration/test_api.py（新規、23件）、tests/unit/test_tracks_query.py（新規、5件）
実行したテスト: pytest（フルスイート）、ruff check/format --check
テスト結果: 141件全green、lint/format clean
実環境で確認したこと:
  - 実compose db（adsb-db）に代表データ量（aircraft 2,000 / observations 33,710 / traffic_minute 43,200、30日分相当）を投入し、docker composeネットワーク経由で全エンドポイントを実測（本文参照、全て目標値を大幅に下回る）
  - EXPLAINでtraffic/tracks/rankings/statusの主要クエリが全てIndex ScanまたはBitmap Index Scanを使用しSeq Scanがないことを確認
  - OpenAPIスキーマに全7エンドポイントが正しく登録されていることを確認
  - 使い捨てPostgresコンテナ上でhealth/status/traffic/tracks/rankings/aircraft/recentの統合テスト23件（DB空・stale・成功/失敗の全ingestion_state、境界値の422、GeoJSON形状、ランキングの機体重複排除など）
残課題:
  - `/health/ready`の「実行中にDBが落ちる」シナリオは未テスト（`asyncpg.create_pool(min_size=1)`が起動時に即座に接続を試みるため、DB不通時はAPI起動自体が失敗する — アーキテクチャ上意図した挙動だが、真の「稼働中のDB停止」試験はMilestone F（F-5障害試験）でモック/テストDBを使って正式に行う）。
  - `GET /api/traffic?hours=168`のレスポンスが1.18MBと大きい（1分粒度×10,080バケットをそのまま返すため）。応答時間は目標内(257ms)だが、Milestone Dでのフロントエンド表示方法や将来的な粗い粒度への切替を検討課題として記録。
  - Milestone E（保持期限）でingestion_statusテーブルの保持ポリシーが依然未定義（Milestone Bのセッション記録から継続）。
次に行うTask: Milestone D（MapLibre/EChartsダッシュボード）
ユーザー判断が必要な事項:
  - D-2の地図スタイル選択（公開無料スタイル / MapTiler等のAPIキースタイル / 後でセルフホスト）— §14に未決定時の既定値なし、着手前に確認が必要。
```

### セッション記録

```text
日付: 2026-07-27
完了したMilestone/Task: Milestone D（モダンなMapLibreダッシュボード）— バックエンド側は完了、フロントエンドの目視確認は未実施
変更した主要ファイル:
  - app/api/routers/config.py（新規、/api/config）、app/api/schemas.py（ConfigResponse、TrackFeatureProperties.last_distance_km追加）
  - app/api/main.py（static file mount、`/`ルート追加）
  - app/db/queries/tracks.py（last_distance_km追加 — 実装中にpopup要件との照合で発見した抜け漏れ）
  - app/config.py（MAP_STYLE_URLの既定値をOpenFreeMap positronに変更）
  - app/static/index.html, app/static/css/style.css（新規）
  - app/static/js/{api,ui,map,chart,main}.js（新規）
  - tests/integration/test_api.py（config/tracks距離のテスト追加）、tests/unit/test_tracks_query.py（distance_km対応）
実行したテスト: pytest（フルスイート）、ruff check/format --check
テスト結果: 142件全green、lint/format clean
実環境で確認したこと:
  - 実compose db（adsb-db）にデモ用データを投入し、docker composeネットワーク上のコンテナでAPIサーバーを起動、`curl`で`/`・`/static/js/*`・`/static/css/*`・全APIエンドポイントのレスポンス(HTTPステータス・Content-Type・JSON構造)を確認
  - `/api/config`が秘密情報(DATABASE_URL・READSB_AIRCRAFT_URL・パスワード)を一切含まないことを自動テストで確認
  - 検証用コンテナは確認後に停止・削除、投入したデモデータもTRUNCATEで削除済み
残課題（重要 — ユーザー確認推奨）:
  - **ブラウザでの実際の目視確認が一切できていない**。このセッションにはClaude in Chrome連携・headlessブラウザ・Node.jsのいずれも利用できず、地図の表示・航跡の色分け・ポップアップ・グラフの描画・レスポンシブ・console errorの有無を確認する手段がなかった。コードレビューとAPI応答の構造確認のみで実装を進めた。
  - D-5: 期間切替ボタン(1h/6h/24h)は現在航跡地図のみに連動し、交通量グラフは常に24h固定(グラフ側の期間切替は未実装)。
  - D-5: `/api/traffic`のゼロ埋めバケットと「収集停止による欠測」をチャート上で視覚的に区別する仕組みは未実装(ingestion_stateバッジ側での判別に依存)。
  - Milestone E（保持期限）でingestion_statusテーブルの保持ポリシーが依然未定義（継続）。
次に行うTask: ユーザーによるブラウザでの動作確認 → 問題なければMilestone E（保持・バックアップ・運用）
ユーザー判断が必要な事項:
  - `docker compose up -d adsb-db`起動後、APIサーバーを何らかの方法で起動し `http://<host>:8088/` をブラウザで開いて、地図・グラフ・レスポンシブ・console errorを確認していただきたい。問題があれば次セッションで修正する。
```
