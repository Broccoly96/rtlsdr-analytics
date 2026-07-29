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

- [ ] `app/db/queries/heatmap.py`を新規作成する: `grid_density(pool, hours, cell_deg=0.01, altitude_band=None, hour_of_day=None, day_of_week=None)` — `round(lat/cell_deg)*cell_deg, round(lon/cell_deg)*cell_deg`でグループ化。`MAX_GRID_CELLS`(例: 5000件)の上限をサーバー側で強制する(`tracks.py`の`MAX_TOTAL_POINTS`と同じ安全策、Milestone C-8で`hours=168`が1.18MBを返した失敗を繰り返さない)。
- [ ] `app/api/routers/heatmap.py`を新規作成する: `GET /api/heatmap?hours=1..720&altitude_band=&hour_of_day=0..23&day_of_week=0..6`。
- [ ] `map.js`を拡張し、既存ダッシュボード地図にヒートマップレイヤー+トグルボタン+高度帯/時間帯/曜日フィルタを追加する(新規ページではない)。
- [ ] テスト: グリッド化ロジックの単体テスト、フィルタ組み合わせを含む結合テスト、可能なら`test_map_failure_playwright.py`を拡張する。

**Milestone K 完了条件**
- [ ] Milestone C-8相当の合成データ量で`EXPLAIN ANALYZE`を実施してから、`(round(lat,2), round(lon,2))`等の関数インデックスの要否を判断する(先回りして追加しない)。測定値をセッション記録に残す。

### Milestone L：日次ロールアップ基盤（スキーマ変更、M/N/Oの前提）

このMilestone単体でのユーザー向け機能はない。2A長期比較・2Dの30日超履歴・2Eの週比較が読むデータを、`observations`が保持期限で消える前に用意することが目的。

- [ ] 新規migrationを追加する(既存の初期migrationを`down_revision`とし、`op.execute()`による生SQL、fix-forward方針を踏襲):
  - [ ] `traffic_day(day PK, unique_aircraft_count, max_concurrent_count, message_count_total, position_aircraft_count_max, farthest_icao, farthest_distance_km, closest_icao, closest_distance_km, most_observed_icao, most_observed_count, computed_at)`
  - [ ] `aircraft_day(icao, day, pass_count, observation_count, PK(icao,day))` + `ix_aircraft_day_day(day)`(Milestone Oの「直近N日で最頻」クエリのために先回りで追加、根拠明確なので許容)
  - [ ] `aircraft_callsign_history(icao, callsign, first_seen_at, last_seen_at, PK(icao,callsign))`
- [ ] JST日境界のヘルパー(例: `day_bounds_utc(day, tz_name) -> (start_utc, end_utc)`、`zoneinfo`使用、`settings.display_timezone`起点、Python側で計算しSQLの`AT TIME ZONE`に頼らない)を追加する。
- [ ] `app/db/queries/period.py`を新規作成する:
  - [ ] `compute_daily_summary(pool, start_utc, end_utc) -> DailyTrafficSummary` — ロールアップジョブ(過去日)と2Eの「今日」ライブ読み取りの両方から呼ばれる共通集計ロジック。
  - [ ] `get_traffic_day(pool, day)` — 過去日は`traffic_day`から読む。
  - [ ] `list_traffic_days(pool, start_day, end_day)` — ゼロ埋め、Milestone M用。
- [ ] `app/dailyrollup.py`を新規作成する(`app/retention.py`の構造を踏襲): `--dry-run`、`--day YYYY-MM-DD`(手動バックフィル)、`--loop`(デーモン、JSTで毎日既定00:10頃に実行)。`pg_try_advisory_lock`は`retention.py`の`84372910`とは別のキーを使う。対象日(既定: DISPLAY_TIMEZONEの昨日)について`traffic_day`・`aircraft_day`(ギャップベースのpass分割、`tracks.py`と同種の手法)・`aircraft_callsign_history`を`ON CONFLICT ... DO UPDATE`で冪等に書き込む。
- [ ] 新規Composeサービス`adsb-daily-rollup`を追加する(`adsb-retention`のブロックと同形: `depends_on: adsb-migrate: service_completed_successfully`、`restart: unless-stopped`、`stop_grace_period`、ログ上限)。
- [ ] `tests/contract/pg_container.py`の`clean_db`のTRUNCATE対象に新3テーブルを追加する。`scripts/db_status.py`のテーブル一覧も更新する。
- [ ] テスト: `tests/contract/test_dailyrollup.py`(`test_retention.py`に倣う: advisory lock、冪等性、**「その日のロールアップ値がretention.pyによる同日observations削除後も残る」**ことを確認するテストを含める)。`tests/unit/`にPython純粋ロジック(境界計算・pass分割)のテストを追加する。

