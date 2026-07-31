# ADS-B Analytics MVP 継続実装計画

- [ADS-B Analytics MVP 継続実装計画](#ads-b-analytics-mvp-継続実装計画)
  - [0. この計画の位置づけ](#0-この計画の位置づけ)
    - [実装済み](#実装済み)
    - [未実装または未完了](#未実装または未完了)
  - [1. Codexエージェント向け最重要ルール](#1-codexエージェント向け最重要ルール)
  - [2. ステータスの記法](#2-ステータスの記法)
  - [3. 完成時の構成](#3-完成時の構成)
  - [4. Milestone A：再開前ベースライン確認](#4-milestone-a再開前ベースライン確認)
    - [A-1. リポジトリ確認](#a-1-リポジトリ確認)
    - [A-2. テスト基準線](#a-2-テスト基準線)
    - [A-3. 設計差分確認](#a-3-設計差分確認)
    - [Milestone A 完了条件](#milestone-a-完了条件)
  - [5. Milestone B：PostgreSQL永続化](#5-milestone-bpostgresql永続化)
    - [B-1. 技術選定](#b-1-技術選定)
    - [B-2. ComposeのDB定義](#b-2-composeのdb定義)
    - [B-3. 初期スキーマ](#b-3-初期スキーマ)
      - [`aircraft`](#aircraft)
      - [`observations`](#observations)
      - [`traffic_minute`](#traffic_minute)
      - [`ingestion_status`](#ingestion_status)
    - [B-4. 制約とインデックス](#b-4-制約とインデックス)
    - [B-5. migration](#b-5-migration)
    - [B-6. PostgresStore](#b-6-postgresstore)
    - [B-7. Store契約テスト](#b-7-store契約テスト)
    - [Milestone B 完了条件](#milestone-b-完了条件)
  - [6. Milestone C：FastAPIと分析クエリ](#6-milestone-cfastapiと分析クエリ)
    - [C-1. API構成](#c-1-api構成)
    - [C-2. Health API](#c-2-health-api)
      - [`GET /health/live`](#get-healthlive)
      - [`GET /health/ready`](#get-healthready)
    - [C-3. Status API](#c-3-status-api)
    - [C-4. Traffic API](#c-4-traffic-api)
    - [C-5. Tracks API](#c-5-tracks-api)
    - [C-6. Rankings API](#c-6-rankings-api)
    - [C-7. Recent aircraft API](#c-7-recent-aircraft-api)
    - [C-8. クエリ性能](#c-8-クエリ性能)
    - [Milestone C 完了条件](#milestone-c-完了条件)
  - [7. Milestone D：モダンなMapLibreダッシュボード](#7-milestone-dモダンなmaplibreダッシュボード)
    - [D-1. デザイン方針](#d-1-デザイン方針)
    - [D-2. 地図スタイル](#d-2-地図スタイル)
    - [D-3. 地図上の航跡](#d-3-地図上の航跡)
    - [D-4. 画面構成](#d-4-画面構成)
      - [ヘッダー](#ヘッダー)
      - [ステータスカード](#ステータスカード)
      - [メイン領域](#メイン領域)
      - [下部](#下部)
    - [D-5. ECharts](#d-5-echarts)
    - [D-6. レスポンシブ・アクセシビリティ](#d-6-レスポンシブアクセシビリティ)
    - [D-7. フロントエンド方針](#d-7-フロントエンド方針)
    - [Milestone D 完了条件](#milestone-d-完了条件)
  - [8. Milestone E：保持、バックアップ、運用](#8-milestone-e保持バックアップ運用)
    - [E-1. 保持期限](#e-1-保持期限)
    - [E-2. DB状態確認](#e-2-db状態確認)
    - [E-3. バックアップ](#e-3-バックアップ)
    - [E-4. ログ](#e-4-ログ)
    - [Milestone E 完了条件](#milestone-e-完了条件)
  - [9. Milestone F：Compose統合と障害試験](#9-milestone-fcompose統合と障害試験)
    - [F-1. イメージ](#f-1-イメージ)
    - [F-2. Compose](#f-2-compose)
    - [F-3. readsbへのコンテナ内疎通](#f-3-readsbへのコンテナ内疎通)
    - [F-4. 結合テスト](#f-4-結合テスト)
    - [F-5. 障害試験](#f-5-障害試験)
      - [readsb停止](#readsb停止)
      - [DB停止](#db停止)
      - [不正JSON](#不正json)
      - [地図障害](#地図障害)
    - [Milestone F 完了条件](#milestone-f-完了条件)
  - [10. Milestone G：Linuxサーバー配置](#10-milestone-glinuxサーバー配置)
    - [G-1. 配置前](#g-1-配置前)
    - [G-2. 配置](#g-2-配置)
    - [G-3. 公開範囲](#g-3-公開範囲)
    - [G-4. 再起動試験](#g-4-再起動試験)
    - [G-5. 24時間soak test](#g-5-24時間soak-test)
    - [Milestone G 完了条件](#milestone-g-完了条件)
  - [11. Phase 1 最終受け入れ条件](#11-phase-1-最終受け入れ条件)
  - [12. 推奨実装順序](#12-推奨実装順序)
  - [13. Phase 2候補](#13-phase-2候補)
    - [Phase 2A：期間比較](#phase-2a期間比較)
    - [Phase 2B：受信局性能](#phase-2b受信局性能)
    - [Phase 2C：ヒートマップ](#phase-2cヒートマップ)
    - [Phase 2D：機体の再訪履歴](#phase-2d機体の再訪履歴)
    - [Phase 2E：今日の空](#phase-2e今日の空)
    - [Phase 2F：地図セルフホスト](#phase-2f地図セルフホスト)
  - [14. 作業再開時に必要な情報](#14-作業再開時に必要な情報)
    - [Phase 1実装中に必要](#phase-1実装中に必要)
    - [配置時までに必要](#配置時までに必要)
  - [15. 進捗記録](#15-進捗記録)
    - [セッション記録](#セッション記録)
    - [セッション記録](#セッション記録-1)
    - [セッション記録](#セッション記録-2)


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
- [!] **[未解決の不具合、原因はユーザーのブラウザ環境側に絞り込み済み]** MapLibreの地図がモダンで、航跡とラベルを読み分けられる — 実装(高度別配色・透明度・選択強調)は完了しているが、ユーザーの実ブラウザでは依然として地図が表示されない。仮環境・本番同等のDockerイメージいずれでも再現し、さらにPlaywright(実Chromiumエンジン)でユーザーと同じURLを自動ロードしたところ地図・CSPともに問題なく動作することを確認した(2026-07-28)。これによりサーバー・アプリコード・ネットワーク経路は原因から除外され、ユーザーのブラウザ環境固有の要因(拡張機能・古いキャッシュ等)に絞り込まれた。シークレットウィンドウでの再現確認待ち。ランキング(最遠/最近)・最近観測した機体パネルは実データで正しく更新されることを確認済み。
- [x] 地図タイル障害時も他機能が使える(構造的に各パネル独立、`map.on("error")`でmapパネルのみエラー表示)。
- [!] **[未検証]** PCとスマートフォンで主要情報が読める — レスポンシブCSSは実装済みだが実機/実ブラウザ確認は未実施。
- [x] stale/異常/データなしを正常状態と誤認しない(`ingestion_state`の4値をbadge・カード両方に反映、staleで数値を"--"化)。
- [!] **[未検証]** ブラウザーで重大なconsole errorがないこと — このセッションにはブラウザ実行環境(Claude in Chrome未接続、headlessブラウザ・Node.js未導入)がなく確認できなかった。curlによるHTTP応答・Content-Type確認、および全JSファイルの読み返しによるレビューのみ実施。

**総括**: バックエンド(API・DB)側は自動テストで裏付けられた完成度だが、フロントエンドの実際の見た目・操作感・console errorの有無は本セッションでは確認できていない。ユーザー側で `docker compose up -d adsb-db` → APIサーバー起動 → `http://<host>:8088/` をブラウザで開いての最終確認を推奨する。

---

## 8. Milestone E：保持、バックアップ、運用

### E-1. 保持期限

- [x] `RAW_RETENTION_DAYS`を設定可能にする(既存`Settings.raw_retention_days`をそのまま使用)。
- [x] 既定30日より古いobservationsを削除する(`app/retention.py:delete_old_observations`)。
- [x] 削除は小さなbatchで行う(既定1000件ずつ、`id IN (SELECT ... LIMIT $2)`パターン)。
- [x] 1分集計を削除対象に含めない(`traffic_minute`には一切触れない設計。契約テスト`test_traffic_minute_rows_are_never_touched`で確認)。
- [x] 削除件数と所要時間をログへ出す(バッチ毎・完了時にINFOログ)。
- [x] 同時実行を防止する(`pg_try_advisory_lock`。契約テスト`test_concurrent_run_skips_when_advisory_lock_held`で確認)。
- [x] 保持処理のdry-runを用意する(`--dry-run`、削除せずCOUNTのみ)。
- [x] 境界時刻をUTCでテストする(`tests/unit/test_retention.py`)。

常駐実行用に`adsb-retention`Composeサービス(`python -m app.retention --loop`、既定24時間毎)を追加し、実際に`compose.yaml`へ組み込んで起動・ログ出力を実機確認済み。

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

- [x] コマンドをREADMEへ記載する(`scripts/db_status.py`、README「DB status」節)。
- [x] 秘密情報を出力しない(DATABASE_URLや接続情報は一切出力しない。`test_render_report_contains_no_secrets_and_key_fields`で確認)。

実データ(observations 1,529件、DB総サイズ8.3MB)に対して実機実行し、正しい集計値が出力されることを確認済み(2026-07-28)。

### E-3. バックアップ

- [x] `pg_dump`による論理バックアップを実装する(`scripts/backup.sh`、`docker compose exec adsb-db pg_dump --format=custom`。adsb-dbはポート非公開のため、ホストから直接`pg_dump`することはできず、コンテナ内実行が必須)。
- [x] バックアップ先を設定可能にする(`BACKUP_DIR`環境変数、既定`backups/`)。
- [x] ファイル名にUTC日時を含める(`adsb-db-YYYYMMDDTHHMMSSZ.dump`)。
- [x] 一時ファイルを安全に扱う(`.tmp`へ書き込み→完了後に同一ファイルシステム内で`mv`、`trap`でクリーンアップ)。
- [x] 失敗時に不完全ファイルを正常バックアップとして残さない(`set -euo pipefail`+`trap cleanup EXIT`。`pg_dump`失敗を模擬したテストで、`.tmp`も最終ファイルも一切残らないことを確認済み)。
- [x] 保持世代数を設定可能にする(`BACKUP_KEEP_GENERATIONS`環境変数、既定7。5世代→3世代保持のプルーニング動作を確認済み)。
- [x] バックアップファイル権限を確認する(ディレクトリ700、ファイル600。実機で確認済み)。
- [x] 本番とは別の一時DBへ復元試験する(`scripts/restore_test.sh`、使い捨ての`postgres:16`コンテナへ`pg_restore`、終了時に確実に削除)。
- [x] 復元後の件数と代表クエリを確認する(全テーブルの件数、最新observationの代表クエリを出力)。

実データに対して`backup.sh`→`restore_test.sh`を実機で1往復実行し、aircraft 74件・observations 1,646件・traffic_minute 52件・ingestion_status 605件が正しく復元され、代表クエリ(最新観測)も正常に返ることを確認済み(2026-07-28)。

### E-4. ログ

- [x] JSONまたは一貫した構造化ログを使用する(`%(asctime)s %(levelname)s %(name)s %(message)s`をcollector/retention/APIの3サービス全てに統一。**今回の点検でAPI(`app/api/asgi.py`)だけ`logging.basicConfig`未設定だったことを発見・修正**し、他2サービスと書式が揃っていなかった不整合を解消した)。
- [x] 正常pollごとの過剰ログを避ける(成功pollは`ingestion_status`保存以外に定型ログを出さない設計を確認、変更なし)。
- [x] 接続失敗と回復を記録する(失敗は既存の`logger.warning("readsb fetch failed")`。**今回の点検で「回復」側のログが存在しないことを発見**、backoff明けの初回成功pollで`"readsb fetch recovered after backoff"`を出すよう追加。実機ログでは未発火(このセッション中に本物の障害が起きていないため)だが、`test_readsb_outage_backs_off_without_crashing_and_recovers`で自動テスト済み)。
- [x] 不正データ除外件数を記録する(**今回の点検で`normalize_poll`が計算する`excluded_reasons`が呼び出し側で一切ログされず捨てられていたことを発見**、`CollectorService.poll_once`に`logger.info`を追加。実機ログで`poll excluded 7 record(s): {'stale': 7}`のように実際に出力されることを確認済み(2026-07-28))。
- [x] Dockerログの`max-size`と`max-file`を設定する(Milestone Fで全サービスに`json-file`/10m/3設定済み)。
- [x] パスワード、完全な接続URL、レスポンス本文をログへ出さない(既存コードを点検、`database_url`や生レスポンスボディをログ出力する箇所は皆無であることを確認)。

### Milestone E 完了条件

- [x] 保持期限処理がテストデータで機能する(契約テスト5件、実DBに対する境界・batch・dry-run・同時実行防止を確認)。
- [x] DB増加量を確認できる(`scripts/db_status.py`、実データ8.3MB/1,529件で実行確認)。
- [x] backupと別DBへのrestoreが成功する(`scripts/backup.sh`→`scripts/restore_test.sh`を実データで1往復確認)。
- [x] ログが容量無制限に増えない(全サービスDockerログ`max-size 10m`/`max-file 3`)。

**Milestone E完了。** 2026-07-28。

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
- [x] fixtureサーバーからcollectorが取得する — 実readsbでの検証(本番同等環境)に加え、`tests/integration/test_end_to_end.py`で「空DB→migration→collector(fixtureペイロード、httpx.MockTransportで実ネットワーク呼び出しなし)→実FastAPIアプリで読み取り」までを1本の自動テストとして追加した。位置ありの機体・位置なし(ground)の機体の両方が正しく`/api/status`・`/api/aircraft/recent`・`/api/tracks`に反映されることを確認。
- [x] DBへデータが保存される — 実データで確認済み(現在1,900件超のobservations、ingestion_statusが約5秒おきに成功記録)。
- [x] 全APIがデータを返す — `/api/status`等がDBの実データを反映して応答することを確認済み。
- [!] **[部分実施]** Web UIが表示される — ステータスバッジ・数値・バージョン表示は動作確認済み。地図はPlaywright(実Chromiumエンジン)による自動検証では問題なく表示されることを確認したが、ユーザーの実ブラウザでの再現待ち(詳細はMilestone D完了条件・下記「地図障害」参照)。
- [x] Compose再起動後もデータが残る — 実機で`docker compose restart adsb-db`を実行し、`scripts/db_status.py`で再起動前後の最古観測時刻(`oldest`)が変化していないこと、かつ再起動後もcollectorが正常に書き込みを継続していることを確認済み(2026-07-28)。

### F-5. 障害試験

本番readsbではなくモックとテストDBで行う。以下は全て自動テスト化済み(`pytest`、158件全green)。DB停止/復旧試験のみ、`docker stop`/`docker start`で実際に制御できる使い捨てPostgresコンテナ(`tests/contract/pg_container.py`の共有fixtureとは別に、この試験専用に用意)を使用し、モック内で済ませず本物のTCP切断を発生させている。

#### readsb停止

- [x] collectorがクラッシュループしない(`test_readsb_outage_backs_off_without_crashing_and_recovers`)。
- [x] バックオフする(同上、interval増加を確認)。
- [x] ready/status/UIがstaleを示す(`test_ready_fails_on_stale_data`、`test_status_stale_zeroes_counts`)。
- [x] 復旧後に自動回復する(`test_readsb_outage_backs_off_without_crashing_and_recovers`。E-4で追加した回復ログ`"readsb fetch recovered after backoff"`もこのテストで確認)。

#### DB停止

- [x] collector/APIが秘密情報のないエラーを出す(API側: `test_db_error_response_never_contains_connection_details`、パスワードを含む偽例外を注入してもレスポンスに一切含まれないことを確認。collector側: `test_real_auth_failure_exception_does_not_contain_the_password`、実Postgresへ誤ったパスワードで接続させ、asyncpg自体の例外メッセージにパスワードが含まれないことを実証)。
- [x] メモリが無制限に増えない(アーキテクチャ上、失敗した書き込みをバッファする仕組みが存在しない設計を確認済み。B-6のdocstringに理由を記載済みで再確認)。
- [x] readinessが503になる(`test_ready_goes_503_on_db_down_and_recovers_after_db_returns`、実際に`docker stop`したPostgresに対して`/health/ready`を叩き503を確認)。
- [x] DB復旧後に再接続する(同テストで`docker start`後、追加コードなしにasyncpgプールが自動再接続し`/health/ready`が200に戻ることを確認)。

#### 不正JSON

- [x] JSON構文エラー(`test_unparseable_json_body_does_not_crash_service`、有効なJSONとしてすら解析できないボディを追加)。
- [x] `aircraft`欠損(`tests/unit/test_normalize.py::test_invalid_payload_shape_does_not_crash`)。
- [x] 巨大レスポンス(`tests/unit/test_normalize.py::test_handles_large_aircraft_count_without_crashing`)。
- [x] 部分的な型不正(`tests/fixtures/aircraft_missing_fields.json`、`aircraft_lat_only.json`ベースのテスト群)。
- [x] 不正座標(`tests/fixtures/aircraft_out_of_range_coords.json`ベース)。
- [x] `alt_baro: "ground"`(`tests/fixtures/aircraft_ground_altitude.json`ベース)。

#### 地図障害

- [x] style URL失敗(`tests/integration/test_map_failure_playwright.py`、Playwrightの`page.route()`で実際にMAP_STYLE_URLへのリクエストを失敗させ、`#map-error`にエラー表示されることを確認)。
- [x] tile失敗(style自体が失敗する時点でtileリクエストは発生しないため、実質的にstyle URL失敗テストに包含される)。
- [x] 地図以外の機能が継続する(同テストで、地図が失敗している状態でもステータスカード`#card-active`が実データを表示し続けることを確認)。

既知の未解決バグ: ブラウザで地図モジュールの動的import自体が失敗するケースを確認済み(`Failed to fetch dynamically imported module: .../static/js/map.js`)。原因はMapLibre本体のvendoring・キャッシュ制御修正後も再現しており未特定。**2026-07-28、本番同等の実環境(本Compose構成、実readsbデータ)でユーザーが再確認した結果、地図は依然として表示されないことを確認した。** 一方、ランキング(最遠/最近)・最近観測した機体は実環境で正しく更新されることを確認した。これにより、地図バグは即席検証コンテナ固有の問題ではなく、コード自体(または対象ブラウザ環境)に起因すると切り分けられた。

**2026-07-28、Playwright(実Chromiumエンジン、ヘッドレス)を導入し、ユーザーと全く同じURL(`http://127.0.0.1:8088/`と実際のTailscale URL `http://100.87.106.77:8088/`の両方)を自動ロードして検証した結果、地図は正常に表示され(`canvas.maplibregl-canvas`が1つ生成、console error・`#map-error`表示なし)、CSP違反も一切発生しなかった。** これにより、サーバー側の静的ファイル配信・CSP設定・`host.docker.internal`経由のネットワーク経路には原因がないことがChromiumエンジンでの実ロードにより確定した。残る原因候補は、ユーザーの実ブラウザ環境固有の要因(拡張機能によるブロック、`no-store`導入前の古いキャッシュが何らかの理由で残存、ブラウザ側の一時的な不具合等)に絞られた。合わせて、次回以降devtoolsなしでも自己診断できるよう、`app/static/js/main.js`に`securitypolicyviolation`イベントリスナー(CSP違反発生時に`#map-error`へ直接表示)と、`import()`前の明示的な`fetch()`事前チェック(モジュールリンクエラーとネットワーク層エラーを区別して表示)を追加した。次のアクション: ユーザーにシークレット/プライベートウィンドウ(拡張機能無効)で同じURLを開いて再現するか確認してもらう。

### Milestone F 完了条件

- [x] Composeだけで空環境から再現できる — サービス構成・起動順序は実機確認済み。fixtureサーバーベースの自動テスト(`test_end_to_end.py`)も追加し、空DB→migration→collector→APIの一気通貫を自動検証できる状態にした。
- [x] 正常、停止、復旧シナリオが自動または再現可能な手順で確認済み — F-5の全項目を自動テスト化(158件green)。
- [x] readsbへの接続経路が安全 — `host.docker.internal`経由のDocker内部限定、readsb側の公開範囲は変更していない(F-3参照)。
- [x] DBとreadsbを外部公開していない — `adsb-db`は`ports:`なし、readsbはこのアプリからの変更なし(既存のLAN/Tailscale公開範囲のまま)。

**Milestone F完了。** 2026-07-28。地図表示バグ自体はMilestone Dの完了条件欄で引き続き追跡(ユーザーのブラウザ環境固有の要因に絞り込み済み、シークレットウィンドウでの再現確認待ち)。

---

## 10. Milestone G：Linuxサーバー配置

### G-1. 配置前

- [!] **[想定内のFAIL、対応不要]** Phase 0レポートを再確認する — `scripts/check_environment.sh`を再実行したところ、G(ネットワーク/ポート)のみFAILし全体verdictがFAILになった(2026-07-28)。原因は「app_port 8088 in use」— このチェックは元々「配置**前**にポートが空いているか」を確認する設計であり、今は既に自分自身の`adsb-api`が意図通り8088で稼働しているためFAILするのは当然の結果。他チェック(A/B/C/D/E/F/H)は全てPASSのまま。**影響: なし。既存サービス・他ポートとの衝突ではなく、自分自身の正常稼働が検出されているだけ。** CLAUDE.mdの「FAILは黙って回避しない」方針に従い、原因と無害である理由をここに明記した上で対応不要と判断する。
- [x] サーバー上のGit差分と配置済みファイルを確認する(`git status`クリーン、全マイルストーンの変更はコミット済み)。
- [x] 使用予定ポートが空いていることを再確認する — 上記の通り8088は自分自身が使用中(意図通り)。他ポート(80=readsb、8504/8542=既存サービス)との衝突なし。
- [x] ディスク空き容量を再確認する(175.9GB空き、10%使用。30日分の推定DB増加量(約440MB、E-2参照)に対して十分)。
- [x] 既存3サービスの状態を記録する(`readsb`/`tar1090`/`fr24feed`全て`active`、Phase 0レポートH項目で前後比較しunchangedを確認)。
- [x] rollback手順を準備する — `git log`で目的のタグ(例`v0.4.3`)へ`git checkout`→`docker compose build && docker compose up -d`で任意バージョンへ戻せる。DBスキーマの後方非互換な変更は現時点でなし(追加のみ)。データ自体を戻す必要がある場合は`scripts/restore_test.sh`と同じ手順(`pg_restore`)を本物の`adsb-db`に対して実行する(未実施、手順のみ準備)。
- [x] 本番`.env`をサーバー上だけに作る(このホスト上にのみ存在、`.gitignore`で除外、コミット履歴に含まれないことを確認済み)。
- [x] 受信地点をログや公開画面で精密表示しない設定にする(`MAP_SHOW_RECEIVER_MARKER=false`、`/api/config`は緯度経度を一切返さない。ログにも`RECEIVER_LAT`/`RECEIVER_LON`の値を出力する箇所なし)。

### G-2. 配置

- [x] x86-64用イメージをサーバーでビルドまたは取得する(このホスト自体がx86-64の対象サーバーであり、`docker compose build`で実ビルド済み)。
- [x] DBとmigrationを起動する。
- [x] migration成功を確認する(`adsb-migrate`は毎回exit 0)。
- [x] collectorを起動する。
- [x] 実readsbから取得できることを確認する(継続的に200 OK、実データ収集中)。
- [x] APIを起動する。
- [x] localhostからhealth/API/UIを確認する(`curl`で`/health/live`・`/health/ready`・`/api/*`全て確認済み)。
- [x] 既存readsb、tar1090、fr24feedが継続稼働していることを確認する(`systemctl is-active`で3つとも`active`)。

### G-3. 公開範囲

初期はlocalhostまたはLAN内を既定とする。

- [x] 希望する公開範囲を確認する(ユーザー選択: Tailscale経由でのアクセスを維持)。
- [x] **[今回の点検で発見・修正]** LAN公開ならLANインターフェースとファイアウォールを確認する — `APP_BIND_HOST=0.0.0.0`だったため、Tailscale(100.87.106.77)だけでなく家庭内LAN(192.168.11.0/24)からも認証なしで到達可能だったことが判明(ufw/iptablesはsudo権限がなく確認不可だったため、bindアドレス自体で制限する方式を採用)。ユーザーに確認の上、`APP_BIND_HOST`をTailscale IP自体(`100.87.106.77`)に変更し再デプロイ。実機で`curl http://192.168.11.19:8088/health/live`が接続拒否になり、`curl http://100.87.106.77:8088/health/live`は引き続き成功することを確認済み(2026-07-28)。
- [x] インターネット公開ならリバースプロキシを使用する — 該当なし(Tailscaleのみに制限、インターネット非公開)。
- [x] インターネット公開ならTLSを必須にする — 該当なし(同上。Tailscale自体が暗号化されたWireGuardトンネルであるため追加のTLS層は不要と判断)。
- [x] 必要に応じて認証を追加する — 個人利用・Tailscaleネットワーク内限定のため追加認証なしと判断。
- [x] PostgreSQLを公開しない(`adsb-db`はポート非公開、変更なし)。
- [x] readsb JSONの直接公開を増やさない(readsb側の設定は一切変更していない)。
- [x] 精密な受信地点や管理情報を公開しない(G-1参照)。

### G-4. 再起動試験

既存サービスへの影響を避けるため、最初はアプリのCompose再起動だけを行う。

- [x] アプリCompose再起動後に自動復旧する(`docker compose restart adsb-api adsb-collector adsb-db`後、全コンテナ`Up`/`healthy`に復旧、`/health/ready`・`/api/status`とも正常応答を確認。OS再起動時のようなbind race自体が発生しないため単純に復旧)。
- [x] DBデータが残る(OS再起動試験の一環で確認。`aircraft.first_seen_at`の最小値が再起動時刻より前であることを実機確認、observations/traffic_minute/ingestion_statusとも非ゼロで継続)。
- [x] collectorが重複起動しない(OS再起動試験の一環で確認。`docker ps -a`で`adsb-collector`コンテナは常に1つのみ)。
- [x] 既存サービスが継続稼働する(`systemctl is-active readsb tar1090 fr24feed`が3つとも`active`のまま、無停止・無再設定)。

OS再起動試験はユーザーの明示的な許可と実施時間帯を確認してから行う。

- [x] OS再起動の許可を得る(ユーザーが実施、2026-07-28 03:12 UTC)。
- [x] 再起動後にDockerが起動する(`docker.service`はブート後正常に起動)。
- [!] **[今回の点検で発見、未修正]** アプリが自動復旧する — `adsb-db`/`adsb-collector`/`adsb-retention`は自動復旧したが、`adsb-api`は復旧しなかった。原因は2つ:
  1. v0.5.1で`APP_BIND_HOST`をTailscale IP(`100.87.106.77`)に固定したため、ブート時に`docker.service`と`tailscaled.service`がほぼ同時に起動し、`tailscale0`にIPが割り当てられる前にDockerがポートbindを試みて`cannot assign requested address`で失敗(`journalctl -u docker`で確認)。Dockerの`restart: unless-stopped`はプロセス側の異常終了時のみ再試行し、コンテナ起動時のネットワーク設定失敗そのものは再試行しないため、そのまま停止状態が続いた。
  2. 手動で`docker compose up -d adsb-api`しても、失敗した起動試行で壊れたネットワークエンドポイントがそのまま再利用され、`adsb-db`への名前解決が`socket.gaierror`で失敗しクラッシュループした。`docker compose up -d --force-recreate adsb-api`でエンドポイントを作り直すことで復旧(単純な`up -d`/`restart`では不十分)。
  - 対応方針はユーザーと協議し、今回は「記録のみ、修正は次回以降」を選択(2026-07-28)。恒久対応の候補: (a) `tailscale0`のIP確立を待ってから`docker compose up`するsystemdユニットを追加する、(b) `APP_BIND_HOST=0.0.0.0`に戻しufw等のホストファイアウォールでTailscaleインターフェースのみへ制限する。どちらもsudo操作を伴うため、実施前にユーザーへ提示が必要(CLAUDE.md記載の運用制約)。
- [x] readsb、tar1090、fr24feedも正常復旧する(`systemctl is-active`で3つとも`active`)。

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

### セッション記録

```text
日付: 2026-07-28
完了したMilestone/Task: Milestone G-4（再起動試験）の実機検証 — ユーザーがOS再起動を実施済みの状態から継続
変更した主要ファイル:
  - PLAN.md（G-4チェックリストの実測結果を記録。コード変更なし）
実行したテスト: なし（今回はコード変更なし、実機検証のみ）
実環境で確認したこと:
  - OS再起動後、`adsb-db`/`adsb-collector`/`adsb-retention`は`restart: unless-stopped`により自動復旧していたが、`adsb-api`は`Exited (128)`のまま停止していることを`docker compose ps`/`docker inspect`で発見。
  - `journalctl -u docker`で原因を特定: v0.5.1で`APP_BIND_HOST`をTailscale IP固定にしたため、ブート時に`tailscaled`のIP割り当てより先にDockerがポートbindを試み`cannot assign requested address`で失敗。Dockerはコンテナ起動時のネットワーク設定失敗を自動再試行しないため、そのまま停止し続けていた。
  - `docker compose up -d adsb-api`で再起動を試みたところ、`socket.gaierror: Temporary failure in name resolution`（`adsb-db`への名前解決失敗）でクラッシュループ。前回の失敗した起動試行で壊れたネットワークエンドポイントが再利用されたことが原因と判断。
  - `docker compose up -d --force-recreate adsb-api`でエンドポイントを作り直し復旧。`/health/live`・`/health/ready`・`/api/status`とも正常応答、実readsbデータの取り込みも継続していることを確認。
  - DBデータの継続性を確認: `aircraft.first_seen_at`の最小値(01:38 UTC)が再起動時刻(03:12 UTC)より前であり、`docker compose down`されずにvolumeが保持されたことを裏付け。observations 3,323件・traffic_minute 105件・ingestion_status 1,227件とも非ゼロ。
  - collectorの重複起動なし(`docker ps -a`で`adsb-collector`は常に1コンテナ)。
  - 既存の`readsb`・`tar1090`・`fr24feed`は`systemctl is-active`で3つとも`active`のまま、無停止・無再設定。
  - 追加で`docker compose restart adsb-api adsb-collector adsb-db`（OS再起動を伴わない単純なCompose再起動）も実施し、こちらは即座に正常復旧することを確認(ブート順序レースが存在しないため)。
残課題（重要 — ユーザー確認推奨）:
  - **G-4の「アプリが自動復旧する」は未達**。恒久対応をユーザーに提示し、今回は「記録のみ、修正は次回以降」を選択いただいた(2026-07-28)。対応候補は本文G-4節に記載: (a) `tailscale0`のIP確立を待ってから`docker compose up`するsystemdユニットを追加、(b) `APP_BIND_HOST=0.0.0.0`に戻しufw等のホストファイアウォールでTailscaleインターフェースのみへ制限。どちらもsudo操作を伴うため、実施前に必ずユーザーへ提示すること(CLAUDE.md運用制約)。
  - 次回OS再起動が発生した場合(予期しない停電・カーネル更新等を含む)、同じ理由で`adsb-api`が復旧しない可能性が高い。恒久対応までは、再起動後に`docker compose ps`を確認し、`adsb-api`が起動していなければ`docker compose up -d --force-recreate adsb-api`が必要になる。
次に行うTask: G-4残り(恒久対応の実施可否をユーザーと決定) → G-5（24時間soak test）
ユーザー判断が必要な事項:
  - 恒久対応(a)systemdユニット追加 / (b)0.0.0.0+ufw のどちらを取るか、いつsudo作業を許可するか。
```

---

## 16. Phase 2 詳細実装計画（Milestone H〜O）

§13のPhase 2候補のうち、2A（期間比較）・2B（受信局性能）・2C（ヒートマップ）・2D（機体の再訪履歴）・2E（今日の空）を対象に、2026-07-28に詳細計画を作成した。**2F（地図セルフホスト）は対象外（保留）**。Milestone G-4（OS再起動後のadsb-api復旧不全）も対象外（保留、詳細はG-4のセッション記録を参照）。G-5（24時間soak test）はPhase 2と並行して進めてよく、ブロッカーではない。

計画のフルテキストはこのセッションの計画ファイルに基づく。設計判断の根拠（既存コードの規約調査結果）は各Milestoneの説明に要約する。以下は実装順の推奨であり、H→I→J→K→Lはこの順、L完了後にM/N/Oへ進む(M/N/OはLの新スキーマに依存)。I/J/Kはスキーマ変更を伴わないため、優先度が変われば入れ替え可。

### 全体を通じた設計判断

- `traffic_minute`(永年保持)には機体ユニーク数・高度・距離・方位がないため、2A/2D/2Eの30日超の期間比較には新しい日次ロールアップ（Milestone L）が必須。`observations`は`RAW_RETENTION_DAYS`(既定30日)で削除されるため、削除前に集計を書き出す必要がある。
- 2B・2Cはスキーマ変更不要(`observations`に既にbearing_deg/distance_km/altitude_ftがある)。価値を先に積み上げるため、スキーマ変更を伴うMilestone Lより先に着手する。
- 現在のAPIに書き込み系エンドポイントは一つもない(全てGET、認証なし、Tailscale/localhost限定)。2Dの「お気に入り機体」はこの前提を壊さないよう、サーバー側エンドポイントを持たずブラウザの`localStorage`のみで実装する。
- `chart.js`には再利用可能なチャート抽象が存在しない(エラー表示DOM要素IDが1つにハードコードされている等)。後続の全チャート追加を妨げるため、最初にリファクタリングする(Milestone H)。
- 2Bと2Eは既存ダッシュボードとは別の専用ページとし、共通ナビゲーションでリンクする(ユーザー判断、2026-07-28)。2Eの通知はSlack/Discord互換のwebhookとし、既定で無効・設定で有効化するオプトイン方式とする(ユーザー判断、2026-07-28)。

### Milestone H：チャートファクトリと共通ナビゲーション

- [x] `app/static/js/chart.js`から`createChart(containerId, errorElId, buildOption)`ファクトリを抽出する。
- [x] `createTrafficChart`をこのファクトリの最初の呼び出し元にする(`{setData, resize}`という既存の呼び出し契約は変更しない、`main.js`が依存しているため)。
- [x] `index.html`に共通`<nav class="app-nav">`(ダッシュボード/受信性能/今日の空/機体履歴)を追加する。
- [ ] 後続Milestoneで追加する各新規ページにも同じnavブロックを複製する(テンプレートエンジンがないため、意図的な複製として許容する) — receiver.html/daily.html/history.htmlの作成時に対応。
- [x] アクティブページを`aria-current="page"`で表示する(`data-`属性ではなくARIA標準属性を採用)。

**Milestone H 完了条件**
- [x] 既存ダッシュボードの見た目・挙動が変化しない(Playwright実ブラウザで確認。詳細はセッション記録参照)。
- [x] 新規エンドポイントなし。
- [x] `make test`/`make lint`が通る(158件全green)。

### Milestone I：2B 受信局性能（スキーマ変更なし）

- [x] `app/db/queries/receiver.py`を新規作成する（`tracks.py`の「2クエリ+Pythonでの後処理」パターンに倣う）。
  - [x] `bearing_range(pool, hours)` — `width_bucket(bearing_deg, 0, 360, 16)`で16方位に分類し、方位ごとの`MAX(distance_km)`。
  - [x] `altitude_band_range(pool, hours)` — 高度帯ごとの最大受信距離。
  - [x] `reception_timeseries(pool, hours)` — `traffic_minute`から`message_count_delta`と位置取得率の時系列(`hours<=24`は分バケット、それ超は時バケットに切替、`traffic.py`のゼロ埋めバケット方式を踏襲)。
- [x] 高度帯(`ALTITUDE_BANDS`)の定義をPython側(`app/domain/bands.py`)に一本化し、`GET /api/config`経由でフロントエンドへ渡した。`map.js`のハードコードされた定義を置き換えた(JS/Python間の値のズレを防ぐ)。
- [x] `app/api/routers/receiver.py`を新規作成する: `GET /api/receiver/bearing-range?hours=1..720`(既定24)、`GET /api/receiver/altitude-range?hours=1..720`、`GET /api/receiver/reception?hours=1..720`。`app/api/main.py`に登録した。
- [x] **[このMilestoneでまとめて対応]** `ingestion_status`の保持ポリシー未定義(Milestone B以降3回のセッション記録で継続報告)を解消した。`app/retention.py`を汎用の`_delete_old_rows`ヘルパーに整理し、`delete_old_observations`(既存)と`delete_old_ingestion_status`(新規、専用advisory lock key `84372911`)の2本立てに拡張。`_run_once`は両方を順に実行する。`tests/contract/test_retention.py`に`ingestion_status`用テスト(削除範囲/dry-run/lock独立性/lock競合)を追加。`scripts/db_status.py`の`_TABLES`は元々`ingestion_status`を含んでいたため変更不要だった。
- [x] `app/static/receiver.html` + `app/static/js/receiver.js`を新規作成した(極座標バーチャート、高度帯レンジの水平バーチャート、メッセージ数/位置取得率の折れ線チャート、いずれもMilestone Hの`createChart`ファクトリ経由)。navに追加した(Hで先行追加していたリンク先を実装)。
- [x] テスト: `tests/unit/test_bands.py`・`tests/unit/test_receiver_query.py`(バケット化ヘルパーの単体テスト、DBなし)、`tests/integration/test_api.py`に3エンドポイント分の結合テスト(空DB/範囲外422/データありの3パターン)を追加、`test_openapi_lists_all_endpoints`更新。テスト総数158→174(+16)。

**Milestone I 完了条件**
- [x] 3クエリともEXPLAIN ANALYZEを確認した(合成データ: aircraft 2,000件/observations 34,000件/traffic_minute・ingestion_status各43,200件=30日分、使い捨てdocker postgresコンテナ上)。`hours=24`のbearing_rangeは`ix_observations_observed_at`のBitmap Index Scan(1.2ms)。`hours=720`(ほぼ全期間)のbearing_range/altitude_band_rangeはSeq Scan(各5.9ms/6.6ms)にフォールバックした — 対象が全34,000行の過半を占め、Postgres自身がSeq Scanを最適と判断した結果であり、この規模では関数インデックスを追加する根拠がないと判断(先回りしない方針どおり)。reception_timeseriesの時バケット集計(720h)は14.9ms。全て目標値(500ms)を大幅に下回る。
- [x] 実データでページが表示される(使い捨てpostgres + 実uvicorn + Playwright Chromiumで`/static/receiver.html`を目視確認。3チャートとも描画、nav・アクティブページハイライトも正常、consoleエラーなし)。
- [x] `make test`/`make lint`が通る(174件全green、lint/format clean)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone I（2B 受信局性能）
変更した主要ファイル:
  - app/domain/bands.py（新規、ALTITUDE_BANDSの単一情報源。band_key_for_altitude/band_case_sqlヘルパー）
  - app/db/queries/receiver.py（新規、bearing_range/altitude_band_range/reception_timeseries）
  - app/api/routers/receiver.py（新規、GET /api/receiver/bearing-range・altitude-range・reception）
  - app/api/main.py（receiverルーター登録）
  - app/api/schemas.py（Bearing/AltitudeRange/Reception系レスポンス、ConfigResponse.altitude_bands追加）
  - app/api/routers/config.py（altitude_bandsをGET /api/configに追加)
  - app/retention.py（_delete_old_rowsへの共通化、delete_old_ingestion_status追加、advisory lock key 84372911）
  - app/static/js/map.js（ハードコードのALTITUDE_BANDSを廃し、setAltitudeBands(config.altitude_bands)で受け取る方式に変更)
  - app/static/js/main.js（mapModule.setAltitudeBands呼び出し追加、DEFAULT_CONFIGにaltitude_bands: []追加)
  - app/static/js/api.js（getBearingRange/getAltitudeRange/getReception追加)
  - app/static/receiver.html・app/static/js/receiver.js（新規ページ、極座標/水平バー/折れ線の3チャート)
  - tests/unit/test_bands.py・tests/unit/test_receiver_query.py（新規）
  - tests/integration/test_api.py（receiver 3エンドポイント分の結合テスト追加、config応答にaltitude_bands検証追加、OpenAPI一覧更新）
  - tests/contract/test_retention.py（ingestion_status用テスト4件追加）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、174件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - 使い捨てdocker postgresコンテナに合成データ(aircraft 2,000件/observations 34,000件/traffic_minute・ingestion_status各43,200件=30日分、Milestone C-8と同規模)を投入し、3クエリ全てにEXPLAIN ANALYZEを実施。`hours=24`のbearing_rangeは`ix_observations_observed_at`のBitmap Index Scan(1.2ms)。`hours=720`のbearing_range/altitude_band_rangeはSeq Scanにフォールバック(5.9ms/6.6ms) — 対象範囲が全期間の過半を占めるためPostgres自身の最適判断であり、この規模で関数インデックスを追加する根拠はないと判断(測定してから判断する方針どおり、先回りして追加せず)。retention側の`delete_old_ingestion_status`の選択クエリは既存の`ix_ingestion_status_checked_at`を正しく利用(Index Scan Backward)。
  - Milestone Hと同じ手法(使い捨てPostgres + 実uvicorn + Playwright Chromium)で`/static/receiver.html`を目視確認。3チャート(極座標バー、高度帯水平バー、メッセージ数/位置取得率の折れ線)とも正しく描画、nav 4リンク・アクティブページハイライト(受信性能)とも正常、consoleエラーはゼロ。スクリーンショットで最終確認済み(セッション内一時ファイル、コミットせず)。
残課題:
  - daily.html/history.htmlは引き続き未作成のため、navの該当2リンクは404のまま(Milestone N/Oで解消予定、既知)。
  - `app/retention.py`の`_run_loop`は失敗時に例外をログして次サイクルへ進む既存方針のまま(observations/ingestion_statusのどちらかが失敗しても他方の次回実行は妨げない設計)。
次に行うTask: Milestone J（2A クイックウィン）
ユーザー判断が必要な事項: なし
```

### Milestone J：2A クイックウィン（スキーマ変更なし）

- [x] `index.html`の未配線`#card-unique`要素に`TrafficResponse.unique_aircraft_count`(既存)を配線した(`ui.js`に`setUniqueCount`追加、`chart.js`の`refreshTraffic`が取得済みtrafficを返すよう変更、`main.js`の`refreshTrafficAndCard`ラッパーから呼び出し)。
- [x] `app/db/queries/distribution.py`を新規作成した: `hour_of_day_unique(pool, days)`、`altitude_histogram(pool, hours, bucket_ft=1000)`、`speed_histogram(pool, hours, bucket_kt=50)`。ヒストグラムは`traffic.py`と異なりゼロ埋めせず、存在するバケットのみ返す(連続ドメインを埋める必要がないため)。
- [x] `app/api/routers/distribution.py`を新規作成した: `GET /api/distribution/hour-of-day?days=1..30`、`GET /api/distribution/altitude?hours=1..720`、`GET /api/distribution/speed?hours=1..720`。`app/api/main.py`に登録した。
- [x] CSVエクスポート: `GET /api/traffic.csv?hours=1..168`(既存`traffic.py`の`get_traffic`を再利用、標準ライブラリ`csv`+`StreamingResponse`、`Content-Disposition: attachment`)。他の全エンドポイントがPydantic `response_model`でOpenAPIに現れる方針のため、ストリーミングでスキーマ化しづらいこのエンドポイントのみ`include_in_schema=False`(既存の`/`ダッシュボードルートと同じ前例)。
- [x] 既存ダッシュボードに新規パネル(時間帯別ユニーク機数バーチャート、高度・速度ヒストグラム、CSVダウンロードリンク)を追加した(新規ページではなく既存トラフィックパネルの拡張。3パネルは新規`.distribution-area`グリッド、レスポンシブブレークポイントにも追加)。
- [x] テスト: Milestone Iと同パターン(`tests/integration/test_api.py`に3エンドポイント+CSVの結合テスト、`test_openapi_lists_all_endpoints`更新)。純Pythonのバケット化ロジックがない(集計はSQL側で完結)ため、Milestone Iのような専用unit testファイルは追加していない。テスト総数174→181(+7)。

**Milestone J 完了条件**
- [x] 各クエリのEXPLAIN確認(合成データ34,000件、`hour_of_day_unique`(7日)13.9ms、`altitude_histogram`(24h)0.6ms、`speed_histogram`(720h)11.2ms — 720hはbearing/altitude-rangeと同じ理由でSeq Scanにフォールバックするが全期間の大半を占めるための正しい選択で、インデックス追加の根拠なし)。
- [x] CSV出力が実データで正しく開けることを確認した(Playwrightから`/api/traffic.csv?hours=24`をfetchし、`Content-Disposition: attachment`・ヘッダ行・1440件の分バケット行を確認)。
- [x] `make test`/`make lint`が通る(181件全green、lint/format clean)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone J（2A クイックウィン）
変更した主要ファイル:
  - app/db/queries/distribution.py（新規、hour_of_day_unique/altitude_histogram/speed_histogram）
  - app/api/routers/distribution.py（新規、GET /api/distribution/hour-of-day・altitude・speed）
  - app/api/routers/traffic.py（GET /api/traffic.csv追加、include_in_schema=False）
  - app/api/main.py（distributionルーター登録）
  - app/api/schemas.py（HourOfDay/Histogram系レスポンス追加）
  - app/static/js/chart.js（refreshTrafficが取得済みtraffic/nullを返すよう変更）
  - app/static/js/ui.js（setUniqueCount追加・export）
  - app/static/js/main.js（refreshTrafficAndCardラッパー、3つの新規チャート生成・fetch・resize配線）
  - app/static/js/api.js（getHourOfDay/getAltitudeHistogram/getSpeedHistogram追加）
  - app/static/index.html（CSVダウンロードリンク、distribution-areaセクション追加）
  - app/static/css/style.css（.panel__headerをflexに、.csv-link、.distribution-area追加、レスポンシブブレークポイント更新）
  - tests/integration/test_api.py（distribution 3エンドポイント+CSVの結合テスト、OpenAPI一覧更新）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、181件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - 使い捨てdocker postgresコンテナに合成データ(observations 34,000件、Milestone C-8/I と同規模)を投入し、3クエリ全てにEXPLAIN ANALYZEを実施。`hour_of_day_unique`(7日)13.9ms、`altitude_histogram`(24h)0.6ms、`speed_histogram`(720h)11.2ms。`speed_histogram`の720hはMilestone Iのbearing/altitude-rangeと同じ理由でSeq Scanにフォールバックするが、対象が全期間の大半を占めるための正しい選択であり関数インデックス追加の根拠なし。`GET /api/traffic.csv`が再利用する`get_traffic`の集計クエリ(168h)は既存のユニーク制約インデックスによるIndex Only Scanで2.0ms。
  - 使い捨てPostgres + 実uvicorn + Playwright Chromiumでダッシュボードを目視確認。`#card-unique`が実データ(79)を表示、CSVリンクから`/api/traffic.csv?hours=24`を実際にfetchしてContent-Disposition・ヘッダ行・1440件の分バケット行を確認、時間帯別/高度/速度の3ヒストグラムパネルとも描画。consoleメッセージはソフトウェアGLレンダラのパフォーマンス警告のみ(アプリコードとは無関係、地図・チャート描画自体は正常)。地図タイル(OpenFreeMap)はこのサンドボックス環境がインターネットに出られないため白紙表示だったが、これは既知の環境制約でありコード変更とは無関係。スクリーンショットで最終確認済み(セッション内一時ファイル、コミットせず)。
残課題:
  - daily.html/history.htmlは引き続き未作成のため、navの該当2リンクは404のまま(Milestone N/Oで解消予定、既知)。
次に行うTask: Milestone K（2C ヒートマップ）
ユーザー判断が必要な事項: なし
```

### Milestone K：2C ヒートマップ（スキーマ変更なし）

- [x] `app/db/queries/heatmap.py`を新規作成した: `grid_density(pool, hours, cell_deg=0.01, altitude_band=None, hour_of_day=None, day_of_week=None)` — `round(lat/cell_deg)*cell_deg, round(lon/cell_deg)*cell_deg`でグループ化。`MAX_GRID_CELLS`(5000件)の上限を`ORDER BY count DESC LIMIT`でサーバー側に強制(`tracks.py`の`MAX_TOTAL_POINTS`と同じ「密度の高いセルを優先して切り詰める」安全策、Milestone C-8で`hours=168`が1.18MBを返した失敗を繰り返さない)。
- [x] `app/api/routers/heatmap.py`を新規作成した: `GET /api/heatmap?hours=1..720&altitude_band=&hour_of_day=0..23&day_of_week=0..6`。不正な`altitude_band`値は422。`app/api/main.py`に登録した。
- [x] `map.js`を拡張し、既存ダッシュボード地図にヒートマップレイヤー(初期`visibility: none`)+トグルボタン+高度帯/時間帯/曜日フィルタを追加した(新規ページではない)。トグルはオプトインで、有効時のみ`/api/heatmap`を取得する(既定では追加クエリなし)。地図初期化失敗時の3種類のフォールバック(`{setTracks,resize,setHeatmap,setHeatmapVisible}`のno-op)にも`setHeatmap`/`setHeatmapVisible`を含め、既存の「地図障害時も他パネルは動作継続」契約を壊さないようにした。
- [x] テスト: `tests/integration/test_api.py`にフィルタ組み合わせを含む結合テスト(空/範囲外422/altitude_band不正値422/データあり+フィルタ一致・不一致)を追加、`test_openapi_lists_all_endpoints`更新。グリッド化計算はSQL側の`round(x/cell)*cell`一行のみで、Milestone I/Jと同様に意味のある純Pythonロジックがないため専用unit testは追加していない。`test_map_failure_playwright.py`の拡張は見送った — ヒートマップコントロールは地図read失敗時もno-opフォールバックで動作継続する設計そのものが検証対象であり、既存テストの「スタイルURL失敗」シナリオとは直交するため、既存テストへの追加より新規の目視確認(下記)で十分と判断。テスト総数181→184(+3)。

**Milestone K 完了条件**
- [x] Milestone C-8相当の合成データ量(observations 34,000件)で`EXPLAIN ANALYZE`を実施した。フィルタなし24h: 1.4ms(Bitmap Index Scan)。フィルタなし720h(全期間の大半): 12.4ms、実際に全データで16,766個の異なるグリッドセルが存在することを確認し、`MAX_GRID_CELLS=5000`の切り詰めが実際に発動することを検証した。altitude_band+hour_of_day+day_of_week全フィルタ組み合わせ(720h): 5.5ms。全てSeq Scan/Bitmap Scanのいずれかで、720hのSeq Scanは対象範囲が広いための正しい選択であり、`(round(lat,2), round(lon,2))`等の関数インデックスを追加する根拠はないと判断(先回りしない方針どおり)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone K（2C ヒートマップ）
変更した主要ファイル:
  - app/db/queries/heatmap.py（新規、grid_density。ORDER BY count DESC LIMIT MAX_GRID_CELLSで密度優先の切り詰め）
  - app/api/routers/heatmap.py（新規、GET /api/heatmap。不正altitude_bandを422に）
  - app/api/main.py（heatmapルーター登録）
  - app/api/schemas.py（GridCellResponse/HeatmapResponse追加）
  - app/static/js/map.js（heatmapソース+レイヤー追加、setHeatmap/setHeatmapVisible、3種のno-opフォールバックにも追加）
  - app/static/js/api.js（getHeatmap追加）
  - app/static/js/main.js（ヒートマップトグル+3フィルタselectの生成・配線、periodButtonsセレクタを.app-header__period配下に限定するバグ修正込み)
  - app/static/index.html（地図パネルヘッダーにヒートマップコントロール追加）
  - app/static/css/style.css（.heatmap-controls追加）
  - tests/integration/test_api.py（heatmap結合テスト、OpenAPI一覧更新）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、184件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - 使い捨てdocker postgresコンテナに合成データ(observations 34,000件)を投入し、フィルタなし(24h/720h)・全フィルタ組み合わせ(720h)にEXPLAIN ANALYZEを実施。720hのフィルタなしクエリでは実際に16,766個の異なるグリッドセルが存在し、`MAX_GRID_CELLS=5000`によるLIMIT切り詰めが本当に発動することを確認した(この規模で切り詰めが机上の空論でないことの実証)。
  - 使い捨てPostgres + 実uvicorn + Playwright Chromiumでダッシュボードを目視確認。高度帯(6)・時間帯(25)・曜日(8)の各セレクトが`/api/config`のaltitude_bandsおよび静的な0-23時/日-土から正しく生成されることを確認、ヒートマップトグルをクリックして`aria-pressed`がtrueに変わること、フィルタ変更後も再フェッチが例外なく走ることを確認。consoleメッセージはソフトウェアGLレンダラの性能警告のみ(アプリコードとは無関係)。スクリーンショットで最終確認済み(セッション内一時ファイル、コミットせず)。
  - Milestone Iのバグ修正付随発見: `.period-btn`クラスをヒートマップトグルボタンにも(スタイル共有目的で)付けたところ、既存の`document.querySelectorAll(".period-btn")`(航跡表示期間の1h/6h/24hボタン用)がヒートマップトグルまで拾ってしまい、クリック時に`currentTracksHours`が`NaN`になる実バグを実装中に発見・その場で修正(セレクタを`.app-header__period .period-btn`に限定)。
残課題:
  - daily.html/history.htmlは引き続き未作成のため、navの該当2リンクは404のまま(Milestone N/Oで解消予定、既知)。
  - スキーマ変更なし群(I/J/K)が完了。次はスキーマ変更を伴うMilestone L(M/N/Oの前提)。
次に行うTask: Milestone L（日次ロールアップ基盤）
ユーザー判断が必要な事項: なし
```

### Milestone L：日次ロールアップ基盤（スキーマ変更、M/N/Oの前提）

このMilestone単体でのユーザー向け機能はない。2A長期比較・2Dの30日超履歴・2Eの週比較が読むデータを、`observations`が保持期限で消える前に用意することが目的。

- [x] 新規migration(`5cee58fd601d`、`down_revision=62c3f8022564`)を追加した(`op.execute()`による生SQL、fix-forward方針を踏襲。使い捨てPostgresでupgrade→downgrade→re-upgradeが全て成功することを確認済み):
  - [x] `traffic_day(day PK, unique_aircraft_count, max_concurrent_count, message_count_total, position_aircraft_count_max, farthest_icao, farthest_distance_km, closest_icao, closest_distance_km, most_observed_icao, most_observed_count, computed_at)`
  - [x] `aircraft_day(icao, day, pass_count, observation_count, PK(icao,day))` + `ix_aircraft_day_day(day)`(Milestone Oの「直近N日で最頻」クエリのために先回りで追加、根拠明確なので許容)
  - [x] `aircraft_callsign_history(icao, callsign, first_seen_at, last_seen_at, PK(icao,callsign))`
- [x] JST日境界のヘルパーを`app/domain/daytime.py`に追加した: `day_bounds_utc(day, tz_name) -> (start_utc, end_utc)`(`zoneinfo`使用、Python側で計算しSQLの`AT TIME ZONE`に頼らない)、`today_in_tz`/`yesterday_in_tz`(ジョブの既定対象日計算・Milestone N用)。
- [x] `app/db/queries/period.py`を新規作成した:
  - [x] `compute_daily_summary(pool, day, start_utc, end_utc) -> DailyTrafficSummary`(plan記載の2引数`(pool, start_utc, end_utc)`に対し`day`を追加— `get_traffic_day`/`list_traffic_days`と同じ`DailyTrafficSummary`型が`day`フィールドを持つ必要があり、呼び出し側は既にどの日を計算しているか把握しているため自然な拡張と判断)。farthest/closestは`rankings.py`と同じ`ORDER BY distance_km {ASC,DESC} LIMIT 1`パターンを使用。
  - [x] `get_traffic_day(pool, day)` — 過去日は`traffic_day`から読む。
  - [x] `list_traffic_days(pool, start_day, end_day)` — ゼロ埋め、Milestone M用。
- [x] `app/dailyrollup.py`を新規作成した(`app/retention.py`の構造を踏襲): `--dry-run`、`--day YYYY-MM-DD`(手動バックフィル)、`--loop`(デーモン、JSTで既定00:10に実行、`next_run_at`ヘルパーで次回実行時刻を計算)。`pg_try_advisory_lock`は`retention.py`の`84372910`/`84372911`とは別の`84372950`を使用。対象日(既定: DISPLAY_TIMEZONEの昨日)について`traffic_day`・`aircraft_day`(`count_passes`によるギャップベースのpass分割、`MAX_PASS_GAP_SECONDS=120`、`tracks.py`のMAX_GAP_SECONDSと同種の手法)・`aircraft_callsign_history`を`ON CONFLICT ... DO UPDATE`で冪等に書き込む。`compute_daily_summary`がpool経由で独立に接続を取得するため、advisory lock保持用に`min_size=1,max_size=2`のプール(`retention.py`の`max_size=1`とは異なる)を使用。
- [x] 新規Composeサービス`adsb-daily-rollup`を追加した(`adsb-retention`のブロックと同形: `depends_on: adsb-migrate: service_completed_successfully`、`restart: unless-stopped`、`stop_grace_period`、ログ上限)。
- [x] `tests/contract/pg_container.py`の`clean_db`のTRUNCATE対象に新3テーブルを追加した。`scripts/db_status.py`のテーブル一覧も更新した。
- [x] テスト: `tests/contract/test_dailyrollup.py`(`test_retention.py`に倣う: 手計算値との一致・冪等性・dry-run・advisory lock競合・**「その日のロールアップ値がretention.pyによる同日observations削除後も残る」**ことを確認するテスト、計5件)。`tests/unit/test_daytime.py`(境界計算、JSTの無DST・比較用にDSTありタイムゾーンも1ケース検証)、`tests/unit/test_dailyrollup.py`(`count_passes`のpass分割、`next_run_at`のスケジューリング計算)。テスト総数184→202(+18)。

**Milestone L 完了条件**
- [x] 合成データで手計算した期待値とロールアップ結果が一致する(`test_run_rollup_writes_expected_values`: 2機体・パス数・callsign履歴・farthest/closest/most_observedを全て手計算値と照合)。
- [x] 同じ日を2回実行しても結果が変わらない(`test_run_rollup_is_idempotent`: `computed_at`以外の全カラムが一致、行数が増えないことを確認)。
- [x] retention実行後もロールアップ済みデータが残ることを確認するテストが通る(`test_rollup_survives_retention_deleting_the_day`)。
- [ ] **[ユーザー確認待ち]** 実`adsb-db`に対して`--dry-run`と実実行の両方を確認する — このセッションは実サーバーへのアクセス手段を持たないため未実施。migration適用(`docker compose up`で`adsb-migrate`経由)と`adsb-daily-rollup`サービスのデプロイはスキーマ変更・新規サービスであり、CLAUDE.md運用制約により実行前にユーザーへの提示が必要な変更として、コード提出のみに留め実施はユーザーに委ねる。

実測性能(このホスト上の使い捨てPostgres、Milestone C-8/I/J/K相当の合成データ 34,000件から抽出した1日分、約1,167 observations・約880機体):
- `compute_daily_summary`の各クエリ(unique/traffic_minute集計/farthest/closest/most_observed): 全て3ms未満。farthest/closestは`rankings.py`と同じ`ix_observations_distance_observed_at`のIndex Scanを使用することを確認。
- `run_rollup`のエンドツーエンド実行(880機体分の`aircraft_day`+`aircraft_callsign_history`個別upsert込み): 約9.2秒。1日1回のバッチジョブとして許容範囲と判断(1文ずつの逐次round-trip方式は本アプリ全体の「トランザクションを跨がない」既存方針に合わせたもので、将来`executemany`によるバッチ化の余地はあるが現時点では先回りの最適化をしない)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone L（日次ロールアップ基盤）
変更した主要ファイル:
  - migrations/versions/5cee58fd601d_add_daily_rollup_tables.py（新規、traffic_day/aircraft_day/aircraft_callsign_history）
  - app/domain/daytime.py（新規、day_bounds_utc/today_in_tz/yesterday_in_tz）
  - app/db/queries/period.py（新規、compute_daily_summary/get_traffic_day/list_traffic_days）
  - app/dailyrollup.py（新規、count_passes/next_run_at/run_rollup/CLI(--dry-run/--day/--loop)）
  - compose.yaml（adsb-daily-rollupサービス追加）
  - tests/contract/pg_container.py（clean_dbのTRUNCATE対象に新3テーブル追加）
  - scripts/db_status.py（_TABLESに新3テーブル追加）
  - tests/contract/test_dailyrollup.py（新規、5件）
  - tests/unit/test_daytime.py・tests/unit/test_dailyrollup.py（新規、計13件)
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、202件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - 使い捨てdocker postgresコンテナで新migrationの`upgrade head`→`downgrade 62c3f8022564`→再`upgrade head`が全て成功することを確認(fix-forward前提だが、空DBに対するdowngradeの安全性は62c3f8022564の前例に倣い検証)。
  - Milestone C-8/I/J/K相当の合成データ(observations 34,000件、30日分)から抽出した1日分(約1,167 observations、約880機体)で`compute_daily_summary`内の各クエリにEXPLAIN ANALYZEを実施。farthest/closestが`rankings.py`と同じ`ix_observations_distance_observed_at`のIndex Scanを使うことを確認(Backward/Forward、共に0.03ms未満)。他のクエリも全て3ms未満。
  - 同じ合成データに対して実際に`run_rollup`をエンドツーエンドで実行し、880機体分の`aircraft_day`+`aircraft_callsign_history`書き込みに約9.2秒かかることを実測(1日1回のバッチジョブとして許容範囲)。
  - `tests/contract/test_dailyrollup.py`で手計算値との一致・冪等性・dry-run・advisory lock競合・retention実行後の生存確認、全5件が実際の使い捨てPostgresに対して成功することを確認。
残課題(重要 — ユーザー確認・実施が必要):
  - **実`adsb-db`に対する`--dry-run`と実実行の確認が未実施**。このセッションはユーザーの実サーバーへのアクセス手段を持たない。ユーザー側で以下を実施いただく必要がある: (1) `docker compose up -d adsb-migrate`(または通常のcompose起動)でmigration `5cee58fd601d`を適用、(2) `docker compose run --rm adsb-daily-rollup python3 -m app.dailyrollup --dry-run`で実データに対する挙動を確認、(3) 問題なければ`docker compose up -d adsb-daily-rollup`でサービスを起動。migration適用・新規サービスのデプロイは実施前提示が必要な変更(CLAUDE.md運用制約)のため、コード提出のみに留めた。
  - daily.html/history.htmlは引き続き未作成のため、navの該当2リンクは404のまま(Milestone N/Oで解消予定、既知)。
次に行うTask: （ユーザーが実`adsb-db`での検証を実施した後)Milestone M（2A 長期比較）
ユーザー判断が必要な事項:
  - 上記の実`adsb-db`へのmigration適用・`adsb-daily-rollup`デプロイをいつ実施するか。
```

### Milestone M：2A 長期比較（Milestone L依存）

- [x] `GET /api/traffic/daily?days=1..365`(既定30) — `period.list_traffic_days`、ゼロ埋め。終端は「今日」ではなく「昨日」(`traffic_day`は確定済みの日のみ保持するため、今日を含めると常にゼロ埋めされた紛らわしい行になる)。
- [x] `GET /api/traffic/daily-summary?day=YYYY-MM-DD`(既定は今日) — 今日ならライブで`compute_daily_summary`、過去日なら`get_traffic_day`(ロールアップ未実施の直近日は生観測データがまだ残っているため、`traffic_day`に行がなければライブ計算にフォールバック)。未来日は422。比較専用エンドポイントは作らず、フロントエンドがこのエンドポイントを2回呼んで差分計算する(Milestone Nでも同じエンドポイントを再利用)。
- [x] 既存ダッシュボードのトラフィックパネルに日/週/月の粒度切替と、前日・先週同曜日比較の表示を追加した。実装のためMilestone Hの`createChart`ファクトリに`setBuildOption()`を追加(1つのチャートコンテナを分単位の折れ線⇔日単位の棒グラフで再利用するための一般化。`chart.setOption(..., true)`でnotMergeにし、形状切替時に旧シリーズ/軸設定が残らないようにした)。差分表示はサーバーの`day`値(DISPLAY_TIMEZONE基準)から日付演算するクライアント側ヘルパー`addDaysToIsoDate`を使用し、ブラウザのタイムゾーンには依存しない。

**Milestone M 完了条件**
- [x] 月表示が数MB級のペイロードにならないことを確認した(`days=365`で約101KB、実測してテストに組み込み済み — `test_traffic_daily_month_view_response_is_small`)。
- [x] 比較差分が手計算と一致する(Playwrightで実際に前日=20機・先週同曜日=10機・今日=30機とシードし、前日比+50%/先週同曜日比+200%が画面表示と一致することを確認)。
- [x] `test_openapi_lists_all_endpoints`更新。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone M（2A 長期比較）
変更した主要ファイル:
  - app/api/schemas.py（DailyTrafficSummaryResponse/TrafficDailyResponse追加）
  - app/api/routers/traffic.py（GET /api/traffic/daily・daily-summary追加）
  - app/static/js/chart.js（createChartにsetBuildOption追加、trafficChartOptionを独立export)
  - app/static/js/main.js（日/週/月トグル、前日比/先週同曜日比の差分表示、card-unique更新ロジックの分離)
  - app/static/js/api.js（getTrafficDaily/getTrafficDailySummary追加)
  - app/static/index.html（粒度トグル・差分表示要素追加)
  - app/static/css/style.css（.chart-controls/.granularity-controls/.traffic-deltas追加)
  - tests/integration/test_api.py（daily/daily-summary結合テスト8件、OpenAPI一覧更新）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、210件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - `traffic_day`に399件相当(実運用の現実的な上限規模)を投入しEXPLAIN ANALYZEを実施。`list_traffic_days`の範囲クエリはSeq Scanだが実行時間0.1ms — このテーブルは1日1行×長期保持でも数百〜数千行にしかならないため、Seq Scanが正しい選択であり索引追加の判断は不要と結論。
  - 使い捨てPostgres + 実uvicorn + Playwright Chromiumで実際に前日=20機・先週同曜日=10機・当日(ライブ計算)=30機をシードし、画面の差分表示が「前日比: +50%」「先週同曜日比: +200%」と手計算どおり表示されることを確認。日→週→月→日の粒度切替をクリックで実施し、チャートが分単位の折れ線(受信中/位置取得中の2系列)⇔日単位の棒グラフ(ユニーク機数1系列)に正しく切り替わること、consoleエラーがゼロであることを確認(スクリーンショット3枚で最終確認、セッション内一時ファイル・コミットせず)。今回はサンドボックスから実際にOpenFreeMapへの接続もでき、地図タイルも描画された。
残課題:
  - daily.html/history.htmlは引き続き未作成のため、navの該当2リンクは404のまま(Milestone N/Oで解消予定、既知)。
  - Milestone L由来の残課題(実`adsb-db`への migration適用・`adsb-daily-rollup`デプロイがユーザー確認待ち)は継続してオープン。Milestone M自体はスキーマ変更を伴わないため、この点はMの完了を妨げない。
次に行うTask: Milestone N（2E 今日の空 + webhook通知）
ユーザー判断が必要な事項: なし
```

### Milestone N：2E 今日の空 + webhook通知（Milestone L依存）

- [x] `app/static/daily.html` + `app/static/js/daily.js`を新規作成した(今日のライブサマリー、前日・先週同曜日との比較、最遠・最接近・最多観測)。navに追加済み(H で先行追加していたリンク先を実装、これで3/4ページが揃った)。
- [x] webhook通知(オプトイン、Slack/Discord互換): 環境変数`NOTIFY_WEBHOOK_URL`・`NOTIFY_WEBHOOK_ENABLED`(既定無効、未設定でも起動失敗しない。`app/config.py`に`model_validator`を追加し、有効化時にURL未設定なら明示的に起動失敗するようにした — 「無効なら何もしない」と「有効なのに設定不備」を区別)。`app/notify.py`を新規作成し、Slack互換の`{"text": "..."}`ペイロードで`DailyTrafficSummary`を要約(座標・秘密情報は含めない)、`httpx`で短いタイムアウト付きPOST、失敗時はログのみで継続。`app/dailyrollup.py`の`--loop`パスのみにトリガーを配線した(`--day`手動バックフィルでは発火しない — 任意の過去日を通知してしまう意図しないノイズを避けるため、plan文言の「前日ロールアップ完了直後」は毎日00:10頃の定期実行を指すと解釈)。
- [x] `.env.example`に新規環境変数をオプトインとして記載した。
- [x] テスト: `tests/unit/test_notify.py`(ペイロード形状・座標や秘密情報が含まれないこと・既定無効・成功時のペイロード内容・HTTPエラー応答での非送出・接続エラーでの非送出、計9件、`httpx.MockTransport`使用、実webhookは呼ばない)。`tests/unit/test_config.py`にNOTIFY_WEBHOOK系の新規バリデータのテストを4件追加。テスト総数210→223(+13)。

**Milestone N 完了条件**
- [x] webhook無効時、ロールアップの挙動が変化しない(`send_daily_notification`は`notify_webhook_enabled`チェックで即returnし、`run_rollup`本体には一切触れない)。
- [x] webhook有効時、モックサーバーに対して正しい形状のペイロードが1日1回送られる(`test_enabled_sends_expected_payload`で`httpx.MockTransport`により送信先URL・JSON本文を検証。「1日1回」は`_run_loop`の日次スケジューリング — Milestone Lで検証済みの`next_run_at` — により保証される)。
- [x] ページが実データで表示される(使い捨てPostgres + 実uvicorn + Playwright Chromiumで`/static/daily.html`を目視確認。ユニーク機数・最遠/最接近・前日比/先週同曜日比が実データと一致することを確認、consoleエラーなし)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone N（2E 今日の空 + webhook通知）
変更した主要ファイル:
  - app/config.py（notify_webhook_enabled/notify_webhook_url追加、URL形式バリデータ、有効化時のURL必須model_validator）
  - app/notify.py（新規、build_payload/send_daily_notification。テスト用にhttpx.AsyncClientを差し替え可能な設計）
  - app/dailyrollup.py（_run_loopのみに通知トリガーを配線、--dayバックフィルでは発火しない）
  - app/static/daily.html・app/static/js/daily.js（新規ページ）
  - app/static/css/style.css（.daily-highlight系スタイル追加）
  - .env.example（NOTIFY_WEBHOOK_ENABLED/NOTIFY_WEBHOOK_URL追加）
  - tests/unit/test_notify.py（新規、9件）
  - tests/unit/test_config.py（NOTIFY_WEBHOOK系バリデータのテスト4件追加）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、223件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - `httpx.MockTransport`を使い、webhook無効時に一切HTTPリクエストが発生しないこと(呼ばれたら即失敗するモック)、有効時に送信先URL・JSON本文(`build_payload`の出力と一致)を検証、HTTPエラー応答(500)・接続エラーの両方で例外が外に漏れないことを確認。
  - 使い捨てPostgres + 実uvicorn + Playwright Chromiumで`/static/daily.html`を目視確認。2機体(最遠310.4km・最接近4.2km)をシードし、カード表示・最遠/最接近ハイライト・前日比(-33%)/先週同曜日比(+100%)が手計算と一致することを確認。consoleエラーはゼロ(このページは地図/チャートを使わないため、他ページで出ていたWebGL関連の警告すら出ない)。
  - 目視確認中、シードスクリプト側の不備(同一icaoに同一observed_atで複数回insert_observationを呼び、`(icao, observed_at)`のUNIQUE制約によりupsertで1行に収束してしまい、意図した「3件観測」が実際には1件だった)により最多観測の表示値が意図と異なる結果になったが、これはテストスクリプトのバグでありアプリ側のロジックの問題ではないと判断(該当ロジックはMilestone Lの`test_run_rollup_writes_expected_values`で異なるタイムスタンプの観測データを使い正しく検証済み)。
残課題:
  - history.htmlのみ引き続き未作成のため、navの該当1リンクは404のまま(Milestone Oで解消予定、既知)。
  - Milestone L由来の「実adsb-dbへのmigration適用・adsb-daily-rollupデプロイ」はユーザー確認待ちのまま継続。webhookを実際に有効化して本番運用する場合も、このデプロイ後に`.env`へ`NOTIFY_WEBHOOK_ENABLED`/`NOTIFY_WEBHOOK_URL`を設定する対応が別途必要(オプトインのため未設定なら何も変わらない)。
次に行うTask: Milestone O（2D 機体の再訪履歴）
ユーザー判断が必要な事項: なし
```

### Milestone O：2D 機体の再訪履歴（Milestone L依存）

- [x] `app/db/queries/aircraft_history.py`を新規作成した: `aircraft_summary(pool, icao)`(`aircraft`の永年データ+`aircraft_day`の集計)、`callsign_history(pool, icao)`、`most_frequent(pool, days=1..365, limit=1..100)`(`ix_aircraft_day_day`を利用)。
- [x] `app/api/routers/aircraft_history.py`を新規作成した: `GET /api/aircraft/{icao}/history`(既存のDB CHECK制約`aircraft_icao_format`と同じ正規表現`^~?[0-9a-f]{6}$`で形式検証→422、不明ICAOは404、このAPI初のpathパラメータ404だがGETのみで新たな懸念は生まない)、`GET /api/aircraft/frequent?days=&limit=`。`app/api/main.py`に登録した。
- [x] `app/static/history.html` + `app/static/js/history.js`を新規作成した: 最頻観測ランキング(`ui.js`の`renderRankingTable`を再利用 — `addCell`をDOMノードも受け付けるよう一般化し、お気に入り星ボタンをセルとして描画できるようにした)、`?icao=`で機体詳細、callsign履歴。**お気に入り機体はブラウザ`localStorage`のみで実装し、バックエンドの書き込みエンドポイントは追加していない**(このAPI初の書き込み経路にしないため)。navに追加した(これで4/4ページが揃った)。
- [x] テスト: `tests/integration/test_api.py`に404ケース・形式不正422・データありの結合テスト6件を追加、`test_openapi_lists_all_endpoints`更新。集計はSQL側で完結し意味のある純Pythonロジックがないため、Milestone I/Jと同様に専用unit testファイルは追加していない。テスト総数223→229(+6)。

**Milestone O 完了条件**
- [x] 複数日にわたる合成データを持つ機体で、観測日数・pass数・callsign履歴が正しく表示される(結合テストで手計算値と照合、Playwrightでも5日分のシードデータで目視確認)。
- [x] お気に入りがページ再読み込み後も`localStorage`経由で保持される(Playwrightで実際に星をクリック→`aria-pressed=true`→ページreload→`aria-pressed=true`のまま、を確認)。
- [x] `make test`/`make lint`が通る(229件全green、lint/format clean)。

### セッション記録

```text
日付: 2026-07-29
完了したMilestone/Task: Milestone O（2D 機体の再訪履歴）— これでPhase 2 Milestone H〜Oが全て完了
変更した主要ファイル:
  - app/db/queries/aircraft_history.py（新規、aircraft_summary/callsign_history/most_frequent）
  - app/api/routers/aircraft_history.py（新規、GET /api/aircraft/{icao}/history・/api/aircraft/frequent）
  - app/api/main.py（aircraft_historyルーター登録）
  - app/api/schemas.py（AircraftHistoryResponse/FrequentAircraftResponse等追加）
  - app/static/js/ui.js（renderRankingTableをbuildRowコールバック方式に一般化、addCellがDOMノードも受理するよう拡張、distanceRankingRowを既存呼び出し元に適用、renderRankingTableをexport）
  - app/static/history.html・app/static/js/history.js（新規ページ。最頻観測ランキング+お気に入りフィルタ、?icao=機体詳細、callsign履歴。お気に入りはlocalStorageのみ）
  - app/static/css/style.css（.favorite-toggle/.detail-title-row/.callsign-history-list等追加）
  - tests/integration/test_api.py（aircraft history結合テスト6件、OpenAPI一覧更新）
  - PLAN.md（本セクション）
実行したテスト: pytest（フルスイート、229件）、ruff check / ruff format --check
テスト結果: 全green、lint/format clean
実環境で確認したこと:
  - `aircraft_day`に実運用の複数年規模(2,000機体×365日分サンプリング、63,779行)相当の合成データを投入し、`most_frequent`にEXPLAIN ANALYZEを実施。狙いどおり`ix_aircraft_day_day`のIndex Scanが使われていることを確認(3.6ms)。`aircraft_summary`の単一機体集計は主キー経由のBitmap Index Scanで0.16ms。
  - 使い捨てPostgres + 実uvicorn + Playwright Chromiumで`/static/history.html`を目視確認。5機体(観測日数5〜1日で意図的に差をつけた合成データ)のランキングが正しい順序で表示されること、お気に入り星をクリック→`aria-pressed`がtrueに変化→ページ再読み込み後も`localStorage`経由で状態が保持されること(完了条件の核心)、お気に入りのみフィルタで1件に絞り込まれること、`?icao=`機体詳細ビューで初観測/最終観測/観測日数/総パス数/callsign履歴が正しく表示されること、不明ICAOで「機体が見つかりません」表示になることを確認。スクリーンショット2枚で最終確認済み(セッション内一時ファイル、コミットせず)。
残課題:
  - 全4ページ(ダッシュボード/受信性能/今日の空/機体履歴)が揃い、navの404リンクは解消済み。
  - **Milestone L由来の残課題が唯一未解決のまま**: 実`adsb-db`への migration `5cee58fd601d`適用と`adsb-daily-rollup`サービスのデプロイがユーザー確認待ち。これが完了するまで、M/N/Oが依存する`traffic_day`/`aircraft_day`/`aircraft_callsign_history`は本番環境では空のまま(コード自体は正しく空データを処理してゼロ表示するため、本番でエラーにはならないが機能として無意味な状態が続く)。
  - Phase 2の6候補中、2F(地図セルフホスト)のみ意図的に対象外(冒頭の設計判断を参照)。
次に行うTask: なし(Phase 2 Milestone H〜O完了)。次のアクションはユーザーによる実adsb-dbへのデプロイ、またはPhase 3の計画。
ユーザー判断が必要な事項:
  - Milestone Lのmigration適用・adsb-daily-rollupデプロイをいつ実施するか(繰り返し、CLAUDE.md運用制約により実行前提示が必要)。
  - 2F(地図セルフホスト)や新たなPhase 3候補に進むかどうか。
```

### 実行上の注意

- Milestone Hより前(Step 0)として、この§16をA〜G同様の構造でPLAN.mdへ追加する作業自体が完了している(このセッションで実施)。各Milestone完了時は引き続き§15形式のセッション記録を追記する。
- 推奨コミット粒度(Milestone単位): `ui: add chart factory and shared nav` / `api: add receiver performance queries and endpoints` / `api+ui: add period quick-wins and CSV export` / `api+ui: add heatmap` / `db: add daily rollup schema and job` / `api+ui: add long-horizon traffic comparison` / `ui+notify: add daily report page and webhook` / `api+ui: add aircraft revisit history`。
- 推奨順序はH→I→J→K→L→M→N→O。I/J/Kはスキーマ変更を伴わず相互に独立のため優先度に応じて入れ替え可。LはM/N/Oの前提。

### セッション記録

```text
日付: 2026-07-28
完了したMilestone/Task: Phase 2 Step 0（§16追加）、Milestone H（チャートファクトリと共通ナビゲーション）
変更した主要ファイル:
  - PLAN.md（§16 Phase 2詳細実装計画を新規追加）
  - app/static/js/chart.js（createChart(containerId, errorElId, buildOption)ファクトリを抽出、createTrafficChartをその最初の呼び出し元に変更。{setData,resize}の外部契約は不変）
  - app/static/index.html（共通<nav class="app-nav">追加、aria-current="page"でアクティブページ表示）
  - app/static/css/style.css（.app-nav用スタイル追加）
実行したテスト: pytest（フルスイート）、ruff check
テスト結果: 158件全green、lint clean
実環境で確認したこと:
  - **[今回のセッションで新たに実施]** Playwright + 使い捨てPostgresコンテナ + 実uvicornサーバーで、実ブラウザ(Chromium)によるダッシュボードの目視・console error確認を実施した(一時テストファイルとして作成し、確認後に削除)。これまでのセッション記録で繰り返し「ブラウザ環境がなく目視確認ができない」と記録されていたが、`tests/integration/test_map_failure_playwright.py`と同じ手法(disposable Postgres + 実uvicorn + Playwright Chromium)がこの環境で実際に動作することを確認した。今後のフロントエンド変更でも同様の手法で目視確認が可能。
  - **[今回の点検で発見・修正]** `.panel__error`のCSSに`display: flex`が無条件に指定されており、`[hidden]`属性のUAデフォルト`display: none`と詳細度が同点のため、著者スタイルが優先されて`hidden`が事実上無視されていた。この結果、`#chart-error`と`#map-error`が常時(エラーが無い状態でも)半透明の赤枠オーバーレイとして地図・グラフパネルの上に表示される、本番環境にも存在していたはずの表示バグを発見した。`.panel__error[hidden] { display: none; }`を追加して修正し、Playwrightで`hidden`時に正しく非表示になることを確認した。Milestone D以降のセッション記録に残っていた「ブラウザ目視確認未実施」のリスクが実際に顕在化した実例。
  - 修正後、Chromiumで実際にダッシュボードをスクリーンショット確認: ナビゲーション4リンク表示・アクティブページハイライト・地図(MapLibre)・交通量チャート・ランキングテーブルが正しく描画され、console errorはゼロ。
残課題:
  - `#card-unique`(24時間ユニーク機数)は引き続き未配線(Milestone Jで対応予定、想定通り)。
  - receiver.html/daily.html/history.html未作成のため、navの3リンクは現時点で404になる(該当Milestone作成時に解消)。
次に行うTask: Milestone I（2B 受信局性能）
ユーザー判断が必要な事項: なし
```

## 17. ダッシュボードフィードバック対応（Milestone P〜U）

ユーザーが実運用中のダッシュボードを実際に使った上でのフィードバック(改善2件+新機能6件)を受けて追加した一連の作業。着手前に各項目をコードベースに即して検討し、ユーザーと議論(AskUserQuestion)した上で計画を確定した。主な設計判断:

- **更新頻度**: 収集側の実際の更新周期(`POLL_INTERVAL_SECONDS`=5秒)より速くしても意味がないことを確認した上で、10秒→5秒に変更(3秒は無駄と判断)。
- **機体写真・機種情報**: 当初計画していた「tar1090-dbのようなオフライン一括データベースを同梱する」方式は断念した。`wiedehopf/tar1090-db`はGitHub API上でライセンスファイルが存在しない(`license: None`)ことを確認し、代替候補のOpenSky Network機体データベースもOpenSky自身が"unlicensed"と明記しており、どちらも再配布に適さないと判断。ユーザーと相談の上、`api.adsbdb.com`(登録記号・機種)と`api.planespotters.net`(写真)への**クリック時のみのライブ問い合わせ**方式に変更した(両APIとも実際に生きていることをWebFetchで事前確認済み)。
- **今日のTop10機種チャートだけは例外**: 1日分の全機体を集計する必要があり、クリック時問い合わせ方式では実現できないため、ユーザーと相談の上「初めて見た機体につき1回だけサーバー側がadsbdb.comに問い合わせ、結果を永続キャッシュする」方式(`aircraft_type_cache`)を採用。読み取りパス(`GET /api/distribution/aircraft-type`)は完全にオフラインのまま。
- **生データ/簡易デコードタブ**: `CLAUDE.md`の既存スコープ外(Raw Beast/Mode-S非対応)と明確に矛盾するが、ユーザーの明示的な依頼により追加。表示専用・DB保存なし・簡易デコード(DF/ICAO24/CA/ADS-B TCカテゴリのみ、CPR位置/速度は非対応)に限定してスコープを絞り、`CLAUDE.md`の out-of-scope 記述を実態に合わせて修正した。
- **受信性能の3D化**: `echarts-gl`(BSD-3-Clause、ベンダリング前にライセンス確認済み)を新規採用。

### Milestone P：UIクイックウィン(スキーマ変更・新規依存なし)

- [x] 地図ホバーポップアップの文字色: ダークテーマの`--text`(ほぼ白)がMapLibreの白背景ポップアップに継承され読めなくなっていたバグを`style.css`の`.maplibregl-popup-content`スコープ指定で修正。
- [x] ダッシュボード更新間隔: `app/static/js/ui.js`の`REFRESH_INTERVAL_MS`を10000→5000に変更。
- [x] フルスクリーン地図ページ: `app/static/fullmap.html` + `app/static/js/fullmap.js`を新規作成、`map.js`の既存`createTrackMap`/`refreshTracks`をそのまま再利用。全ページのnavに追加。
- [x] 距離別RSSIヒートマップ: `app/db/queries/receiver.py`に`rssi_by_distance()`追加、`GET /api/receiver/rssi-by-distance`新設、`receiver.html`/`receiver.js`にECharts heatmapパネル追加。
- [x] テスト: `tests/integration/test_api.py`にrssi-by-distanceの空/bounds/シード済みテスト追加。全234件green。

### Milestone Q：機体情報・写真ポップアップ(④⑤、当初計画のQ+Rを統合)

オフラインDBのライセンス問題により当初計画から設計変更(上記参照)。

- [x] `app/static/js/aircraftinfo.js`を新規作成: `createAircraftInfoTrigger(icao, label)`が、クリック時のみ`api.adsbdb.com`(登録記号/機種/製造者)と`api.planespotters.net`(サムネイル+撮影者クレジット+リンク)へ並行して問い合わせ、結果をトグルパネルに描画するボタンを返す。自動プリフェッチなし、サーバー側キャッシュなし。
- [x] `history.js`(機体詳細)・`ui.js`(ダッシュボードのランキング/最近観測テーブルの機体セル)・`daily.js`(今日の空のハイライトタイル)に組み込んだ。
- [x] **今回の点検で発見・修正**: `ui.js`のランキング/最近観測テーブルはPミルストーンで5秒ポーリングに変更済みのため、開いた情報パネルが5秒ごとの再描画で消えてしまうバグを実装中に発見。`aircraftinfo.js`に開いているパネル数を追跡する`isAnyAircraftInfoPanelOpen()`を追加し、`ui.js`側でパネルが開いている間はテーブル再描画をスキップするよう修正。
- [x] READMEのSecurity & Privacy節を更新し、「呼び出し先なし」の主張に2つの明示的な例外(クリック時のみ)があることを明記。

### Milestone S：今日のTop10機種チャート(⑥)

Milestone Qのクリック方式では1日分の集計ができないため、ユーザーと協議の上サーバー側の永続キャッシュ方式を採用。

- [x] 新規migration(`d6494c2713c8`): `aircraft_type_cache(icao PK, type_code, type_name, manufacturer, registration, lookup_failed, looked_up_at)`。
- [x] `app/aircraft_lookup.py`新規作成: `refresh_uncached_aircraft_types()`が、まだキャッシュにない機体(または30日以上前に失敗した機体)を`api.adsbdb.com`に問い合わせ、成功/失敗の両方を永続的にキャッシュする(失敗した検索を毎回再試行しないため)。`app/dailyrollup.py`の`--loop`サイクルに組み込み、ロールアップ本体・webhookとは独立したtry/exceptで失敗を隔離。
- [x] `app/db/queries/aircraft_type.py` + `GET /api/distribution/aircraft-type?day=&limit=`: `aircraft_type_cache`は日付を持たないため、`traffic/daily-summary`と同様「対象日はobservationsから都度計算」という単一のクエリ形状で今日・過去日の両方に対応。
- [x] `daily.html`/`daily.js`にチャート追加、キャッシュが空の場合は明示的な空状態メッセージを表示(エラーにしない)。
- [x] テスト: `tests/contract/test_aircraft_lookup.py`(httpx.MockTransportで7ケース、実DB使用)、`tests/integration/test_api.py`に5ケース追加。
- [x] 実機体3件(JA218A/A320、HL8015/B738、JA614A/B767)で実際に`adsbdb.com`へ問い合わせてキャッシュへの書き込みとチャートAPIへの反映を実環境で確認済み。

### Milestone T：生データ・簡易デコードタブ(⑦、CLAUDE.mdの既存スコープ外だがユーザー依頼により追加)

- [x] `app/domain/beast.py`新規作成: Beastバイナリフォーマットのパース(バイトスタッフィング処理、TCPの分割読み込みに対応)と簡易デコード(DF/ICAO24/CA、DF17/18のTCカテゴリラベル)。単体テスト14件に加え、実機の30005番ポートから直接キャプチャした実データでも検証した。
- [x] `app/api/routers/rawdata.py`: `WS /ws/rawdata`。ブラウザ接続ごとにreadsbのBeastポートへ個別にTCP接続(Beastサーバーは複数同時読者を前提に設計されているため、共有ファンアウトハブは過剰と判断)。DBには一切書き込まない。
- [x] `READSB_BEAST_HOST`/`READSB_BEAST_PORT`設定を追加(`READSB_AIRCRAFT_URL`のホスト名から自動導出)。空文字列が`Settings()`をクラッシュさせないことをテストで確認(NOTIFY_WEBHOOK_URLと同じ落とし穴)。
- [x] `app/static/rawdata.html` + `js/rawdata.js`: 最大500件・一時停止/クリア・自動再接続。全ページのnavに追加。
- [x] `CLAUDE.md`の out-of-scope 記述を、実態(表示専用・簡易デコードのみは対象内、保存・本格デコードは引き続き対象外)に合わせて修正。
- [x] **今回の点検で発見・修正**: `compose.yaml`で`adsb-api`に`extra_hosts: host.docker.internal:host-gateway`が設定されておらず(これまで`adsb-collector`のみに設定)、実際にWebSocketクライアントで接続するまで気づかなかった接続失敗を発見・修正。
- [x] 実際のWebSocketクライアント(`websockets`ライブラリ)で本番環境に接続し、DF11/DF17/DF0の実フレームが正しくデコードされて配信されることを確認済み。

### Milestone U：受信性能3D半球表示(⑧-a)

- [x] `app/db/queries/receiver.py`に`bearing_elevation_range()`追加: 既存の方位セクター分割に仰角帯(0-90度を10度刻み9帯)を追加した2次元ビニング。`GET /api/receiver/bearing-elevation-range`新設。
- [x] `echarts-gl@2.0.9`(BSD-3-Clause、ベンダリング前にGitHub APIでライセンス確認)を`app/static/js/vendor/echarts-gl/`に配置。
- [x] **実ブラウザ検証で発見・解決した問題が2つ**:
  1. echarts-gl公式ドキュメントは「ECharts 5.x系のみ対応」と明記しているが、本リポジトリは6.1.0を同梱済み。ドキュメントを鵜呑みにせずPlaywrightで実際に組み合わせて検証した結果、正常に動作することを確認してから採用した。
  2. 実データ+visualMapで実際にチャートを描画すると、echarts-glのシェーダー内部コンパイラが"Invalid expression"で例外を投げる不具合を発見。scratchpad上で最小再現ケースを作り、原因が本アプリの厳格なCSP(`script-src 'self'`、`unsafe-eval`なし)であることを特定。`receiver.html`のCSPにのみ`'unsafe-eval'`を追加して解決し(他の全ページは変更なし)、READMEのSecurity & Privacy節にトレードオフとして明記した。
- [x] 実際の本番データ(118セル)でPlaywrightからスクリーンショットを取得し、正しく3D散布図が描画され console error がゼロであることを確認済み。

### セッション記録

```text
日付: 2026-07-30
完了したMilestone/Task: Milestone P〜U(ダッシュボードフィードバック対応、全6件)
変更した主要ファイル:
  - Milestone P: app/static/css/style.css, app/static/js/ui.js, app/static/fullmap.html(新規), app/static/js/fullmap.js(新規), app/db/queries/receiver.py, app/api/schemas.py, app/api/routers/receiver.py, app/static/receiver.html, app/static/js/api.js, app/static/js/receiver.js
  - Milestone Q: app/static/js/aircraftinfo.js(新規), app/static/js/history.js, app/static/js/ui.js, app/static/js/daily.js, README.md
  - Milestone S: migrations/versions/d6494c2713c8_add_aircraft_type_cache.py(新規), app/aircraft_lookup.py(新規), app/dailyrollup.py, app/db/queries/aircraft_type.py(新規), app/api/routers/distribution.py, app/api/schemas.py, app/static/daily.html, app/static/js/api.js, app/static/js/daily.js
  - Milestone T: app/domain/beast.py(新規), app/api/routers/rawdata.py(新規), app/config.py, app/api/main.py, app/static/rawdata.html(新規), app/static/js/rawdata.js(新規), compose.yaml, CLAUDE.md, 全ページのnav
  - Milestone U: app/db/queries/receiver.py, app/api/schemas.py, app/api/routers/receiver.py, app/static/js/api.js, app/static/js/receiver.js, app/static/receiver.html, app/static/js/vendor/echarts-gl/echarts-gl.min.js(新規)
  - 共通: README.md(全マイルストーンで機能・設定・Security & Privacy節を都度更新), .env.example
実行したテスト: pytest(フルスイート、234→271件、+37)、ruff check
テスト結果: 全green、lint clean
実環境で確認したこと:
  - 各マイルストーンごとに`docker compose build`/`up -d --force-recreate`で本番デプロイし、curl/実WebSocketクライアント/Playwright(実Chromium)で目視・動作確認した(セッション内の一連の作業として、都度)。
  - 実環境検証で3件の実バグを発見・修正(コードだけでは見つからなかったもの): (1) Milestone Qでui.jsの5秒ポーリングが開いた情報パネルを消してしまう競合、(2) Milestone Tでcompose.yamlのadsb-apiにhost.docker.internal解決用のextra_hostsが不足、(3) Milestone Uでecharts-glのCSP(unsafe-eval)要件。
  - Milestone Sは実機体3件、Milestone Tは実Beastフレーム、Milestone Uは実受信データ118セルで、それぞれ本番のreadsb/adsbdb.com/DBを使った検証を実施。
残課題:
  - なし(6マイルストーン全て完了・デプロイ・検証済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 18. tar1090風サイドバー + リアルタイム3D航跡(Milestone V〜W)

ダッシュボード利用後のユーザーからの追加フィードバック2件(4.機体情報をtar1090風の左サイドバーに、8.受信範囲3D半球とは別に、地球儀を遠くから操作する感覚のリアルタイム3D航跡タブを新設)を受けて実施。着手前にコードベースを調査した上でユーザーと議論(AskUserQuestion)し、以下を決定:

- **サイドバーの情報深度**: tar1090はスコーク・NAC/SIL/NIC精度指標・FMS選択高度/方位・風向風速・TAT/OAT・マッハ・磁方位などを表示しているが、`observations`テーブルにはこれらが一切ない(確認済み)。ユーザーは「readsbへのライブ問い合わせを追加する」方式(B)を選択 — 選択中の1機体に限定した、意図的かつ narrow なリアルタイム例外として扱う。
- **3D実装方式**: 既に導入済みのecharts-glの`globe`コンポーネントは地球全体に1枚のテクスチャを貼る仕様で、受信局周辺だけの精細な衛星画像には不向きと判明。ユーザーはCesiumJS(Apache-2.0、npm packageの`Build/Cesium/`がビルド不要の即利用可能な配布物であることを確認済み)の新規導入を選択。
- **衛星画像ソース**: ArcGIS World Imagery。「ArcGIS Onlineライセンスが必要」という矛盾する二次情報があったが、curlで実際に無認証・無キーでHTTP 200 + 実JPEGタイル + `Access-Control-Allow-Origin: *`が返ることを直接確認し採用。表示中は常時通信(クリック時のみではない)することをユーザーが承認。
- **3D空間内の軌跡範囲**: 過去履歴(既存`/api/tracks`相当のデータをこの1機体用に取得)+ タブを開いてからのリアルタイム更新の両方。

### Milestone V:ライブ機体データ基盤 + tar1090風サイドバー

- [x] `WS /ws/aircraft/{icao}`(`app/api/routers/aircraft_live.py`新規)を追加: readsbを収集側と同じ周期で独立ポーリングし、該当機体のみフィルタして、`observations`に無いtar1090相当フィールド(スコーク、NAC/SIL/NIC、FMS選択値、風、マッハ等)+ `lat`/`lon`(生の5秒周期、3D航跡のライブマーカー用)をプッシュ。DB保存なし。
- [x] `app/db/queries/tracks.py`に`get_aircraft_track()`追加(既存`_build_track`のギャップ分割ロジックを1機体用に再利用)、`GET /api/aircraft/{icao}/positions?hours=`新設。
- [x] `app/db/queries/aircraft_history.py`に`latest_observation()`追加、`GET /api/aircraft/{icao}/history`のレスポンスに自局の最新観測(高度・速度・距離・RSSI等)を含めるよう拡張。
- [x] `app/static/js/aircraftinfo.js`を全面刷新: クリックした要素直下のトグルパネル方式から、`document.body`に遅延生成する単一の共有左サイドバー方式に変更。`createAircraftInfoTrigger(icao, label)`のシグネチャは不変のため、`history.js`/`ui.js`/`daily.js`は無変更で動作。
- [x] **実ブラウザ検証で発見・修正した既存バグ(Milestone Q由来)**: Planespotters.netの`/pub/`写真APIが「連絡先付きの説明的なUser-Agent」を要求するようになっており、ブラウザの`fetch()`はUser-Agentを上書きできない(禁止ヘッダー)ため、直接ブラウザから呼ぶ方式は全ユーザーにとって無言で機能しない状態だった。ユーザーと相談の上、`GET /api/aircraft/{icao}/photo`としてサーバー側プロキシ化(適切なUser-Agentを付与)して解決。adsbdb.com側にも同じUser-Agentを追加(既存動作への実害はないが行儀の良い対応として)。
- [x] `CLAUDE.md`の「リアルタイム追跡はしない」を、選択中の1機体に限定した2つの意図的な例外(生データWS、機体ライブWS)として明記するよう修正。
- [x] テスト: `tests/unit/test_aircraft_photo.py`(新規、httpx.MockTransportで4ケース)、`tests/integration/test_api.py`に positions/photo/history拡張分のテスト追加。全282件green。
- [x] 実環境で実際のWebSocketクライアントから複数機体のライブデータ(スコーク・NAC・FMS選択値・マッハ等)を確認、Playwrightで実際のサイドバー(写真含む)をスクリーンショットしconsole errorゼロを確認。

### Milestone W:3D航跡タブ(CesiumJS)

- [x] CesiumJS 1.143.0(Apache-2.0、GitHub/npmで確認済み)のnpm tarballから`Build/Cesium/`(23MB、392ファイル)を抽出し`app/static/js/vendor/cesium/`に配置(ビルド不要)。
- [x] `app/static/globe.html` + `app/static/js/globe.js`新規作成: 機体セレクタ(`/api/aircraft/recent`から生成)、選択時に`/api/aircraft/{icao}/positions`で過去軌跡を3Dポリラインとして即座に描画、`WS /ws/aircraft/{icao}`(Milestone Vと共有)でライブ位置マーカーを更新し続ける。地面はArcGIS World Imagery。
- [x] **実ブラウザ検証で発見・解決した問題が2つ**:
  1. CesiumJS自身のスクリプトが地形/画像デコード用にWebAssemblyを即座にコンパイルしようとし、CSPの`script-src`に`'unsafe-eval'`が無いとCesiumのトップレベルスクリプトが実行途中で例外を投げ、`window.Cesium`自体が未定義のままになる(receiver.htmlのecharts-gl問題と同種だが別ページ固有)。
  2. Cesiumはweb workerをblob:スクリプト経由でブートストラップしており、そのworker内の`importScripts()`が`script-src`に`blob:`が無いとブロックされる(`worker-src`だけでは不十分 — worker自体の生成元は制御するが、worker内から`importScripts()`で読み込むスクリプトは対象外)。
  globe.htmlのCSPにのみ`'unsafe-eval' blob:`を追加して解決(他ページは無変更)。
- [x] 実環境で実際に機体を選択し、過去軌跡(シアン色の線)とライブ更新中の現在位置マーカー(軌跡の終端より先に進んでいることを確認 = ライブ更新が実際に機能している証拠)を実際の衛星画像上でPlaywrightスクリーンショットにより確認。選択→切替→解除でconsole/page errorゼロ。
- [x] README/CLAUDE.mdを更新(3D航跡ページの説明、CesiumJS/ArcGIS衛星画像の常時通信に関するSecurity & Privacy追記)。

### セッション記録

```text
日付: 2026-07-30
完了したMilestone/Task: Milestone V(tar1090風サイドバー + ライブ機体データ)、Milestone W(3D航跡タブ、CesiumJS)
変更した主要ファイル:
  - Milestone V: app/api/routers/aircraft_live.py(新規)、app/db/queries/tracks.py、app/db/queries/aircraft_history.py、app/api/routers/aircraft_history.py、app/api/schemas.py、app/api/main.py、app/static/js/aircraftinfo.js(全面刷新)、app/static/js/api.js、app/version.py、app/aircraft_lookup.py、app/static/css/style.css、CLAUDE.md、README.md
  - Milestone W: app/static/globe.html(新規)、app/static/js/globe.js(新規)、app/static/js/cesium-base-url.js(新規)、app/static/js/vendor/cesium/(新規、392ファイル)、app/api/routers/aircraft_live.py(lat/lon追加)、全ページのnav、README.md
実行したテスト: pytest(フルスイート、271→282件)、ruff check
テスト結果: 全green、lint clean
実環境で確認したこと:
  - Milestone V: 実WebSocketクライアントで複数の実機体からライブデータ(スコーク7055・マッハ0.688・NAC/SIL等)を受信確認。Playwrightで実サイドバー(写真付き)をスクリーンショット、console/page errorゼロ。
  - Milestone Qの写真機能が実は全ユーザーに対して無言で壊れていたことを実ブラウザテストで発見(Planespotters.netのUser-Agentポリシー変更)。サーバー側プロキシ化で修正し、実際に写真が表示されることを確認。
  - Milestone W: echarts-gl(Milestone U)の時と同様、ドキュメント記載を鵜呑みにせず実際に検証する姿勢で2つの実バグ(CSPのunsafe-eval不足、blob:不足)を発見・修正。最終的に実データで軌跡+ライブマーカーの3D描画を確認。
残課題:
  - なし(両マイルストーン完了・デプロイ・検証済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 19. バグ修正 + 単位設定 + マルチ機体3D航跡(Milestone X〜Z)

Milestone V〜W(tar1090風サイドバー + 3D航跡)を実際に使ったユーザーからの追加フィードバック(バグ5件 + 新機能案2件)を受けて実施。着手前に問題を実際に再現・根本原因を特定した上でユーザーと議論(AskUserQuestion)し、以下を決定:

- **言語選択**: 今回は見送り(全ページ・全JSファイルの文字列をi18nキー化する大きな別作業になるため)。単位設定(距離km/nm、高度ft/m)のみ実装。
- **マルチ機体3Dのアーキテクチャ**: 現状の同時受信数(~14機程度)ならデフォルト全機体表示は視覚的に問題ないと判断。既存の「選択機体ごとに独立ポーリングするWebSocket」方式(1機体なら問題ない)から、**全機体一括配信の共有WebSocket1本**に変更(readsbへの冗長ポーリングを回避)。
- **モダンな便利機能**: ユーザー提案の4件(高度による色分け、Shift+クリックで単体表示、ホバーツールチップ、カメラ自動追従)を全て採用。

### Milestone X:バグ修正(新規アーキテクチャなし)

- [x] 3D航跡のマーカー/ラベルがICAO16進コード表示だったのをcallsign表示に変更(`<select>`のoptionに保持していたcallsignを流用)。
- [x] 3D航跡でライブ更新中の航跡(黄色線)が伸びないバグを修正 — 根本原因はWSハンドラが`liveEntity.position`を更新するだけで、ポリラインへの追記が一切なかったこと(コードレビューで確認済み)。`Cesium.CallbackProperty`で成長する配列を参照するポリラインに変更し、過去軌跡(シアン)の終端からライブ軌跡(黄色)が実際に伸びることを実環境で確認。
- [x] 3D航跡で機体クリック時にサイドバーを開くよう追加(`Cesium.ScreenSpaceEventHandler` + `scene.pick`、既存の共有サイドバーを流用)。
- [x] 今日の空の最遠/最接近/最多観測をICAOコードからcallsign表示に変更 — `app/db/queries/period.py`の`compute_daily_summary`が読む3クエリにcallsignを追加(`traffic_day`テーブル側=過去日分は対象外、スキーマ変更なし)。
- [x] 今日の空の機種別機数チャートがTop3で止まり動的更新もされないバグを調査 — 根本原因は`aircraft_type_cache`が1日1回(`adsb-daily-rollup`の`--loop`サイクル内)しか更新されないアーキテクチャのミスマッチと判明(クエリ自体は正しい)。`app/aircraft_lookup.py`を独立した`--loop --interval-minutes`CLIに分離し、新規`adsb-type-lookup`サービス(15分間隔)として実行。実環境で3種類→10種類にチャートが実際に増えることを確認。

### Milestone Y:設定タブ(単位のみ、言語は見送り)

- [x] `app/static/settings.html` + `app/static/js/settings.js`新規: 距離単位(km/海里)・高度単位(ft/m)を`localStorage`のみで保存(Milestone Oのfavorites方式と同じくサーバー関与なし)。
- [x] 共有`app/static/js/units.js`新規: `formatDistance`/`formatAltitude`/`toDisplayDistance`(軸データ自体を変換する必要がある箇所用)。
- [x] 既存の距離/高度表示箇所全てに配線: `ui.js`のランキング行、`daily.js`のハイライトタイル、`aircraftinfo.js`のサイドバー、`map.js`のポップアップ、`receiver.js`のチャート(方位別受信距離、高度帯別受信距離、RSSI距離ヒートマップ、3D受信範囲半球) — ツールチップ文字列だけでなく系列データ自体も変換し、軸目盛りとツールチップの単位が食い違わないようにした。
- [x] 全ページのnavに設定リンク追加。
- [x] 実環境でnm/mに切り替え、ダッシュボード・今日の空・サイドバー・受信性能チャート(軸ラベル含む)が正しく変換されることをPlaywrightで確認、全8ページでconsole errorゼロ。

### Milestone Z:マルチ機体ライブ3D + モダンな操作性

- [x] **Z-1**: `WS /ws/aircraft-positions`(`app/api/routers/aircraft_positions.py`新規)を追加 — アプリのlifespanで起動/停止される単一のバックグラウンドタスクがreadsbを1回ポーリングし、接続中の全クライアントに同じスナップショットを配信。既存の`WS /ws/aircraft/{icao}`(サイドバー用、tar1090相当の詳細フィールド)は無変更。
- [x] **Z-2**: `app/static/js/globe.js`を全面刷新:
  - デフォルトで現在受信中の全機体を高度帯別の色分けドットで表示(`/api/config`の`altitude_bands`を2D地図と共通利用)。
  - 機体クリックで共有サイドバーを開く。
  - Shift+クリックで単体表示に切替(他機体を非表示にし、過去軌跡+ライブ延伸軌跡を表示)、再度Shift+クリックか「全機体表示に戻す」ボタンで解除。
  - ホバーでcallsign/高度/速度のツールチップ表示(配信済みデータのみ、追加リクエストなし)。
  - 「機体選択」チェックボックス式ポップオーバーで表示機体を絞り込み(デフォルト全機体表示)。
  - 「カメラ自動追従」トグルでCesium組み込みの`trackedEntity`を単体表示中の機体にロック(ユーザーが手動でパン/ズームすると自動解除、`viewer.trackedEntityChanged`で追従ボタンの状態も同期)。
  - Cesiumの初期カメラは地球全体を映す仕様のため、初回のライブデータ受信時に受信機体の重心へ自動フライト(以降はユーザー操作を妨げないよう1回のみ)。
- [x] `CLAUDE.md`/`README.md`の「リアルタイム追跡はしない」記述を実態に合わせて修正 — 3D航跡のデフォルト表示は実質的に「全機体のライブマップ」になったため、意図的な例外として正直に3件目として明記(tar1090の全フィールドではない点、この1ページに限定される点は維持)。

### セッション記録

```text
日付: 2026-07-30
完了したMilestone/Task: Milestone X(バグ修正5件)、Milestone Y(設定タブ・単位)、Milestone Z(マルチ機体ライブ3D航跡)
変更した主要ファイル:
  - Milestone X: app/db/queries/period.py、app/api/schemas.py、app/static/js/daily.js、app/aircraft_lookup.py(--loopのCLI化)、app/dailyrollup.py(型キャッシュ更新の分離)、compose.yaml(adsb-type-lookup新規)、app/static/js/globe.js
  - Milestone Y: app/static/settings.html(新規)、app/static/js/settings.js(新規)、app/static/js/units.js(新規)、ui.js、daily.js、aircraftinfo.js、map.js、receiver.js、全ページのnav
  - Milestone Z: app/api/routers/aircraft_positions.py(新規)、app/api/main.py(lifespanでbroadcaster起動)、app/static/js/globe.js(全面刷新)、app/static/globe.html、app/static/css/style.css
  - 全体: README.md、CLAUDE.md
実行したテスト: pytest(フルスイート、282→288件)、ruff check
テスト結果: 全green、lint clean
実環境で確認したこと:
  - Milestone X: callsign表示・ライブ軌跡延伸・クリックでサイドバー表示・今日の空のcallsign表示・機種別チャートが3種類→10種類に増えることをPlaywright/curlで確認。
  - Milestone Y: nm/m切り替え後、ダッシュボード・今日の空・サイドバー・受信性能チャート(軸ラベル含む)の全てが正しく変換されることを確認。
  - Milestone Z: Cesiumの`scene.pick()`を直接呼び出して実機体の正確な画面座標を取得する手法で、実際に動いている機体へのクリック/Shift+クリックを確実に再現し、デフォルト全機体表示・色分け・ピッカーでの表示切替・クリックでのサイドバー表示・単体表示への切替と解除・ホバーツールチップ・カメラ追従の全てを確認。ホバーツールチップがCanvas外にマウスが出ると消えない実バグを発見しその場で修正(`mouseleave`リスナー追加)。全8ページでconsole errorゼロ。
残課題:
  - なし(3マイルストーン全て完了・デプロイ・検証済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 20. 3D航跡:複数機体の航跡ライン + 透明度設定 + 3D機体モデル(Milestone AA)

マルチ機体3D航跡(Milestone Z)を実際に使ったユーザーからの追加フィードバック3件を受けて実施。着手前にAskUserQuestionで2点を確認:

- **3Dモデルの粒度**: 機種別(737/A320等)に作り分けるか、汎用モデル1種類で統一するか → **汎用モデル1種類で統一**を選択(機種別モデルは`aircraft_type_cache`との連携・複数モデルのライセンス確認等、大幅な工数増になるため)。
- **モデルファイルの調達方法**: ユーザー提供のURLを使うか、無償・再配布可能なモデルを探して提案するか → **探して提案**を選択。調査の結果、CesiumJS自身がSandcastleデモ用に同梱している`Cesium_Air.glb`(`CesiumGS/cesium`リポジトリの`Apps/SampleData/models/CesiumAir/`)を採用 — このアプリが既にベンダリングしているCesiumJS本体と同じApache License 2.0でカバーされており、追加のライセンスリスクなし。GitHub APIで実在確認、`strings`/バイナリ解析でDraco圧縮なし(WASMデコーダ不要)を確認済み。

### Milestone AA-1:全機体の航跡ライン表示

- [x] デフォルト(全機体)表示で航跡ラインが出ない挙動を調査 — バグではなく仕様通りで、単体表示(isolate)モードでのみ`isolateHistoryEntities`/`isolateLiveEntity`/`isolateLiveTrackPositions`という単一機体専用の状態変数を使って過去軌跡+ライブ延伸軌跡を描画していたことが判明。
- [x] `app/static/js/globe.js`を全機体対応に一般化: `trackState`(icao→{historyEntities, liveEntity, liveTrackPositions})というMapに置き換え、新規機体が最初に出現した時点で`ensureTrack()`が自動的に過去軌跡取得+ライブポリラインを開始。`applyVisibility()`は機体本体だけでなく対応する航跡の表示/非表示も連動させ、`removeStaleEntities()`は航跡エンティティも解体する。isolate機能自体は「他機体を隠す+カメラを飛ばす」だけに簡素化(航跡の生成/破棄はもう担当しない)。

### Milestone AA-2:航跡ラインの透明度設定(デフォルト50%)

- [x] 新規`app/static/js/track-settings.js`(`units.js`と同じ形): `getTrackOpacity()`/`setTrackOpacity()`、`localStorage`キー`adsb-analytics:track-opacity`、デフォルト0.5。
- [x] `app/static/settings.html`に「3D航跡」パネル新設、`<input type="range">`(このアプリ初のレンジスライダー、`style.css`に`::-webkit-slider-thumb`/`::-moz-range-thumb`を新規追加)+ パーセント表示ラベル。
- [x] `globe.js`でページ読み込み時に一度だけ`getTrackOpacity()`を読み、過去軌跡(シアン)・ライブ軌跡(黄)両方のポリライン`material`に`Cesium.Color.withAlpha(opacity)`を適用。

### Milestone AA-3:3D機体モデル(機首方向・傾きを反映)

- [x] `Cesium_Air.glb`(Apache-2.0、上記調査で確認済み)を`app/static/models/aircraft.glb`としてダウンロード・配置。
- [x] `app/api/routers/aircraft_positions.py`の`extract_position()`を拡張: `roll_deg`(readsbの`roll`、多くの機体で未装備のため`None`が普通)、`vertical_rate_fpm`(`baro_rate`優先、`geom_rate`フォールバック — `app/collector/normalize.py`と同じ優先順位)を追加。`track_deg`は既存の配信フィールドをそのまま流用(これまでクライアント側で未使用だった)。テスト追加(`tests/unit/test_aircraft_positions.py`)。
- [x] `globe.js`: readsbにpitchフィールドが無いため、垂直速度(fpm)と地速(kt)から`Math.atan2`で近似算出(実飛行力学ではなく視覚的な目安と明記)。`Cesium.Transforms.headingPitchRollQuaternion`で向きのクォータニオンを構築し`entity.orientation`に設定、`point`グラフィックを`model`グラフィックに置き換え(`colorBlendMode: MIX`で高度帯色を維持)。
- [x] **実機体では検証しづらいテストケースのため、合成テスト用エンティティを一時的に追加して検証**(この手法もこのセッションで確立した「ドキュメントを鵜呑みにせず実際に確認する」姿勢の延長): 真方位0°(北)を指定した固定エンティティを真上から見下ろすカメラで撮影した結果、機首が東(90°時計回り)を向いて描画されるバグを発見 — `MODEL_HEADING_OFFSET_RAD = -90°`で補正し、再検証して機首が正しく北を向くことを確認。ロール(バンク角)の符号は、テスト中に実際にバンクしている機体のroll値が観測できなかったため視覚的な確認はできなかったが、Cesiumの公式ドキュメント(roll正=右バンク)とADS-Bのroll規約(正=右バンク)が一致することを根拠にそのまま採用(コード内に検証状況を正直に明記)。
- [x] `README.md`/`CLAUDE.md`を更新: モデルの出典・ライセンス表記、3D航跡ページの説明(全機体モデル表示・航跡・透明度設定)、配信フィールドにroll/vertical_rateが増えたことの反映。

### セッション記録

```text
日付: 2026-07-30
完了したMilestone/Task: Milestone AA-1(全機体航跡表示)、AA-2(航跡透明度設定)、AA-3(3D機体モデル+向き)
変更した主要ファイル:
  - AA-1: app/static/js/globe.js(trackState一般化)
  - AA-2: app/static/js/track-settings.js(新規)、app/static/settings.html、app/static/js/settings.js、app/static/css/style.css(レンジスライダー)、app/static/js/globe.js
  - AA-3: app/static/models/aircraft.glb(新規、Cesium_Air.glb由来)、app/api/routers/aircraft_positions.py、tests/unit/test_aircraft_positions.py、app/static/js/globe.js
  - 全体: README.md、CLAUDE.md、app/static/globe.html
実行したテスト: pytest(フルスイート、288→291件)、ruff check
テスト結果: 全green、lint clean
実環境で確認したこと:
  - AA-1: デフォルト全機体表示で各機体が個別のシアン(過去)+黄(ライブ延伸)航跡を持つことをPlaywrightで確認。
  - AA-2: 設定画面でスライダーを20%に変更→`localStorage`保存→再読み込み後も反映→3D航跡ページで実際に線が薄くなることを確認。
  - AA-3: 3Dモデルが実際にレンダリングされること(CSP変更不要、Draco/WASM問題なし)を確認。合成テストエンティティで機首方向のキャリブレーションを実施しバグを発見・修正。クリック→サイドバー、Shift+クリック→単体表示/解除が`model`グラフィックのエンティティでも引き続き動作することを`scene.pick()`直接呼び出しの手法で確認。全8ページでconsole errorゼロ。
残課題:
  - ロール(バンク角)の符号がCesiumのドキュメント記載に基づく想定のみで、実機体での視覚的な検証はできていない(バンクしている機体のroll値がテスト中に観測できなかったため)。将来的に実際にターンしている機体のroll値がある状況で見た目がおかしければ、`globe.js`の`MODEL_ROLL_SIGN`を`-1`に反転する。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 21. 3D航跡:過去航跡モード(1h/6h/24h) + ライブ更新1Hzモード(Milestone BB)

3D航跡ページへの追加フィードバック2件を受けて実施。

- **過去航跡モード**: フルスクリーン地図(`app/static/fullmap.html`/`app/static/js/map.js`)が既に持つ1h/6h/24hの期間ボタン+`GET /api/tracks?hours=`+ホバーポップアップの仕組みをそのまま3D航跡に流用する方針とした。調査で1点課題が判明: `GET /api/tracks`の座標は`[lon, lat]`のみ(高度なし)で、`GET /api/aircraft/{icao}/positions`(既存のライブ単体表示で使用)とは異なる。高度なしでは上昇・降下中の機体が真っ平らな線として描画され、ライブ3D航跡の隣で明らかに不自然に見えるため、`GET /api/tracks`のGeoJSON座標を`[lon, lat, altitude_ft]`の3要素に拡張(RFC 7946準拠、MapLibre GL JSは3要素目を無視するだけで動作に影響しない — 実機で2D地図/フルスクリーン地図が変更後も無エラーで描画されることを確認済み)。
- **ライブ更新1Hzモード**: `WS /ws/aircraft-positions`の受信専用だったインバウンドチャンネル(`receive_text()`の戻り値を捨てているだけだった)を`{"fast": true/false}`のクライアント制御メッセージに転用。`PositionBroadcaster`が「1秒モードを希望している接続が1つでもあれば1秒、なければ既定値(`POLL_INTERVAL_SECONDS`)」で動作するよう拡張。収集側(`app/collector/service.py`)は完全に別プロセスのため、この変更はDB書き込み頻度に一切影響しない。**「ADS-Bの頻度的に毎秒は可能か」という質問に対し、この実機で`aircraft.json`を1秒間隔で複数回ポーリングし、readsb自身の`now`/`messages`フィールドが毎回確実に進んでいることを実際に確認**(推測ではなく実測に基づく回答)。

### Milestone BB-1:過去航跡モード

- [x] `app/db/queries/tracks.py`/`app/api/routers/tracks.py`: 座標を`[lon, lat, altitude_ft or 0]`の3要素に拡張。既存テスト更新+新規アサーション追加。
- [x] `app/static/globe.html`: ヘッダーに表示モードボタン群(ライブ/1h/6h/24h、`fullmap.html`と同じ`.period-btn`規約)を新設。既存のライブ専用コントロール群に`id="live-controls"`を付与しモード切替時に一括表示/非表示。
- [x] `app/static/js/globe.js`: `enterHistoryMode(hours)`/`enterLiveMode()`を新規実装。過去航跡モードではブロードキャストWSを切断し全ライブエンティティ(機体モデル+航跡)を解体、`GET /api/tracks`から取得した各セグメントを静的ポリラインとして描画(3D機体モデルなし、高度別色分けのみ)。ホバーで`map.js`の`describeFeature`と同じ内容(callsign/高度/速度/距離/観測時刻)のポップアップ、クリックで共有サイドバーを開く処理を追加(`picked.id.trackInfo`をライブ用の`picked.id.icao`と並行してチェック)。

### Milestone BB-2:ライブ更新1Hzモード

- [x] `app/api/routers/aircraft_positions.py`: `FAST_POLL_INTERVAL_SECONDS=1.0`定数、`PositionBroadcaster`に`_fast_clients`セットと`set_fast()`/`current_interval`プロパティを追加。WSハンドラが`receive_text()`の内容を実際にJSONとして解釈し`{"fast": true/false}`を処理するよう変更(不正なメッセージは無視、接続は切らない)。モジュールdocstringを実態に合わせて修正。
- [x] `app/static/globe.html`/`globe.js`: 「更新頻度: 1秒」トグルボタンを追加、`socket.send(JSON.stringify({fast: enabled}))`で送信。再接続時(ライブモードに戻った時)も希望状態を保持し送信し直す。
- [x] テスト追加(`tests/unit/test_aircraft_positions.py`): `PositionBroadcaster`のfast-client管理・`current_interval`選択ロジック。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone BB-1(過去航跡モード)、BB-2(ライブ更新1Hzモード)
変更した主要ファイル:
  - BB-1: app/db/queries/tracks.py、app/api/routers/tracks.py、app/api/schemas.py、tests/integration/test_api.py、app/static/globe.html、app/static/js/globe.js
  - BB-2: app/api/routers/aircraft_positions.py、tests/unit/test_aircraft_positions.py、app/static/globe.html、app/static/js/globe.js
  - 全体: README.md、CLAUDE.md
実行したテスト: pytest(フルスイート、291→295件)、ruff check
テスト結果: 全green、lint clean
実環境で確認したこと:
  - readsbの`aircraft.json`を1秒間隔で5回ポーリングし、`now`/`messages`フィールドが毎回確実に進むことを実測(1Hzモードの技術的な妥当性を推測ではなく実データで確認)。
  - BB-1: 過去航跡モード(1h/6h/24h)で全機体の過去航跡が実際に高度変化を伴う3D形状(平坦でない)で描画されること、ホバーポップアップの内容、クリックでのサイドバー表示、ライブモードへの復帰(3D機体モデル・ライブコントロールが正しく戻る)を確認。座標拡張後もフルスクリーン地図/ダッシュボードの2D地図が無エラーで描画されることを確認。
  - BB-2: WebSocketフレームの実際の受信間隔を計測し、既定時は約5秒間隔、「更新頻度: 1秒」有効時は約1.0-1.08秒間隔に変化、無効化で約5秒間隔に戻ることを実測で確認。
残課題:
  - なし(両マイルストーン完了・デプロイ・検証済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 22. 3D航跡スライダー/透明度 + フルマップサイドバー + 凡例 + 今日の空拡張 + 受信性能3D半球のCesiumJS化(Milestone CC)

3D航跡・フルスクリーン地図・今日の空・受信性能の4ページにまたがる7件のフィードバックを受けて実施。

- **過去航跡の時間スライダー化**: `1h/6h/24h`の3ボタンを、15分(0.25h)刻みで動かせるレンジスライダーに置き換え。`GET /api/tracks?hours=`の`hours`パラメータ制約を`ge=1`から`ge=0.25`(float)に緩和。スライダーは`input`イベントでラベルのみ即時更新、`change`イベント(ドラッグ終了時)で実際の再取得を行う設計とし、リクエストトークンで古い応答を破棄するガードも追加(ボタンと違いスライダーは短時間に`change`が連続発火し得るため)。
- **過去航跡の透明度未適用バグ**: `enterHistoryMode`のポリライン生成が`.withAlpha(trackOpacity)`を呼んでおらず、設定した透明度がライブ航跡にしか効いていなかった実バグを発見・修正。
- **フルスクリーン地図への共有サイドバー追加**: `map.js`(`index.html`埋め込み地図・`fullmap.html`共有)の航跡クリックハンドラに`openAircraftSidebar`呼び出しを追加。他の全ページが既に使っている共有モジュールを流用しただけで、両ページに同時に反映。
- **高度色分けの凡例**: 新規共有モジュール`app/static/js/altitude-legend.js`(`renderAltitudeLegend`)を3D航跡・ダッシュボード地図・フルスクリーン地図の3ページから呼び出し、`/api/config`の`altitude_bands`が元々持っていた日本語ラベルを初めて画面に表示。
- **今日の空「最遠」callsignバグの根本原因調査**: 実データ調査で判明した実態は「最遠/最接近の1行そのものの callsign を使う」設計自体は意図通りだが、機体を初めて捕捉した直後の(=電波到達範囲ギリギリで最遠になりやすい)最初の数pingはcallsign未デコードのことが多いという系統的バイアスだった(本日の最遠機体は61行中最初の2行がcallsign nullで3行目から`CAL003`、全275機体中「最大距離行のcallsignがnull」は37%、ランダムな1行では6.1%)。`farthest`/`closest`クエリを、その機体のその日のうちで時間的に最も近い非null callsignを相関サブクエリで拾う方式に変更(元の設計意図=正しいフライトレグのcallsignを保つ、を維持したまま実バグのみ修正)。`most_observed`にも同型の潜在バグがあったため`FILTER (WHERE callsign IS NOT NULL)`で同様に硬化。
- **今日の空の新機能3件(ユーザーが提示した3案全てを選択)**: 本日初観測の機体一覧(`aircraft.first_seen_at`が当日のもの、最大20件)、本日の最高速度/最高高度ハイライトカード(farthest/closestと同じ相関サブクエリでcallsignを解決)、直近7日間のユニーク機数トレンドスパークライン(`traffic_day`の過去6日+当日のライブ集計を結合、最終日を強調表示)。
- **受信性能3D半球のCesiumJS化**: echarts-glのXYZ散布図(何を示しているか分かりにくいという指摘)を、ユーザーの明示的な選択(「echarts-gl改良」ではなく「CesiumJSベースに作り直す」を選択)に基づきCesiumJSシーンで再構築。方位16分割×仰角9分割の各セルをテクスチャなしの三角形メッシュとして接続描画(点の散布ではなく面)、東西南北ラベル、同心円の距離目安リング、ホバーで方位/仰角/距離のツールチップ、色の意味と実測最大距離(nm/km設定に連動)を説明するキャプションを追加。受信局の実座標は今まで通り一切APIで返さない設計を維持しつつ、Cesiumのlocal East-North-Up座標系は地球上のどの地点に置いても真北基準で正しく成立するという性質を利用し、Null Island(0°N/0°E)という明らかに実在と無関係な仮の座標にシーンを固定(既存のプライバシー設計をコード上も明記)。バックエンド側は`bearing_elevation_range`を同ファイル内の`bearing_range`と同じ手法で16×9セル全件ゼロ埋めするよう変更(疎な結果だと隣接セルの三角形メッシュを繋げられないため)。CSPは`globe.html`で既に実証済みの`'unsafe-eval'`+`blob:`をそのまま踏襲(今回は初回デプロイでCSPエラー・Cesium初期化エラーとも一切発生せず)。

### Milestone CC-1:過去航跡スライダー + 透明度バグ修正

- [x] `app/api/routers/tracks.py`/`app/db/queries/tracks.py`: `hours`をfloat化、`ge=0.25`に緩和。
- [x] `app/static/globe.html`/`app/static/js/globe.js`: 1h/6h/24hボタンをスライダーに置き換え、リクエストトークンガード追加、履歴航跡に`.withAlpha(trackOpacity)`を適用。
- [x] テスト追加: `hours=0.25`受理・`hours=0.1`拒否のケース。

### Milestone CC-2:フルスクリーン地図への共有サイドバー追加

- [x] `app/static/js/map.js`: `openAircraftSidebar`をインポートし航跡クリックハンドラで呼び出し(`index.html`/`fullmap.html`両方に反映)。

### Milestone CC-3:高度色分け凡例(3D航跡 + 地図)

- [x] 新規`app/static/js/altitude-legend.js`(`renderAltitudeLegend`)、新規CSS(`.altitude-legend`系)。
- [x] `app/static/globe.html`/`fullmap.html`/`index.html`とそれぞれのJSに凡例コンテナ+呼び出しを追加。

### Milestone CC-4:今日の空「最遠/最接近」callsignバグ修正

- [x] `app/db/queries/period.py`: `farthest`/`closest`を相関サブクエリ方式に変更、`most_observed`のcallsign抽出を`FILTER (WHERE callsign IS NOT NULL)`で硬化。
- [x] テスト追加: 最遠行がnull callsignでも同日内の非null callsignを拾うケース、一度もcallsignを broadcastしない機体はnullのまま(クラッシュしない)ケース。

### Milestone CC-5:今日の空 新機能3件

- [x] `app/db/queries/period.py`: `FirstSeenAircraft`データクラス、`fastest`/`highest`クエリ(CC-4と同型の相関サブクエリ)、`first_seen_rows`クエリを追加、`DailyTrafficSummary`を拡張。
- [x] `app/api/schemas.py`: `FirstSeenAircraftResponse`追加、`DailyTrafficSummaryResponse`拡張(ルーター変更不要、`asdict`が再帰的にネストしたdataclassを変換することを確認済み)。
- [x] `app/static/daily.html`/`app/static/js/daily.js`: 最高速度/最高高度ハイライトカード、本日初観測テーブル、7日間トレンドスパークライン(`chart.js`の`createChart`を流用した最小構成)を追加。
- [x] テスト追加: 実際に速度/高度が最大の機体が選ばれること、`first_seen_today`の件数・内容。

### Milestone CC-6:受信性能3D半球のCesiumJS化

- [x] `app/db/queries/receiver.py`: `bearing_elevation_range`を16×9セル全件ゼロ埋めに変更(`bearing_range`と同じパターン)。
- [x] `app/static/receiver.html`: CSPに`blob:`を追加(コメントで`globe.html`と同根の理由を明記)、Cesium widgets CSS読み込み、半球チャートのDOM構造をCesiumコンテナ+ツールチップ+キャプションに置き換え。
- [x] `app/static/js/receiver.js`: 旧`createHemisphereChart`(echarts-gl scatter3D)を削除、Cesiumベースの`createHemisphereDome`を新規実装(ENUローカル座標変換、三角形メッシュのGeometry/GeometryInstance/Primitive構築、東西南北ラベル、距離リング、ホバーツールチップ、単位対応キャプション)。
- [x] テスト更新: `bearing_elevation_range`の空/シード済みテストを「常に16×9=144件」の形に合わせて更新。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone CC-1(過去航跡スライダー+透明度修正)、CC-2(フルマップサイドバー)、CC-3(高度凡例)、CC-4(最遠/最接近callsignバグ修正)、CC-5(今日の空新機能3件)、CC-6(受信性能3D半球のCesiumJS化)
変更した主要ファイル:
  - CC-1: app/api/routers/tracks.py、app/db/queries/tracks.py、app/static/globe.html、app/static/js/globe.js、app/static/css/style.css、tests/integration/test_api.py
  - CC-2: app/static/js/map.js
  - CC-3: app/static/js/altitude-legend.js(新規)、app/static/css/style.css、app/static/globe.html、app/static/fullmap.html、app/static/index.html、app/static/js/globe.js、app/static/js/main.js、app/static/js/fullmap.js
  - CC-4/CC-5: app/db/queries/period.py、app/api/schemas.py、app/static/daily.html、app/static/js/daily.js、tests/integration/test_api.py
  - CC-6: app/db/queries/receiver.py、app/static/receiver.html、app/static/js/receiver.js、tests/integration/test_api.py
  - 全体: README.md
実行したテスト: pytest(フルスイート、299件)、ruff check(app tests scripts migrations)
テスト結果: 全green、lint clean
実環境で確認したこと:
  - CC-1: スライダーを操作すると15分刻みで`GET /api/tracks`の`hours`が変化し過去航跡が再描画されること、履歴モードの航跡が設定した透明度で薄く描画されること(修正前後のスクリーンショット比較)。
  - CC-2: フルスクリーン地図で航跡をクリックすると他ページと同じ共有サイドバーが開くこと。
  - CC-3: 3D航跡・ダッシュボード地図・フルスクリーン地図それぞれで凡例が表示され、実際の帯色と一致すること。
  - CC-4/CC-5: 今日の空の最遠/最接近が実データでcallsign表示になること、最高速度/最高高度カード・本日初観測リスト・7日間トレンドが実データで描画されること。
  - CC-6: デプロイ後の初回Playwright確認でCSPエラー・console error 0件(このセッションで過去に構築したCesium系ページは全て初回に何らかのCSP/初期化エラーが出ていたため、今回が初めての一発成功)。実際にドームメッシュ上をホバーして方位/仰角/距離ツールチップが表示されること(例: 「方位113° / 仰角10° / 距離176.9 km」)、期間ボタン(24h/7日/30日)切り替えでconsole errorが出ないこと、設定タブでnm表示に切り替えるとキャプションの数値が km→nm(357.5 km→193.0 nm)に正しく追従することを確認。
残課題:
  - なし(全Milestone完了・デプロイ・検証・ドキュメント更新済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 23. 3D航跡スライダーのドラッグ位置ズレ修正 + 表示短縮 + 受信性能3D半球の削除(Milestone DD)

§22で実装したCesiumJS版3D受信半球について、ユーザーから「(echarts-gl版に続き、CesiumJS版でも)やはりわかりにくいので機能自体を削除してほしい」という判断があり、機能を丸ごと削除。合わせて3D航跡の過去航跡スライダーについて2件のフィードバック(ドラッグ中に位置がズレて正確に時間指定できない、表示を「x時間y分」から「x.yH」に短縮)に対応。

- **スライダーのドラッグ位置ズレの根本原因**: `.globe-history-slider`内で時間表示ラベル(`<label>過去<span id="history-hours-value">`)がスライダーより**前**のDOM順に置かれており、ドラッグ中に表示文字列の幅が変わる(例:「6時間」→「1時間30分」)たびにflexレイアウトが再計算され、スライダー自体の画面上のX座標がわずかに動いていた。ラベルをスライダーの**後ろ**に移動しただけでは不十分だった: 親の`.app-header__period`が`margin-left: auto`で右寄せされており、内部の可変幅ラベルが伸縮するたびに、この auto margin が消費する余白量が変化し、グループ全体(スライダーごと)が左右に動いていた。根本修正は数値表示spanに`width`(`min-width`ではなく固定`width: 5ch`)を指定し、表示文字列が変わってもボックス幅自体が変化しないようにしたこと。実際にPlaywrightでスライダーをドラッグしながら10段階でbounding boxのx座標を計測し、ドラッグ中一切動かないことを確認。
- **表示形式の短縮**: 「6時間」「1時間30分」のような可変長の日本語表記から、固定的な「6.0H」「1.5H」のような形式に変更(`formatHoursLabel`を10分の1時間単位の整数丸めで実装し、JSの`toFixed`が起こしうる浮動小数点誤差による表示ゆれを回避)。
- **受信性能3D半球の削除**: `app/static/js/receiver.js`のCesiumドーム関連コード(定数・座標変換・三角形メッシュ構築・コンパスラベル・距離リング・ツールチップ・`createHemisphereDome`本体)を全削除し、§22以前(echarts-glの散布図版ですらなく、その前のMilestone Iベースライン)の4チャート構成に戻した。バックエンド(`app/db/queries/receiver.py`の`bearing_elevation_range`/`BearingElevationEntry`、`ELEVATION_BAND_COUNT`等の定数)、ルーター(`/api/receiver/bearing-elevation-range`)、スキーマ(`BearingElevationEntryResponse`/`BearingElevationRangeResponse`)、フロントエンドAPI(`api.js`の`getBearingElevationRange`)を全て削除。ベンダー済み`echarts-gl`(632KB、この機能のみが利用していた)も削除し、`receiver.html`のCSPから`'unsafe-eval'`の理由・`blob:`を全て外して素の`echarts`のみのCSPに戻した(`worker-src 'self' blob:;`はecharts-gl導入前から存在していたため維持)。テスト(`test_receiver_bearing_elevation_range_empty`/`_with_seeded_data`、bounds/openapiテストの該当エントリ)も削除。

### Milestone DD-1:過去航跡スライダーのドラッグ位置ズレ修正 + 表示短縮

- [x] `app/static/globe.html`: ラベル(「過去」固定テキストのみ)→スライダー→数値表示spanの順にDOM再構成。
- [x] `app/static/css/style.css`: `#history-hours-value`に`width: 5ch`(固定幅、`min-width`ではない)+`font-variant-numeric: tabular-nums`を追加。
- [x] `app/static/js/globe.js`: `formatHoursLabel`を「x時間y分」形式から「x.yH」形式(10分の1時間の整数丸め)に変更。
- [x] Playwrightでスライダーを10段階に分けてドラッグしながらbounding boxのx座標を計測し、ドラッグ中スライダー位置が一切動かないことを実機で確認。

### Milestone DD-2:受信性能3D半球の削除

- [x] `app/static/js/receiver.js`: Cesiumドーム関連コード全削除(`showChartError`/`hideChartError`ヘルパーも含む、他に利用箇所がないため)。
- [x] `app/static/receiver.html`: hemisphereセクションのDOM削除、CesiumスクリプトタグとWidgets CSS削除、CSPを`script-src 'self' 'unsafe-eval';`(echarts-glのみを理由とする、素のecharts用)に復元。
- [x] `app/db/queries/receiver.py`/`app/api/routers/receiver.py`/`app/api/schemas.py`: `bearing_elevation_range`関連の関数・データクラス・エンドポイント・スキーマを全削除。
- [x] `app/static/js/api.js`: `getBearingElevationRange`削除。
- [x] ベンダー済み`app/static/js/vendor/echarts-gl/`を削除(`git rm`)。
- [x] `tests/integration/test_api.py`: 該当テスト・bounds/openapiテストのエントリを削除。
- [x] README.mdの受信性能・3D航跡セクション、CSP関連の記述を更新(削除の経緯を明記)。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone DD-1(過去航跡スライダーのドラッグ位置ズレ修正+表示短縮)、DD-2(受信性能3D半球の削除)
変更した主要ファイル:
  - DD-1: app/static/globe.html、app/static/css/style.css、app/static/js/globe.js
  - DD-2: app/static/js/receiver.js、app/static/receiver.html、app/db/queries/receiver.py、app/api/routers/receiver.py、app/api/schemas.py、app/static/js/api.js、app/static/js/vendor/echarts-gl/(削除)、tests/integration/test_api.py
  - 全体: README.md
実行したテスト: pytest(フルスイート、299→297件)、ruff check(app tests scripts migrations)
テスト結果: 全green、lint clean
実環境で確認したこと:
  - DD-1: Playwrightでスライダーのつまみを10段階(10%刻み)でドラッグしながら都度bounding boxのx座標を計測し、修正前は表示文字列の幅変化に応じてスライダー自体が左右に動いていたのに対し、修正後は一切座標が変化しないことを実測で確認。表示形式が実際に「6.0H」のような固定長表記になっていることをスクリーンショットで確認。
  - DD-2: 受信性能ページを再デプロイ後、3D半球のDOM(`#hemisphere-container`)が存在しないこと、旧4チャート(方位別受信距離・高度帯別受信距離・メッセージ数/位置取得率推移・RSSIヒートマップ)が正常描画されること、console error 0件を確認。
  - 全体: ダッシュボード/受信性能/今日の空/機体履歴/フルスクリーン地図/生データ/3D航跡/設定の8ページ全てでconsole error 0件を再確認。
残課題:
  - なし(両マイルストーン完了・デプロイ・検証・ドキュメント更新済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 24. 生データフィルタ + タブ並び替え + 航跡地図ライブモード + 航跡色バグ修正・再配色(Milestone EE)

ダッシュボード全体を使い込んだユーザーからの7件のフィードバックに対応。実装前に3並列のExploreエージェントで生データページ・ナビ構成/フルスクリーン地図・航跡色の3領域を調査し、2件をAskUserQuestionでユーザーに確認したうえで実装した。

- **生データのフィルタリング**: DF/ICAO/種別はいずれも`WS /ws/rawdata`で毎フレーム届いておりサーバー往復不要と判明。ICAOのテキストフィルタと、「メッセージ種類」列と全く同じ文字列をキーにした複数選択ポップオーバー(globe.htmlの機体選択ポップオーバーと同じCSS/構造を再利用)を追加。フィルタは表示のみに影響し、500件バッファ・一時停止・クリアの挙動には一切影響しない設計とした。
- **タブ並び替え + 改名**: ダッシュボード→今日の空→受信性能→航跡地図(旧フルスクリーン地図)→3D航跡→機体履歴→生データ→設定の順に変更。8ページ全てに手動複製されている`<nav>`ブロック(テンプレート化されていない)をPythonスクリプトで一括生成・置換。
- **航跡色バグの根本原因**: `map.js`の`tracksToLineFeatures`と`globe.js`の`enterHistoryMode`はいずれも「機体1機につき1色」を`last_altitude_ft`から一度だけ計算し、航跡全体をその色で塗っていた(高度データ自体は各点に既に存在しており、レンダリングロジックの不備と判明)。さらに`globe.js`のライブモードの機体別航跡(`ensureTrack`)は高度帯と無関係な固定色(黄=ライブ延伸中/シアン=過去分)を使っており、そもそも凡例と対応する設計になっていなかった。ユーザー確認の上、ライブモードも高度帯配色に統一する方針とした。
- **修正方式**: 高度帯が変化するたびに新しいポリライン(区間の境界点を共有して視覚的な連続性を保つ)に分割する「バンドラン分割」を採用。MapLibreは1フィーチャーにつき1色、Cesiumポリラインは1エンティティにつき1マテリアルという制約が同じ形をしているため、2D/3D共通の考え方で実装(`map.js`の`splitCoordinatesByBand`、`globe.js`の`addBandRunPolylines`/ライブ延伸用の`pushLiveTrackPoint`)。副次的に見つかった実データバグとして、`GET /api/tracks`が高度不明を`altitude_ft or 0`で0(地上)に丸めていたのを修正し、`GeoJSONMultiLineString.coordinates`にNoneを許容するようスキーマを緩和。
- **再配色**: 中高度を旧高高度の青(`#60a5fa`)に、高高度を旧超高高度の紫(`#c084fc`)に、超高高度を新しい赤(`#ef4444`)に変更(地上/低高度は変更なし)。`altitude-legend.js`は各帯の正確な数値範囲(配列の並び順から下限を導出、バックエンド変更不要)も表示するよう拡張。
- **航跡地図(フルスクリーン地図)のライブモード**: 3D航跡と同じ`WS /ws/aircraft-positions`共有ブロードキャストに接続し、機種カテゴリ別のフラット2Dアイコン(MapLibreのsymbolレイヤー、`icon-rotate`で機首方向に回転)で全機体を表示。クリックでサイドバー、Shift+クリックで機体を1機に絞り込み、機体選択ポップオーバー、更新頻度1秒切り替えなど、3D航跡のライブモードと同じ操作感を実装(状態遷移も`connectBroadcast`/`teardownLiveView`/`enterHistoryMode`/`enterLiveMode`という同じ形)。アイコンは機種の正確なシルエットではなく、readsbのADS-B `category`フィールド(軽量機/大型機/回転翼機/滑空機/UAV/地上車両など約7分類)に基づく自作の単純なSVGシルエットとする方針を、ユーザーに確認の上で採用(tar1090/FlightRadar24規模の機種別アイコンライブラリはライセンス・工数の両面でこの個人アプリの規模に見合わないため)。`aircraft_positions.py`の`extract_position`にreadsbの`category`フィールドをそのまま追加(追加のI/Oなし)。
- **フルスクリーン地図の過去履歴スライダー**: 1h/6h/24hボタンを1時間刻みのスライダーに変更し、`GET /api/tracks`の`hours`上限を24→72に拡大(既存の`MAX_TOTAL_POINTS`/`MAX_AIRCRAFT`間引きが72hでも安全に機能するため、他のバックエンド変更は不要)。

### Milestone EE-1:生データのフィルタリング

- [x] `app/static/js/rawdata.js`: ICAOテキストフィルタ、メッセージ種類ポップオーバー(動的に選択肢を追加)を実装。`app/static/rawdata.html`にフィルタUIを追加。

### Milestone EE-2:タブ並び替え + フルスクリーン地図→航跡地図改名

- [x] 全8ページの`<nav>`ブロックを新しい並び順に更新、`fullmap.html`の`<title>`を`<h1>`(既に「航跡地図」だった)に合わせて修正。

### Milestone EE-3:航跡色システムの見直し(バグ修正 + 再配色 + 数値範囲表示)

- [x] `app/domain/bands.py`: 中高度/高高度/超高高度の色を変更。
- [x] `app/static/js/altitude-legend.js`: 各帯の数値範囲を表示。
- [x] `app/api/routers/tracks.py`/`app/api/schemas.py`: 高度不明の0埋めを廃止しNoneを許容。
- [x] `app/static/js/map.js`: `splitCoordinatesByBand`でバンドラン分割、`tracksToLineFeatures`を書き換え。
- [x] `app/static/js/globe.js`: `addBandRunPolylines`(履歴モード・機体別過去航跡)、`pushLiveTrackPoint`(ライブ延伸航跡)を実装し、旧黄/シアン固定色を廃止。

### Milestone EE-4:航跡地図の過去履歴スライダー(1時間単位、最大72時間)

- [x] `app/api/routers/tracks.py`: `hours`の上限を72に拡大。`tests/integration/test_api.py`のbounds/72h受理テストを更新。
- [x] `app/static/fullmap.html`/`app/static/js/fullmap.js`: 期間ボタンをスライダーに置き換え。

### Milestone EE-5:航跡地図のライブモード(カテゴリ別アイコン)

- [x] `app/api/routers/aircraft_positions.py`: `category`フィールドを追加。
- [x] 新規`app/static/js/aircraft-icons.js`: カテゴリ別SVGシルエット(高度帯色ごとに事前生成し`map.addImage`で登録)。
- [x] `app/static/js/map.js`: ライブ位置用symbolレイヤー、`setLivePositions`/`clearLivePositions`/`setLiveFeatureShiftClickHandler`を追加。
- [x] `app/static/js/fullmap.js`: ライブ/履歴モードの状態遷移、機体選択ポップオーバー、更新頻度切り替え、Shift+クリック分離を実装。
- [x] 実機確認中に判明した不具合を修正: symbolレイヤーの`text-field`がMAP_STYLE_URLの既定フォント("Open Sans")を要求し404していたため、`text-font`をスタイルが実際にホストする"Noto Sans Regular"に明示指定。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone EE-1(生データフィルタ)、EE-2(タブ並び替え+改名)、EE-3(航跡色システム見直し)、EE-4(航跡地図スライダー)、EE-5(航跡地図ライブモード)
変更した主要ファイル:
  - EE-1: app/static/rawdata.html、app/static/js/rawdata.js
  - EE-2: app/static/{daily,fullmap,globe,history,index,rawdata,receiver,settings}.html
  - EE-3: app/domain/bands.py、app/static/js/altitude-legend.js、app/api/routers/tracks.py、app/api/schemas.py、app/static/js/map.js、app/static/js/globe.js、app/static/css/style.css
  - EE-4: app/api/routers/tracks.py、app/static/fullmap.html、app/static/js/fullmap.js、tests/integration/test_api.py
  - EE-5: app/api/routers/aircraft_positions.py、app/static/js/aircraft-icons.js(新規)、app/static/js/map.js、app/static/js/fullmap.js、tests/unit/test_aircraft_positions.py
  - 全体: README.md、CLAUDE.md
実行したテスト: pytest(フルスイート、297→298件)、ruff check(app tests scripts migrations)
テスト結果: 全green、lint clean
実環境で確認したこと:
  - EE-1: ICAOフィルタ・メッセージ種類ポップオーバーで実際に該当行が非表示になること、フィルタが受信・バッファ・一時停止/クリアの挙動に影響しないことを確認。
  - EE-3: フルスクリーン地図72時間表示・3D航跡24時間表示のいずれでも、1本の航跡が離陸/着陸区間で複数の色に変化していることをスクリーンショットで確認(赤→紫→青→緑のグラデーション状の遷移が実際に描画された)。凡例の数値範囲、再配色後の色も確認。
  - EE-5: ライブモードでカテゴリ別アイコンが実際に機首方向へ回転し高度帯で色分けされて表示されること、アイコンクリックでサイドバーが開くこと、機体選択ですべて非表示にできること、更新頻度1秒トグルが正常に切り替わることを確認。デプロイ直後の実機確認で`text-font`未指定によるフォント404を発見・修正(この1点を除き初回デプロイでconsole error 0件)。
  - 全体: 8ページ全てでconsole error 0件を再確認。
残課題:
  - なし(全Milestone完了・デプロイ・検証・ドキュメント更新済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 25. 高度帯しきい値の調整 + 生データの小改善 + 航跡地図ライブモードへの航跡ライン追加(Milestone FF)

Milestone EE完了後の細かいフィードバック4件に対応。

- **高度帯しきい値の変更**: 地上/低高度を5000ft以下、低高度を5000〜10000ft、中高度を10000〜20000ft、高高度を20000〜30000ft、超高高度を30000ft超に変更(旧: 0/10000/25000/35000)。`app/domain/bands.py`の`max_ft`のみ変更すれば、色・凡例の数値範囲・航跡の配色・受信性能のバンド集計・ヒートマップのフィルタなど全消費者が`/api/config`経由で自動的に追従する設計であることを実際に確認(他ファイルの変更は一切不要だった)。`tests/unit/test_bands.py`の境界値テスト(5000ftが旧「低高度」→新「地上/低高度」になった点)のみ更新。
- **生データの最大保存件数を500→5000件に増加**: `app/static/js/rawdata.js`の`MAX_ROWS`定数と`app/static/rawdata.html`の表示テキストを変更。
- **24bitアドレスのラベルを「Hex」→「ICAO」に変更**: `app/static/js/aircraftinfo.js`の機体情報サイドバーのヘッダーラベルを変更。生データページのICAOフィルタと表記を揃えることで、フィルタに何を入力すればよいかが分かりやすくなるというユーザーの意図に対応。
- **航跡地図のライブモードに機体別の航跡ラインを追加**: これまでライブモードはアイコンのみで航跡ラインが無かった問題に対応。`map.js`に`updateLiveTracks`/`pruneLiveTracks`/`clearLiveTracks`を新設し、3D航跡の`ensureTrack`/`pushLiveTrackPoint`と同じ設計思想(機体ごとに過去分を`GET /api/aircraft/{icao}/positions`で一度取得、以降はブロードキャストの各tickでライブ延伸、既存の`splitCoordinatesByBand`で高度帯ごとに色分けしたポリラインに分割)をMapLibreのGeoJSON特徴量として実装し、履歴モードと共用している既存の`tracks`ソース/レイヤーにそのまま描画。機体選択で非表示にした機体も裏側では航跡の蓄積を継続し(3D航跡と同じ設計)、表示のみを`visibleLiveIcaos`でフィルタする方式のため、再表示時に航跡が途切れない。

### Milestone FF-1:高度帯しきい値の調整

- [x] `app/domain/bands.py`: `max_ft`を5000/10000/20000/30000/Noneに変更。
- [x] `tests/unit/test_bands.py`: 境界値テストを更新。

### Milestone FF-2:生データの改善(最大件数 + ICAO表記統一)

- [x] `app/static/js/rawdata.js`/`app/static/rawdata.html`: `MAX_ROWS`と表示テキストを5000件に。
- [x] `app/static/js/aircraftinfo.js`: サイドバーのラベルを「Hex」→「ICAO」に変更。

### Milestone FF-3:航跡地図ライブモードへの航跡ライン追加

- [x] `app/static/js/map.js`: `updateLiveTracks`/`pruneLiveTracks`/`clearLiveTracks`、`ensureLiveTrackHistory`/`pushLiveTrackPoint`/`renderLiveTracks`を実装。
- [x] `app/static/js/fullmap.js`: ブロードキャストのメッセージハンドラで`updateLiveTracks`/`pruneLiveTracks`を呼び出し、`teardownLiveView`で`clearLiveTracks`を呼び出すよう配線。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone FF-1(高度帯しきい値調整)、FF-2(生データ改善)、FF-3(航跡地図ライブモード航跡ライン)
変更した主要ファイル:
  - FF-1: app/domain/bands.py、tests/unit/test_bands.py
  - FF-2: app/static/js/rawdata.js、app/static/rawdata.html、app/static/js/aircraftinfo.js
  - FF-3: app/static/js/map.js、app/static/js/fullmap.js、app/static/fullmap.html
  - 全体: README.md
実行したテスト: pytest(フルスイート、298件、全green)、ruff check(app tests scripts migrations)
テスト結果: 全green、lint clean
実環境で確認したこと:
  - FF-1: 凡例が新しいしきい値(5000/10000/20000/30000ft)で正しく表示されることを確認。
  - FF-2: 生データページのヘッダーが「最大5000件」と表示されること、ダッシュボードのランキング経由で開いた機体情報サイドバーが「ICAO: xxxxxx」と表示されることを確認。
  - FF-3: 航跡地図のライブモードで各機体アイコンの下に高度帯で色分けされた航跡ラインが実際に描画されること(スクリーンショットで複数色の航跡を確認)、ライブ→過去→ライブの往復、機体選択の全非表示→全表示往復、航跡ライン自体のクリックでのサイドバー表示、いずれもconsole error 0件で動作することを確認。
  - 全体: 8ページ全てでconsole error 0件を再確認。
残課題:
  - なし(全Milestone完了・デプロイ・検証・ドキュメント更新済み)。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: なし。
```

## 26. バージョン管理ポリシー + PWA化 + Cloudflare Tunnel対応(Milestone GG)

ユーザーからの3件の要望に対応: (1) Tailscale外への一般公開(Cloudflareの利用可否含む)、(2) Android向けのPWA化(ウィジェット化は不要と判断)、(3) バージョン番号が全く進んでいない件のドキュメント化・改善。実装前に3並列のExploreエージェントでdocker compose構成/PWA実現可能性/バージョニング機構を調査した。

- **バージョン管理の根本原因調査**: `git log`で確認したところ、`pyproject.toml`のversionは2026-07-27〜28の2日間で12回バンプされた後、その後3日間・52コミット(EE/FF両マイルストーンの全機能を含む)で一度もバンプされていなかった。さらに調査を進めると、表示されている`(gitrevision)`部分は本番コンテナ内では**常にNone**になっていたことが判明: `app/version.py`の`get_git_revision()`はライブの`git rev-parse`サブプロセス呼び出しに依存していたが、`.dockerignore`が`.git/`を除外し、`python:3.12-slim`にはgitバイナリ自体が存在しないため。つまり本番環境で唯一信頼できるビルド識別子は`pyproject.toml`のversionフィールドだけであり、それが52コミットも止まっていたことがより深刻だったと判明。
- **対応**: `pyproject.toml`を0.5.1→0.6.0にバンプ(蓄積されたEE/FF分の機能追加を反映したminorバンプ、新ポリシーの最初の適用例)。`get_git_revision()`をビルド時に焼き込む`GIT_REVISION`環境変数優先に変更(`Dockerfile`のARG/ENV、`compose.yaml`のbuild.args、`setup.sh`が自動でエクスポート)、ローカル開発時は従来のsubprocessフォールバックを維持。`CLAUDE.md`に新規「Versioning」セクションを追加し、「ユーザーに見える変更は同じコミットでversionをバンプする」ポリシーを明文化。
- **PWA化**: Android Chromeの「ホーム画面に追加」でアプリのようなアイコン・スタンドアロン表示ができるようにした。`manifest.json`、最小限のservice worker(オフラインキャッシュは意図的に実装せず — このアプリのデータは本質的にライブなので、キャッシュされた古いデータを見せるくらいなら何もしない方が良いという判断)、アイコン(`scripts/generate_pwa_icons.py`でPillowを使い、`aircraft-icons.js`の"jet"シルエットを流用して生成、512/192/32pxの3サイズ)を追加。8ページ全てのCSPを調査した結果、変更不要と判明(`default-src 'self'`/`worker-src 'self' blob:'`が既にservice worker登録・manifest取得を許可していた)。
- **Cloudflare Tunnel対応**: `compose.yaml`に新規`cloudflared`サービスを追加。`docker compose up -d`では起動しない「cloudflare」Composeプロファイルで隔離し、ホストポートを一切公開せず(Compose標準ネットワーク経由で`adsb-api`のサービス名で到達可能なことを確認済み)、既存のTailscale専用アクセス経路には一切影響しない設計。Cloudflareアカウント作成・ドメイン追加・Tunnel作成・トークン取得・Accessポリシー設定はユーザー自身のCloudflareダッシュボード操作が必要なため、このリポジトリ側では実施できない旨を明記した上で、README に手順を詳細に記載した。

### Milestone GG-1:バージョン管理ポリシー + git_revision修正 + 0.6.0へバンプ

- [x] `pyproject.toml`: versionを0.6.0にバンプ、devにpillowを追加。
- [x] `app/version.py`: `GIT_REVISION`環境変数を優先するよう`get_git_revision()`を変更。
- [x] `Dockerfile`/`compose.yaml`/`setup.sh`: `GIT_REVISION`のビルド時注入を配線。
- [x] `CLAUDE.md`/`README.md`: バージョニングポリシーを文書化。
- [x] `tests/unit/test_version.py`(新規): 環境変数優先・フォールバックの単体テスト。

### Milestone GG-2:PWA化(Android「ホーム画面に追加」対応)

- [x] `app/static/manifest.json`/`sw.js`/`js/pwa.js`(いずれも新規)。
- [x] `scripts/generate_pwa_icons.py`(新規): アイコン生成(512/192/32px)。
- [x] `app/api/main.py`: `GET /manifest.json`/`GET /sw.js`のルートを追加。
- [x] 全8ページのHTML(manifest/icon/theme-colorのリンク・メタタグ追加)とJSエントリポイント(`registerServiceWorker()`呼び出し追加)。

### Milestone GG-3:Cloudflare Tunnel対応(オプトイン)

- [x] `compose.yaml`: `cloudflared`サービスを`cloudflare`プロファイル配下に新規追加、`adsb-api`に`--proxy-headers`を追加。
- [x] `.env.example`: `CLOUDFLARE_TUNNEL_TOKEN`を追加。
- [x] `CLAUDE.md`/`README.md`: 手動で必要なCloudflareダッシュボード手順を文書化。

### セッション記録

```text
日付: 2026-07-31
完了したMilestone/Task: Milestone GG-1(バージョン管理)、GG-2(PWA化)、GG-3(Cloudflare Tunnel対応)
変更した主要ファイル:
  - GG-1: pyproject.toml、app/version.py、Dockerfile、compose.yaml、setup.sh、tests/unit/test_version.py、CLAUDE.md、README.md
  - GG-2: app/static/manifest.json、app/static/sw.js、app/static/js/pwa.js、app/static/icons/、scripts/generate_pwa_icons.py、app/api/main.py、全8ページのHTML/JS、tests/integration/test_api.py
  - GG-3: compose.yaml、.env.example、CLAUDE.md、README.md
実行したテスト: pytest(フルスイート、301→303件)、ruff check(app tests scripts migrations)
テスト結果: 全green、lint clean
実環境で確認したこと:
  - GG-1: `GIT_REVISION=$(git rev-parse --short HEAD) docker compose build`でビルド・再デプロイし、`/api/config`とページヘッダーが実際に「v0.6.0 (9a475d1)」と表示されることを確認(本番で初めてgit_revisionが表示された)。
  - GG-2: 8ページ全てでservice workerが正しく登録される(console error 0件)こと、`/manifest.json`/`/sw.js`が正しいcontent-typeで配信されること、生成したアイコン(ジェット機シルエット)の見た目を確認。Playwright上ではservice worker APIが利用不可("unsupported")と出るが、これはTailscale経由の平文HTTPがセキュアコンテキストでないためであり、想定通りの挙動であることを確認(HTTPSまたはlocalhostが必要 — Cloudflare Tunnel経由でのアクセス時に有効になる)。
  - GG-3: `docker compose config`で構文検証、`cloudflared`がプロファイル未指定時に起動しないこと(`docker compose ps`で確認)、`adsb-api`が`--proxy-headers`追加後も正常にhealthyであることを確認。実際のトンネル起動(トークン取得含む)はユーザー自身のCloudflareダッシュボード操作待ち。
  - 全体: 8ページ全てでconsole error 0件を再確認。
残課題:
  - Cloudflare Tunnelの実際の稼働確認(トークン取得・Accessポリシー設定含む)はユーザー自身のCloudflareダッシュボード操作待ち。
次に行うTask: なし。ユーザーからの次の指示待ち。
ユーザー判断が必要な事項: Cloudflareアカウント/ドメイン/Tunnel/Accessポリシーの設定(README記載の手順を参照)。
```