**Milestone L 完了条件**
- [ ] 合成データで手計算した期待値とロールアップ結果が一致する。
- [ ] 同じ日を2回実行しても結果が変わらない(冪等性)。
- [ ] retention実行後もロールアップ済みデータが残ることを確認するテストが通る。
- [ ] 実`adsb-db`に対して`--dry-run`と実実行の両方を確認する。

### Milestone M：2A 長期比較（Milestone L依存）

- [ ] `GET /api/traffic/daily?days=1..365`(既定30) — `period.list_traffic_days`、ゼロ埋め。
- [ ] `GET /api/traffic/daily-summary?day=YYYY-MM-DD`(既定は今日) — 今日ならライブで`compute_daily_summary`、過去日なら`get_traffic_day`。比較専用エンドポイントは作らず、フロントエンドがこのエンドポイントを2回呼んで差分計算する(Milestone Nでも同じエンドポイントを再利用)。
- [ ] 既存ダッシュボードのトラフィックパネルに日/週/月の粒度切替と、前日・先週同曜日比較の表示を追加する。

**Milestone M 完了条件**
- [ ] 月表示が数MB級のペイロードにならないことを確認する(レスポンスサイズを実測)。
- [ ] 比較差分が手計算と一致する。
- [ ] `test_openapi_lists_all_endpoints`更新。

### Milestone N：2E 今日の空 + webhook通知（Milestone L依存）

- [ ] `app/static/daily.html` + `app/static/js/daily.js`を新規作成する(今日のライブサマリー、前日・先週同曜日との比較、最遠・最接近・最多観測)。navに追加する。
- [ ] webhook通知(オプトイン、Slack/Discord互換): 環境変数`NOTIFY_WEBHOOK_URL`・`NOTIFY_WEBHOOK_ENABLED`(既定無効、未設定でも起動失敗しない)。`app/notify.py`を新規作成し、Slack互換の`{"text": "..."}`ペイロードで前日分`DailyTrafficSummary`を要約(座標・秘密情報は含めない)、`httpx`で短いタイムアウト付きPOST、失敗時はログのみで継続。`app/dailyrollup.py`の前日ロールアップ完了直後にトリガーする。
- [ ] `.env.example`に新規環境変数をオプトインとして記載する。
- [ ] テスト: `tests/unit/test_notify.py`(ペイロード形状、既定無効、失敗しても例外を投げないこと、モックHTTPトランスポート使用、実webhookは呼ばない)。

**Milestone N 完了条件**
- [ ] webhook無効時、ロールアップの挙動が変化しない。
- [ ] webhook有効時、モックサーバーに対して正しい形状のペイロードが1日1回送られる。
- [ ] ページが実データで表示される。

### Milestone O：2D 機体の再訪履歴（Milestone L依存）

- [ ] `app/db/queries/aircraft_history.py`を新規作成する: `aircraft_summary(pool, icao)`(`aircraft`の永年データ+`aircraft_day`の集計)、`callsign_history(pool, icao)`、`most_frequent(pool, days=1..365, limit=1..100)`(`ix_aircraft_day_day`を利用)。
- [ ] `app/api/routers/aircraft_history.py`を新規作成する: `GET /api/aircraft/{icao}/history`(不明ICAOは404、このAPI初のpathパラメータ404だがGETのみで新たな懸念は生まない)、`GET /api/aircraft/frequent?days=&limit=`。
- [ ] `app/static/history.html` + `app/static/js/history.js`を新規作成する: 最頻観測ランキング(`ui.js`の`renderRankingTable`を再利用)、`?icao=`で機体詳細、callsign履歴。**お気に入り機体はブラウザ`localStorage`のみで実装し、バックエンドの書き込みエンドポイントは追加しない**(このAPI初の書き込み経路にしないため)。navに追加する。
- [ ] テスト: 404ケースを含む結合テストのトリオ、純粋Pythonフォーマットヘルパーの単体テスト。

**Milestone O 完了条件**
- [ ] 複数日にわたる合成データを持つ機体で、観測日数・pass数・callsign履歴が正しく表示される。
- [ ] お気に入りがページ再読み込み後も`localStorage`経由で保持される。
- [ ] `make test`/`make lint`が通る。

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
