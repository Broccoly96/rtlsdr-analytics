// i18n.js -- language preference (Settings tab) and the translation
// dictionary/lookup for every page. Same zero-backend, localStorage-only
// precedent as units.js/track-settings.js: "read once at load, reload to
// see a change" -- no live re-render on language switch, no browser-
// language auto-detection, matching those modules' own documented design
// exactly rather than inventing a new convention for this one setting.
//
// Dictionary keys are dot-namespaced by page/section (e.g. "nav.dashboard",
// "daily.card.unique") to keep ~150+ keys navigable. Missing keys fall
// back to the Japanese entry, then to the raw key itself -- t() never
// throws, matching this app's existing fail-soft philosophy (a missing
// translation should degrade to *something visible*, not break the page).

const LANGUAGE_KEY = "adsb-analytics:language";
const DEFAULT_LANGUAGE = "ja";

export function getLanguage() {
  try {
    const raw = localStorage.getItem(LANGUAGE_KEY);
    return raw === "en" ? "en" : DEFAULT_LANGUAGE;
  } catch (err) {
    console.error("failed to read language setting from localStorage", err);
    return DEFAULT_LANGUAGE;
  }
}

export function setLanguage(lang) {
  try {
    localStorage.setItem(LANGUAGE_KEY, lang === "en" ? "en" : "ja");
  } catch (err) {
    console.error("failed to persist language setting to localStorage", err);
  }
}

// Locale string for Intl/toLocaleString-family calls elsewhere (ui.js's
// formatTime, chart.js's formatAxisTime, rawdata.js's formatNowTime,
// daily.js's thousands-separator formatting) -- centralized here so
// there's one place deciding "en" -> "en-US".
export function currentLocale() {
  return getLanguage() === "en" ? "en-US" : "ja-JP";
}

const DICT = {
  ja: {
    // --- shared nav (identical across all 8 pages) ---
    "nav.aria": "ページ",
    "nav.dashboard": "ダッシュボード",
    "nav.daily": "今日の空",
    "nav.receiver": "受信性能",
    "nav.trackMap": "航跡地図",
    "nav.globe": "3D航跡",
    "nav.history": "機体履歴",
    "nav.rawdata": "生データ",
    "nav.settings": "設定",

    // --- settings page ---
    "settings.pageTitle": "設定 - ADS-B Analytics",
    "settings.title": "設定",
    "settings.units.header": "表示単位",
    "settings.localOnly": "この端末のブラウザにのみ保存されます(サーバーには送信されません)。既に開いているタブには反映されません -- 再読み込みしてください。",
    "settings.distanceUnit": "距離の単位",
    "settings.distanceUnit.km": "キロメートル (km)",
    "settings.distanceUnit.nm": "海里 (nm)",
    "settings.altitudeUnit": "高度の単位",
    "settings.altitudeUnit.ft": "フィート (ft)",
    "settings.altitudeUnit.m": "メートル (m)",
    "settings.language": "言語 / Language",
    "settings.language.ja": "日本語",
    "settings.language.en": "English",
    "settings.track.header": "3D航跡",
    "settings.track.opacity": "航跡ラインの透明度:",
    "settings.theme.header": "テーマ",
    "settings.theme.dark": "ダーク",
    "settings.theme.light": "ライト",
    "settings.dashboard.header": "ダッシュボード表示",
    "settings.browserNotify.header": "お気に入り機体のブラウザ通知",
    "settings.browserNotify.description":
      "航跡地図・3D航跡のライブ表示中に、お気に入り登録した機体が現れたらブラウザ通知します。",
    "settings.browserNotify.requestPermission": "通知の許可をリクエスト",
    "settings.browserNotify.permission.default": "通知許可: 未設定",
    "settings.browserNotify.permission.granted": "通知許可: 許可済み",
    "settings.browserNotify.permission.denied": "通知許可: 拒否されています",
    "settings.browserNotify.permission.unsupported": "通知許可: このブラウザでは未対応",
    "settings.speech.header": "スポッターラジオ風読み上げ",
    "settings.speech.description":
      "航跡地図・3D航跡のライブ表示中に、新しく現れた機体をブラウザの音声合成で読み上げます。",
    "settings.speech.off": "オフ",
    "settings.speech.on": "オン",

    // --- ui.js (status badge, footer, generic API-error text) ---
    "ui.ingestionState.ok": "正常",
    "ui.ingestionState.stale": "データ取得停止中",
    "ui.ingestionState.error": "取得エラー",
    "ui.ingestionState.no_data": "データなし",
    "ui.footerLastFetch": "最終取得: {time}",
    "ui.apiError": "APIエラー",

    // --- shared across pages ---
    "common.noData": "データがありません",
    "common.aircraft": "機体",

    // --- daily.js / daily.html ---
    "daily.pageTitle": "今日の空 - ADS-B Analytics",
    "daily.targetDay": "対象日:",
    "daily.todayStatus": "今日の状況",
    "daily.card.unique": "ユニーク機数",
    "daily.card.concurrent": "最大同時受信数",
    "daily.card.messages": "メッセージ数",
    "daily.card.positionMax": "位置取得最大数",
    "daily.aircraftTypeHeading": "機種別 機数 (Top10)",
    "daily.aircraftTypeEmpty": "機種データはまだありません(adsb-daily-rollupが未実行の機体は集計対象外です)",
    "daily.todayRanking": "今日のランキング",
    "daily.farthest": "最遠",
    "daily.closest": "最接近",
    "daily.mostObserved": "最多観測",
    "daily.fastest": "最高速度",
    "daily.highest": "最高高度",
    "daily.firstSeenTodayHeading": "本日初観測の機体",
    "daily.firstSeenTodayCaption": "今日はじめて観測した機体",
    "daily.firstSeenTime": "初観測時刻",
    "daily.firstSeenTodayEmpty": "今日はまだ新規機体はありません",
    "daily.trendHeading": "直近7日間のユニーク機数トレンド",
    "daily.timesObserved": "{count}回観測",
    "daily.deltaVsYesterday": "前日比",
    "daily.deltaVsLastWeek": "先週同曜日比",
    "daily.period.heading": "月次・年次サマリー",
    "daily.period.month": "月次",
    "daily.period.year": "年次",
    "daily.period.show": "表示",
    "daily.period.summaryLine":
      "データがある日数: {days}日 / ユニーク機数: {unique}機 / メッセージ数: {messages} / " +
      "最大同時受信数: {concurrent}機 / 最遠: {farthest}",

    "common.altitudeUnknown": "高度不明",

    // --- chart.js ---
    "chart.initFailed": "グラフの初期化に失敗しました。",
    "chart.renderFailed": "グラフの描画に失敗しました。",
    "chart.active": "受信中",
    "chart.positionAcquired": "位置取得中",
    "chart.trafficFetchFailed": "交通量データの取得に失敗しました。",

    // --- map.js / fullmap.js ---
    "map.unknownError": "詳細不明のエラー",
    "map.webglUnavailable": "このブラウザ/環境ではWebGLが利用できないため地図を表示できません(グラフ・ランキングは利用できます)。リモートデスクトップ/VM環境やWebGL無効化設定が原因のことがあります。",
    "map.initFailed": "地図の初期化に失敗しました: {detail}(グラフ・ランキングは利用できます)",
    "map.loadTimeout": "地図の読み込みがタイムアウトしました({seconds}秒)。スタイルURL({styleUrl})への通信を確認してください。グラフ・ランキングは利用できます。",
    "map.dataFetchFailed": "地図データの取得に失敗しました: {detail}(グラフ・ランキングは利用できます)",
    "map.tracksFetchFailed": "航跡データの取得に失敗しました。",

    // --- globe.js ---
    "globe.initFailed": "3D表示の初期化に失敗しました: {detail}(WebGLが利用できない環境の可能性があります)",
    "globe.tracksFetchFailed": "過去航跡の取得に失敗しました。",
    "globe.followRequiresIsolate": "カメラ自動追従には、先に機体をShift+クリックしてください。",
    "globe.liveConnectionError": "ライブ接続エラー",

    // --- rawdata.js ---
    "rawdata.resume": "再開",
    "rawdata.pause": "一時停止",
    "rawdata.connecting": "接続中…",
    "rawdata.connected": "接続中",
    "rawdata.disconnected": "切断されました。{seconds}秒後に再接続します…",
    "rawdata.connectionError": "接続エラー",

    // --- shared bands (altitude-legend.js, main.js heatmap filter, receiver.js) ---
    "bands.ground": "地上/低高度",
    "bands.low": "低高度",
    "bands.mid": "中高度",
    "bands.high": "高高度",
    "bands.very_high": "超高高度",

    // --- shared day-of-week (main.js heatmap filter) ---
    "common.dow.0": "日曜",
    "common.dow.1": "月曜",
    "common.dow.2": "火曜",
    "common.dow.3": "水曜",
    "common.dow.4": "木曜",
    "common.dow.5": "金曜",
    "common.dow.6": "土曜",

    "common.distance": "距離",
    "common.altitude": "高度",
    "common.observedAt": "観測時刻",

    // --- main.js / index.html ---
    "index.pageTitle": "ADS-B Analytics",
    "index.loading": "読み込み中…",
    "index.lastUpdated": "最終更新:",
    "index.trackPeriod": "航跡表示期間",
    "index.currentStatus": "現在の状況",
    "index.card.active": "現在受信中",
    "index.card.position": "位置取得中",
    "index.card.unique24h": "24時間ユニーク機数",
    "index.card.lastFetch": "最終取得成功",
    "index.trackMapHeading": "航跡地図",
    "index.heatmapSettings": "ヒートマップ設定",
    "index.heatmap": "ヒートマップ",
    "index.heatmapAltitudeFilter": "高度帯フィルタ",
    "index.heatmapHourFilter": "時間帯フィルタ",
    "index.heatmapDowFilter": "曜日フィルタ",
    "index.trafficHeading": "交通量",
    "index.granularity": "表示粒度",
    "index.granularity.day": "日",
    "index.granularity.week": "週",
    "index.granularity.month": "月",
    "index.csvDownload": "CSVダウンロード",
    "index.statisticalPatterns": "統計パターン",
    "index.hourOfDayHeading": "時間帯別ユニーク機数(直近7日)",
    "index.altitudeHistHeading": "高度分布(24時間)",
    "index.speedHistHeading": "速度分布(24時間)",
    "index.rankingsAndRecent": "ランキングと最近の機体",
    "index.farthestCaption": "受信局から最も遠い機体",
    "index.closestCaption": "受信局に最も近づいた機体",
    "index.recentAircraft": "最近観測した機体",
    "index.recentAircraftCaption": "最終観測時刻が新しい機体",
    "index.firstSeen": "初観測",
    "index.lastSeen": "最終観測",

    "main.cspBlocked": "CSPにより読み込みがブロックされました: {blockedURI}(directive: {directive})",
    "main.cspBlockedSuffix": "{detail} -- ブラウザの拡張機能やセキュリティソフトが関与している可能性があります。",
    "map.moduleLoadFailed": "地図モジュールの読み込みに失敗しました: {detail}",
    "map.jsFetchFailed": "map.jsの取得に失敗しました (HTTP {status})",
    "map.jsNetworkFailed": "map.jsへのネットワーク接続に失敗しました: {detail}",
    "main.otherDataAvailable": "(他の情報は利用できます)",
    "main.hourLabel": "{hour}時",
    "main.heatmap.allAltitudes": "高度: 全て",
    "main.heatmap.allHours": "時間帯: 全て",
    "main.heatmap.hourOption": "{hour}時台",
    "main.heatmap.allDaysOfWeek": "曜日: 全て",

    // --- altitude-legend.js ---
    "altitudeLegend.upTo": "{value}以下",
    "altitudeLegend.above": "{value}超",

    // --- receiver.js / receiver.html ---
    "receiver.pageTitle": "受信性能 - ADS-B Analytics",
    "receiver.period": "集計期間",
    "receiver.period.7d": "7日",
    "receiver.period.30d": "30日",
    "receiver.bearingHeading": "方位別受信距離",
    "receiver.altitudeHeading": "高度帯別受信距離",
    "receiver.receptionHeading": "メッセージ数・位置取得率の推移",
    "receiver.rssiHeading": "距離別受信強度(RSSI)ヒートマップ",
    "receiver.rssiCount": "件数",
    "receiver.messageCount": "メッセージ数",
    "receiver.positionRate": "位置取得率(%)",
    "receiver.dayNightHeading": "昼夜別受信距離",
    "receiver.weeklyTrendHeading": "週次トレンド(ユニーク機数)",
    "receiver.dayNightSummary": "昼間の最大到達距離: {day} / 夜間の最大到達距離: {night}",
    "receiver.metarSummary": "現在の気象({station}): {raw}",

    // --- history.js / history.html ---
    "history.pageTitle": "機体履歴 - ADS-B Analytics",
    "history.detailHeading": "機体詳細",
    "history.backToList": "一覧に戻る",
    "history.mostFrequent": "最頻観測機体",
    "history.period.30d": "30日",
    "history.period.90d": "90日",
    "history.favoritesOnly": "お気に入りのみ",
    "history.frequentCaption": "直近N日間で最も多く観測された機体",
    "history.favorite": "お気に入り",
    "history.daysObserved": "観測日数",
    "history.totalPasses": "総パス数",
    "history.favoriteToggle": "{icao}をお気に入りに追加/削除",
    "history.viewInfoAndPhoto": "機体情報・写真を見る",
    "history.daysUnit": "{count}日",
    "history.passesUnit": "{count}回",
    "history.callsignHistory": "コールサイン履歴",
    "history.notFound": "機体が見つかりません。",
    "history.fetchFailed": "機体情報の取得に失敗しました。",
    "history.onThisDay.heading": "n年前の今日",
    "history.onThisDay.empty": "過去の同じ日に観測記録はありません。",
    "history.onThisDay.yearsAgo": "{year}年({count}年前)",

    // --- shared controls (fullmap.html + globe.html header) ---
    "trackControls.modeGroupLabel": "表示モード",
    "trackControls.aircraftGroupLabel": "表示機体",
    "trackControls.live": "ライブ",
    "trackControls.historyLabel": "過去",
    "trackControls.aircraftPicker": "機体選択 ▾",
    "trackControls.showAll": "すべて表示",
    "trackControls.hideAll": "すべて非表示",
    "trackControls.refreshList": "一覧更新",
    "trackControls.fastMode": "更新頻度: 1秒",
    "trackControls.exitIsolate": "全機体表示に戻す",

    // --- fullmap.js / fullmap.html ---
    "fullmap.pageTitle": "航跡地図 - ADS-B Analytics",
    "fullmap.mapAriaLabel": "航跡地図",
    "fullmap.description":
      "「ライブ」表示中は現在受信中の全機体を機種カテゴリ別のアイコン(高度帯で色分け)で表示し、" +
      "各機体の過去の軌跡とライブ延伸中の軌跡(高度帯で色分け)も重ねて表示します。" +
      "アイコンをクリックすると詳細サイドパネルを開きます。「機体選択」で表示する機体を絞り込めます。" +
      "スライダー(1時間単位、最大72時間)で過去の航跡表示に切り替えられます。",

    // --- globe.js / globe.html ---
    "globe.pageTitle": "3D航跡 - ADS-B Analytics",
    "globe.followToggle": "カメラ自動追従",
    "globe.description.pre": "衛星画像(",
    "globe.description.post":
      ", Maxar, Earthstar Geographics, GIS User Community)を背景に、現在受信中の全機体を3D機体モデルで" +
      "高度別に色分けしてライブ表示します(機首方向・傾きも可能な範囲で反映)。各機体は過去の軌跡(実線)と" +
      "ライブ延伸中の軌跡(透明度は設定タブで変更可)を重ねて表示します。機体をクリックすると詳細サイド" +
      "パネルを開きます。Shift+クリックでその機体だけを表示します(もう一度Shift+クリックか" +
      "「全機体表示に戻す」で解除)。「更新頻度: 1秒」でライブ更新をより高頻度に。" +
      "スライダー(15分単位、最大24時間)で過去の航跡のみを全機体分表示し(3D機体モデルは表示されません)、" +
      "航跡にカーソルを合わせると機体情報がポップアップします。ドラッグで回転、スクロールでズームできます。" +
      "データはサーバーに保存されません。",

    // --- rawdata.js / rawdata.html ---
    "rawdata.pageTitle": "生データ - ADS-B Analytics",
    "rawdata.heading": "生データ (Beastストリーム)",
    "rawdata.description":
      "readsbの生のBeastフォーマットストリームを表示しています。サーバーには保存されません" +
      "(ブラウザを閉じれば消えます)。DF/ICAO/種別は簡易デコードです — 位置・速度などの本格的な" +
      "デコードはreadsb自身が正しく行っているものをこのダッシュボードの他のページで表示しています。" +
      "フィルタは表示のみに影響し、受信・保持するフレーム数(最大5000件)には影響しません。",
    "rawdata.filterGroupLabel": "フィルタ",
    "rawdata.filterPlaceholder": "ICAOでフィルタ",
    "rawdata.msgTypeFilter": "種類で絞り込み ▾",
    "rawdata.displayControlGroupLabel": "表示制御",
    "rawdata.clear": "クリア",
    "rawdata.tableCaption": "受信した生のBeastフレーム",
    "rawdata.col.time": "時刻",
    "rawdata.col.type": "種別",
    "rawdata.col.df": "DF",
    "rawdata.col.icao": "ICAO",
    "rawdata.col.ca": "CA",
    "rawdata.col.msgType": "メッセージ種類",
    "rawdata.col.hex": "生データ (hex)",
    "rawdata.frameCountPre": "フレーム (直近",
    "rawdata.frameCountPost": "件、最大5000件)",
    "rawdata.emptyState": "まだフレームを受信していません…",

    // --- squawk-alert.js (shared emergency-squawk banner) ---
    "squawkAlert.entry": "🚨 {label} (squawk {squawk})",

    // --- transit-alert.js (shared sun-transit toast) ---
    "transitAlert.message": "☀️ {label} が太陽の前を通過中です",

    // --- speech.js (spotter-radio announcements) ---
    "speech.announcement": "{label}、受信しました",

    // --- browser-notify.js (favorite aircraft browser notifications) ---
    "browserNotify.title": "お気に入り機体を検知",
    "browserNotify.body": "{label} を受信中です",

    // --- highlight-image.js (daily.html "save as image") ---
    "highlightImage.saveButton": "画像として保存",
    "highlightImage.title": "今日の空のハイライト",

    // --- aircraftinfo.js (shared aircraft-detail sidebar) ---
    "aircraftinfo.close": "閉じる",
    "aircraftinfo.icaoLabel": "ICAO: {icao}",
    "aircraftinfo.downloadGpx": "GPXダウンロード",
    "aircraftinfo.downloadKml": "KMLダウンロード",
    "aircraftinfo.notFound": "機体情報は見つかりませんでした(adsbdb.com)",
    "aircraftinfo.photoAlt": "機体写真",
    "aircraftinfo.noPhoto": "写真は見つかりませんでした(Planespotters.net)",
    "aircraftinfo.photoCredit": "撮影: {photographer} (Planespotters.net)",
    "aircraftinfo.ownDataSection": "自局データ",
    "aircraftinfo.noOwnData": "自局での観測データはまだありません",
    "aircraftinfo.groundSpeed": "地速",
    "aircraftinfo.verticalRate": "昇降率",
    "aircraftinfo.bearing": "方位",
    "aircraftinfo.noLiveData": "現在readsbから受信していません",
    "aircraftinfo.squawk": "スコーク",
    "aircraftinfo.lastPosition": "最終位置",
    "aircraftinfo.secondsAgoSuffix": " 秒前",
    "aircraftinfo.baroAltitude": "気圧高度",
    "aircraftinfo.geomAltitude": "幾何高度",
    "aircraftinfo.iasTasLabel": "対気速度(IAS/TAS)",
    "aircraftinfo.mach": "マッハ",
    "aircraftinfo.trackMagHeading": "Track / 磁方位",
    "aircraftinfo.roll": "ロール",
    "aircraftinfo.verticalRateBaroGeom": "昇降率(baro/geom)",
    "aircraftinfo.category": "カテゴリ",
    "aircraftinfo.fmsSection": "FMS選択値",
    "aircraftinfo.selectedAltitude": "選択高度",
    "aircraftinfo.selectedHeading": "選択方位",
    "aircraftinfo.accuracySection": "精度指標(ACCURACY)",
    "aircraftinfo.windTempSection": "風・気温",
    "aircraftinfo.windDirSpeed": "風向/風速",
    "aircraftinfo.ownDataFetchFailed": "自局データの取得に失敗しました",
    "aircraftinfo.noOwnDataFound": "自局での観測データはありません",
    "aircraftinfo.liveDisconnected": "ライブ接続が切断されました",
    "aircraftinfo.liveError": "ライブ接続エラー",

    // --- nationality.js / flags.js / flags.html ---
    "nationality.country.IT": "イタリア",
    "nationality.country.ES": "スペイン",
    "nationality.country.FR": "フランス",
    "nationality.country.DE": "ドイツ",
    "nationality.country.GB": "イギリス",
    "nationality.country.NL": "オランダ",
    "nationality.country.AF": "アフガニスタン",
    "nationality.country.KR": "韓国",
    "nationality.country.MY": "マレーシア",
    "nationality.country.PH": "フィリピン",
    "nationality.country.SG": "シンガポール",
    "nationality.country.CN": "中国",
    "nationality.country.AU": "オーストラリア",
    "nationality.country.IN": "インド",
    "nationality.country.JP": "日本",
    "nationality.country.TH": "タイ",
    "nationality.country.VN": "ベトナム",
    "nationality.country.TW": "台湾",
    "nationality.country.ID": "インドネシア",
    "nationality.country.US": "アメリカ合衆国",
    "nationality.country.CA": "カナダ",
    "nationality.country.NZ": "ニュージーランド",

    "nav.flags": "フラッグコレクション",
    "nav.badges": "実績バッジ",
    "nav.archive": "機体アーカイブ",
    "nav.searchPlaceholder": "ICAO / コールサイン検索",
    "flags.pageTitle": "フラッグコレクション - ADS-B Analytics",
    "flags.heading": "フラッグコレクション",
    "flags.description":
      "これまでに観測した全機体を、ICAO24bitアドレスから推定した国籍別に集計したものです" +
      "(推定は主要な航空国を中心とした簡易的なブロック表によるもので、全ての国をカバーしている" +
      "わけではありません)。",
    "flags.empty": "まだ国籍を推定できた機体がありません。",
    "flags.aircraftCount": "{count}機",
    "flags.firstSeen": "初観測: {date}",
    "flags.fetchFailed": "国籍データの取得に失敗しました。",

    // --- badges.js / badges.html ---
    "badges.pageTitle": "実績バッジ - ADS-B Analytics",
    "badges.heading": "実績バッジ",
    "badges.description":
      "これまでの観測記録から自動的に判定される実績です。データを都度再計算しているだけで、" +
      "達成日時などは記録していません。",
    "badges.fetchFailed": "実績データの取得に失敗しました。",
    "badges.progress": "現在: {value}",
    "badges.first_contact.name": "はじめての機体",
    "badges.first_contact.description": "最初の機体を観測しました",
    "badges.aircraft_100.name": "100機達成",
    "badges.aircraft_100.description": "累計100機を観測しました",
    "badges.aircraft_500.name": "500機達成",
    "badges.aircraft_500.description": "累計500機を観測しました",
    "badges.aircraft_1000.name": "1000機達成",
    "badges.aircraft_1000.description": "累計1000機を観測しました",
    "badges.types_10.name": "機種図鑑(10種)",
    "badges.types_10.description": "10種類の機種を識別しました",
    "badges.types_50.name": "機種図鑑(50種)",
    "badges.types_50.description": "50種類の機種を識別しました",
    "badges.types_100.name": "機種図鑑(100種)",
    "badges.types_100.description": "100種類の機種を識別しました",
    "badges.far_catch.name": "遠距離キャッチ",
    "badges.far_catch.description": "300km以上先の機体を受信しました",
    "badges.frequent_flyer.name": "常連さん",
    "badges.frequent_flyer.description": "同じ機体を合計50回以上観測しました",
    "badges.callsign_collector.name": "コールサイン収集家",
    "badges.callsign_collector.description": "同じ機体で5つ以上のコールサインを記録しました",
    "badges.favorite_collector.name": "お気に入りコレクター",
    "badges.favorite_collector.description": "5機以上をお気に入り登録しました",
    "badges.veteran_month.name": "1ヶ月選手",
    "badges.veteran_month.description": "30日分のデータが蓄積されました",
    "badges.veteran_year.name": "1年選手",
    "badges.veteran_year.description": "365日分のデータが蓄積されました",
    "badges.busy_sky.name": "混雑した空",
    "badges.busy_sky.description": "同時に20機以上を受信しました",

    // --- archive.js / archive.html ---
    "archive.pageTitle": "機体アーカイブ - ADS-B Analytics",
    "archive.filterGroupLabel": "検索・並び替え",
    "archive.searchPlaceholder": "ICAO / コールサイン",
    "archive.sort.lastSeen": "最終観測",
    "archive.sort.firstSeen": "初観測",
    "archive.sort.daysObserved": "観測日数",
    "archive.sort.totalPasses": "総パス数",
    "archive.sort.icao": "ICAO",
    "archive.col.icao": "ICAO",
    "archive.col.firstSeen": "初観測",
    "archive.col.lastSeen": "最終観測",
    "archive.prev": "前へ",
    "archive.next": "次へ",
    "archive.pageInfo": "{from}〜{to} / 全{total}件",
  },
  en: {
    "nav.aria": "Pages",
    "nav.dashboard": "Dashboard",
    "nav.daily": "Today's Sky",
    "nav.receiver": "Receiver Performance",
    "nav.trackMap": "Track Map",
    "nav.globe": "3D Tracks",
    "nav.history": "Aircraft History",
    "nav.rawdata": "Raw Data",
    "nav.settings": "Settings",

    "settings.pageTitle": "Settings - ADS-B Analytics",
    "settings.title": "Settings",
    "settings.units.header": "Display Units",
    "settings.localOnly": "Stored only in this browser (never sent to the server). Already-open tabs won't pick this up -- reload to apply.",
    "settings.distanceUnit": "Distance unit",
    "settings.distanceUnit.km": "Kilometers (km)",
    "settings.distanceUnit.nm": "Nautical miles (nm)",
    "settings.altitudeUnit": "Altitude unit",
    "settings.altitudeUnit.ft": "Feet (ft)",
    "settings.altitudeUnit.m": "Meters (m)",
    "settings.language": "言語 / Language",
    "settings.language.ja": "日本語",
    "settings.language.en": "English",
    "settings.track.header": "3D Tracks",
    "settings.track.opacity": "Track line opacity:",
    "settings.theme.header": "Theme",
    "settings.theme.dark": "Dark",
    "settings.theme.light": "Light",
    "settings.dashboard.header": "Dashboard Layout",
    "settings.browserNotify.header": "Favorite Aircraft Browser Notifications",
    "settings.browserNotify.description":
      "Sends a browser notification when a favorited aircraft appears while the track map or " +
      "3D globe's live view is open.",
    "settings.browserNotify.requestPermission": "Request notification permission",
    "settings.browserNotify.permission.default": "Notification permission: not set",
    "settings.browserNotify.permission.granted": "Notification permission: granted",
    "settings.browserNotify.permission.denied": "Notification permission: denied",
    "settings.browserNotify.permission.unsupported": "Notification permission: not supported here",
    "settings.speech.header": "Spotter Radio Announcements",
    "settings.speech.description":
      "Announces newly-appeared aircraft via the browser's speech synthesis while the track " +
      "map or 3D globe's live view is open.",
    "settings.speech.off": "Off",
    "settings.speech.on": "On",

    "ui.ingestionState.ok": "OK",
    "ui.ingestionState.stale": "Data stopped",
    "ui.ingestionState.error": "Fetch error",
    "ui.ingestionState.no_data": "No data",
    "ui.footerLastFetch": "Last fetched: {time}",
    "ui.apiError": "API error",

    "common.noData": "No data available",
    "common.aircraft": "Aircraft",

    "daily.pageTitle": "Today's Sky - ADS-B Analytics",
    "daily.targetDay": "Date:",
    "daily.todayStatus": "Today's status",
    "daily.card.unique": "Unique aircraft",
    "daily.card.concurrent": "Max concurrent",
    "daily.card.messages": "Messages",
    "daily.card.positionMax": "Max with position",
    "daily.aircraftTypeHeading": "Aircraft types (Top 10)",
    "daily.aircraftTypeEmpty": "No aircraft type data yet (aircraft not yet processed by adsb-daily-rollup are excluded)",
    "daily.todayRanking": "Today's rankings",
    "daily.farthest": "Farthest",
    "daily.closest": "Closest",
    "daily.mostObserved": "Most observed",
    "daily.fastest": "Fastest",
    "daily.highest": "Highest",
    "daily.firstSeenTodayHeading": "First seen today",
    "daily.firstSeenTodayCaption": "Aircraft first observed today",
    "daily.firstSeenTime": "First seen at",
    "daily.firstSeenTodayEmpty": "No new aircraft yet today",
    "daily.trendHeading": "Unique aircraft trend (last 7 days)",
    "daily.timesObserved": "Observed {count}x",
    "daily.deltaVsYesterday": "vs. yesterday",
    "daily.deltaVsLastWeek": "vs. last week (same weekday)",
    "daily.period.heading": "Monthly / Yearly Summary",
    "daily.period.month": "Monthly",
    "daily.period.year": "Yearly",
    "daily.period.show": "Show",
    "daily.period.summaryLine":
      "Days with data: {days} / Unique aircraft: {unique} / Messages: {messages} / " +
      "Max concurrent: {concurrent} / Farthest: {farthest}",

    "common.altitudeUnknown": "Altitude unknown",

    "chart.initFailed": "Failed to initialize the chart.",
    "chart.renderFailed": "Failed to render the chart.",
    "chart.active": "Active",
    "chart.positionAcquired": "Position acquired",
    "chart.trafficFetchFailed": "Failed to fetch traffic data.",

    "map.unknownError": "Unknown error",
    "map.webglUnavailable": "The map can't be shown because WebGL isn't available in this browser/environment (the chart and rankings still work). This is often caused by a remote desktop/VM without GPU passthrough, or WebGL disabled in browser settings.",
    "map.initFailed": "Failed to initialize the map: {detail} (the chart and rankings still work).",
    "map.loadTimeout": "Map loading timed out ({seconds}s). Check connectivity to the style URL ({styleUrl}). The chart and rankings still work.",
    "map.dataFetchFailed": "Failed to fetch map data: {detail} (the chart and rankings still work).",
    "map.tracksFetchFailed": "Failed to fetch track data.",

    "globe.initFailed": "Failed to initialize the 3D view: {detail} (WebGL may not be available in this environment).",
    "globe.tracksFetchFailed": "Failed to fetch past tracks.",
    "globe.followRequiresIsolate": "To auto-follow the camera, Shift+click an aircraft first.",
    "globe.liveConnectionError": "Live connection error",

    "rawdata.resume": "Resume",
    "rawdata.pause": "Pause",
    "rawdata.connecting": "Connecting…",
    "rawdata.connected": "Connected",
    "rawdata.disconnected": "Disconnected. Reconnecting in {seconds}s…",
    "rawdata.connectionError": "Connection error",

    "bands.ground": "Ground/Low",
    "bands.low": "Low",
    "bands.mid": "Mid",
    "bands.high": "High",
    "bands.very_high": "Very high",

    "common.dow.0": "Sunday",
    "common.dow.1": "Monday",
    "common.dow.2": "Tuesday",
    "common.dow.3": "Wednesday",
    "common.dow.4": "Thursday",
    "common.dow.5": "Friday",
    "common.dow.6": "Saturday",

    "common.distance": "Distance",
    "common.altitude": "Altitude",
    "common.observedAt": "Observed at",

    "index.pageTitle": "ADS-B Analytics",
    "index.loading": "Loading…",
    "index.lastUpdated": "Last updated:",
    "index.trackPeriod": "Track display period",
    "index.currentStatus": "Current status",
    "index.card.active": "Currently received",
    "index.card.position": "Position acquired",
    "index.card.unique24h": "Unique aircraft (24h)",
    "index.card.lastFetch": "Last successful fetch",
    "index.trackMapHeading": "Track Map",
    "index.heatmapSettings": "Heatmap settings",
    "index.heatmap": "Heatmap",
    "index.heatmapAltitudeFilter": "Altitude band filter",
    "index.heatmapHourFilter": "Hour-of-day filter",
    "index.heatmapDowFilter": "Day-of-week filter",
    "index.trafficHeading": "Traffic",
    "index.granularity": "Granularity",
    "index.granularity.day": "Day",
    "index.granularity.week": "Week",
    "index.granularity.month": "Month",
    "index.csvDownload": "Download CSV",
    "index.statisticalPatterns": "Statistical patterns",
    "index.hourOfDayHeading": "Unique aircraft by hour of day (last 7 days)",
    "index.altitudeHistHeading": "Altitude distribution (24h)",
    "index.speedHistHeading": "Speed distribution (24h)",
    "index.rankingsAndRecent": "Rankings and recent aircraft",
    "index.farthestCaption": "Aircraft farthest from the receiver",
    "index.closestCaption": "Aircraft that came closest to the receiver",
    "index.recentAircraft": "Recently observed aircraft",
    "index.recentAircraftCaption": "Aircraft with the most recent last-seen time",
    "index.firstSeen": "First seen",
    "index.lastSeen": "Last seen",

    "main.cspBlocked": "Blocked by Content-Security-Policy: {blockedURI} (directive: {directive})",
    "main.cspBlockedSuffix": "{detail} -- a browser extension or security software may be involved.",
    "map.moduleLoadFailed": "Failed to load the map module: {detail}",
    "map.jsFetchFailed": "Failed to fetch map.js (HTTP {status})",
    "map.jsNetworkFailed": "Network error fetching map.js: {detail}",
    "main.otherDataAvailable": " (other data is still available).",
    "main.hourLabel": "{hour}:00",
    "main.heatmap.allAltitudes": "Altitude: All",
    "main.heatmap.allHours": "Hour: All",
    "main.heatmap.hourOption": "{hour}:00",
    "main.heatmap.allDaysOfWeek": "Day: All",

    "altitudeLegend.upTo": "Up to {value}",
    "altitudeLegend.above": "Above {value}",

    "receiver.pageTitle": "Receiver Performance - ADS-B Analytics",
    "receiver.period": "Aggregation period",
    "receiver.period.7d": "7 days",
    "receiver.period.30d": "30 days",
    "receiver.bearingHeading": "Max range by bearing",
    "receiver.altitudeHeading": "Max range by altitude band",
    "receiver.receptionHeading": "Messages / position-acquisition rate over time",
    "receiver.rssiHeading": "Signal strength (RSSI) by distance heatmap",
    "receiver.rssiCount": "Count",
    "receiver.messageCount": "Messages",
    "receiver.positionRate": "Position rate (%)",
    "receiver.dayNightHeading": "Day/Night Reception Range",
    "receiver.weeklyTrendHeading": "Weekly Trend (Unique Aircraft)",
    "receiver.dayNightSummary": "Max daytime range: {day} / Max nighttime range: {night}",
    "receiver.metarSummary": "Current weather ({station}): {raw}",

    "history.pageTitle": "Aircraft History - ADS-B Analytics",
    "history.detailHeading": "Aircraft detail",
    "history.backToList": "Back to list",
    "history.mostFrequent": "Most frequently observed aircraft",
    "history.period.30d": "30 days",
    "history.period.90d": "90 days",
    "history.favoritesOnly": "Favorites only",
    "history.frequentCaption": "Aircraft observed most often in the last N days",
    "history.favorite": "Favorite",
    "history.daysObserved": "Days observed",
    "history.totalPasses": "Total passes",
    "history.favoriteToggle": "Add/remove {icao} from favorites",
    "history.viewInfoAndPhoto": "View aircraft info & photo",
    "history.daysUnit": "{count} days",
    "history.passesUnit": "{count}x",
    "history.callsignHistory": "Callsign history",
    "history.notFound": "Aircraft not found.",
    "history.fetchFailed": "Failed to fetch aircraft information.",
    "history.onThisDay.heading": "On This Day",
    "history.onThisDay.empty": "No observations on this same calendar date in past years.",
    "history.onThisDay.yearsAgo": "{year} ({count} years ago)",

    "trackControls.modeGroupLabel": "Display mode",
    "trackControls.aircraftGroupLabel": "Aircraft shown",
    "trackControls.live": "Live",
    "trackControls.historyLabel": "History",
    "trackControls.aircraftPicker": "Select aircraft ▾",
    "trackControls.showAll": "Show all",
    "trackControls.hideAll": "Hide all",
    "trackControls.refreshList": "Refresh list",
    "trackControls.fastMode": "Update rate: 1s",
    "trackControls.exitIsolate": "Show all aircraft again",

    "fullmap.pageTitle": "Track Map - ADS-B Analytics",
    "fullmap.mapAriaLabel": "Track map",
    "fullmap.description":
      "While in \"Live\" mode, every currently received aircraft is shown as a category icon " +
      "(colored by altitude band), each drawing its own historical track plus its live-extending " +
      "track (also colored by altitude band). Click an icon to open the detail side panel. " +
      "Use \"Select aircraft\" to filter which aircraft are shown. Use the slider (1-hour steps, " +
      "up to 72 hours) to switch to a past-track view.",

    "globe.pageTitle": "3D Tracks - ADS-B Analytics",
    "globe.followToggle": "Auto-follow camera",
    "globe.description.pre": "Satellite imagery (",
    "globe.description.post":
      ", Maxar, Earthstar Geographics, GIS User Community) shown as the backdrop, with every " +
      "currently received aircraft live-rendered as a 3D aircraft model colored by altitude band " +
      "(heading and, where possible, pitch/roll are reflected). Each aircraft draws its past track " +
      "(solid line) plus its live-extending track (opacity adjustable in the Settings tab). Click an " +
      "aircraft to open the detail side panel. Shift+click to show only that aircraft (Shift+click " +
      "again, or \"Show all aircraft again\", to undo). \"Update rate: 1s\" makes live updates more " +
      "frequent. The slider (15-minute steps, up to 24 hours) shows only past tracks for every " +
      "aircraft (no 3D models); hover a track to pop up aircraft info. Drag to rotate, scroll to " +
      "zoom. No data is stored on the server.",

    "rawdata.pageTitle": "Raw Data - ADS-B Analytics",
    "rawdata.heading": "Raw Data (Beast stream)",
    "rawdata.description":
      "Shows readsb's raw Beast-format stream. Nothing is stored on the server (it's lost when you " +
      "close the browser). DF/ICAO/type are a simple decode -- the real decoding of position, " +
      "velocity, etc. is done correctly by readsb itself and shown on this dashboard's other pages. " +
      "The filter only affects what's displayed; it doesn't affect how many frames are received or " +
      "kept (up to 5000).",
    "rawdata.filterGroupLabel": "Filter",
    "rawdata.filterPlaceholder": "Filter by ICAO",
    "rawdata.msgTypeFilter": "Filter by type ▾",
    "rawdata.displayControlGroupLabel": "Display controls",
    "rawdata.clear": "Clear",
    "rawdata.tableCaption": "Received raw Beast frames",
    "rawdata.col.time": "Time",
    "rawdata.col.type": "Type",
    "rawdata.col.df": "DF",
    "rawdata.col.icao": "ICAO",
    "rawdata.col.ca": "CA",
    "rawdata.col.msgType": "Message type",
    "rawdata.col.hex": "Raw data (hex)",
    "rawdata.frameCountPre": "Frames (last ",
    "rawdata.frameCountPost": ", max 5000)",
    "rawdata.emptyState": "No frames received yet…",

    "squawkAlert.entry": "🚨 {label} (squawk {squawk})",

    "transitAlert.message": "☀️ {label} is passing in front of the sun",

    "speech.announcement": "Now receiving {label}",

    "browserNotify.title": "Favorite aircraft detected",
    "browserNotify.body": "Now receiving {label}",

    "highlightImage.saveButton": "Save as image",
    "highlightImage.title": "Today's Sky Highlights",

    "aircraftinfo.close": "Close",
    "aircraftinfo.icaoLabel": "ICAO: {icao}",
    "aircraftinfo.downloadGpx": "Download GPX",
    "aircraftinfo.downloadKml": "Download KML",
    "aircraftinfo.notFound": "Aircraft info not found (adsbdb.com)",
    "aircraftinfo.photoAlt": "Aircraft photo",
    "aircraftinfo.noPhoto": "No photo found (Planespotters.net)",
    "aircraftinfo.photoCredit": "Photo: {photographer} (Planespotters.net)",
    "aircraftinfo.ownDataSection": "This receiver's data",
    "aircraftinfo.noOwnData": "No observations from this receiver yet",
    "aircraftinfo.groundSpeed": "Ground speed",
    "aircraftinfo.verticalRate": "Vertical rate",
    "aircraftinfo.bearing": "Bearing",
    "aircraftinfo.noLiveData": "Not currently received from readsb",
    "aircraftinfo.squawk": "Squawk",
    "aircraftinfo.lastPosition": "Last position",
    "aircraftinfo.secondsAgoSuffix": " s ago",
    "aircraftinfo.baroAltitude": "Baro altitude",
    "aircraftinfo.geomAltitude": "Geometric altitude",
    "aircraftinfo.iasTasLabel": "Airspeed (IAS/TAS)",
    "aircraftinfo.mach": "Mach",
    "aircraftinfo.trackMagHeading": "Track / Mag heading",
    "aircraftinfo.roll": "Roll",
    "aircraftinfo.verticalRateBaroGeom": "Vertical rate (baro/geom)",
    "aircraftinfo.category": "Category",
    "aircraftinfo.fmsSection": "FMS selected",
    "aircraftinfo.selectedAltitude": "Selected altitude",
    "aircraftinfo.selectedHeading": "Selected heading",
    "aircraftinfo.accuracySection": "Accuracy",
    "aircraftinfo.windTempSection": "Wind & temp",
    "aircraftinfo.windDirSpeed": "Wind dir/speed",
    "aircraftinfo.ownDataFetchFailed": "Failed to fetch this receiver's data",
    "aircraftinfo.noOwnDataFound": "No observations from this receiver",
    "aircraftinfo.liveDisconnected": "Live connection disconnected",
    "aircraftinfo.liveError": "Live connection error",

    "nationality.country.IT": "Italy",
    "nationality.country.ES": "Spain",
    "nationality.country.FR": "France",
    "nationality.country.DE": "Germany",
    "nationality.country.GB": "United Kingdom",
    "nationality.country.NL": "Netherlands",
    "nationality.country.AF": "Afghanistan",
    "nationality.country.KR": "South Korea",
    "nationality.country.MY": "Malaysia",
    "nationality.country.PH": "Philippines",
    "nationality.country.SG": "Singapore",
    "nationality.country.CN": "China",
    "nationality.country.AU": "Australia",
    "nationality.country.IN": "India",
    "nationality.country.JP": "Japan",
    "nationality.country.TH": "Thailand",
    "nationality.country.VN": "Vietnam",
    "nationality.country.TW": "Taiwan",
    "nationality.country.ID": "Indonesia",
    "nationality.country.US": "United States",
    "nationality.country.CA": "Canada",
    "nationality.country.NZ": "New Zealand",

    "nav.flags": "Flag Collection",
    "nav.badges": "Badges",
    "nav.archive": "Aircraft Archive",
    "nav.searchPlaceholder": "Search ICAO / callsign",
    "flags.pageTitle": "Flag Collection - ADS-B Analytics",
    "flags.heading": "Flag Collection",
    "flags.description":
      "Every aircraft ever observed, grouped by country as inferred from its ICAO 24-bit " +
      "address (a simple block table covering the major aviation nations -- not every " +
      "country is covered).",
    "flags.empty": "No aircraft with an inferable nationality yet.",
    "flags.aircraftCount": "{count} aircraft",
    "flags.firstSeen": "First seen: {date}",
    "flags.fetchFailed": "Failed to fetch nationality data.",

    "badges.pageTitle": "Badges - ADS-B Analytics",
    "badges.heading": "Badges",
    "badges.description":
      "Achievements computed automatically from your observation history. Recomputed on " +
      "every visit -- no earned-on date is recorded anywhere.",
    "badges.fetchFailed": "Failed to fetch badge data.",
    "badges.progress": "Current: {value}",
    "badges.first_contact.name": "First Contact",
    "badges.first_contact.description": "Observed your very first aircraft",
    "badges.aircraft_100.name": "Century Club",
    "badges.aircraft_100.description": "Observed 100 distinct aircraft",
    "badges.aircraft_500.name": "500 Club",
    "badges.aircraft_500.description": "Observed 500 distinct aircraft",
    "badges.aircraft_1000.name": "Thousand Club",
    "badges.aircraft_1000.description": "Observed 1,000 distinct aircraft",
    "badges.types_10.name": "Type Spotter (10)",
    "badges.types_10.description": "Identified 10 distinct aircraft types",
    "badges.types_50.name": "Type Spotter (50)",
    "badges.types_50.description": "Identified 50 distinct aircraft types",
    "badges.types_100.name": "Type Master",
    "badges.types_100.description": "Identified 100 distinct aircraft types",
    "badges.far_catch.name": "Long Reach",
    "badges.far_catch.description": "Received an aircraft 300km or farther away",
    "badges.frequent_flyer.name": "Frequent Flyer",
    "badges.frequent_flyer.description": "Observed the same aircraft 50+ times in total",
    "badges.callsign_collector.name": "Callsign Collector",
    "badges.callsign_collector.description": "Recorded 5+ different callsigns for one aircraft",
    "badges.favorite_collector.name": "Favorites Collector",
    "badges.favorite_collector.description": "Favorited 5 or more aircraft",
    "badges.veteran_month.name": "One Month In",
    "badges.veteran_month.description": "30 days of data collected",
    "badges.veteran_year.name": "One Year In",
    "badges.veteran_year.description": "365 days of data collected",
    "badges.busy_sky.name": "Busy Skies",
    "badges.busy_sky.description": "Received 20+ aircraft at once",

    "archive.pageTitle": "Aircraft Archive - ADS-B Analytics",
    "archive.filterGroupLabel": "Search & sort",
    "archive.searchPlaceholder": "ICAO / callsign",
    "archive.sort.lastSeen": "Last seen",
    "archive.sort.firstSeen": "First seen",
    "archive.sort.daysObserved": "Days observed",
    "archive.sort.totalPasses": "Total passes",
    "archive.sort.icao": "ICAO",
    "archive.col.icao": "ICAO",
    "archive.col.firstSeen": "First seen",
    "archive.col.lastSeen": "Last seen",
    "archive.prev": "Previous",
    "archive.next": "Next",
    "archive.pageInfo": "{from}-{to} of {total}",
  },
};

export function t(key, vars) {
  const lang = getLanguage();
  let template = DICT[lang]?.[key] ?? DICT[DEFAULT_LANGUAGE][key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      template = template.replaceAll(`{${name}}`, String(value));
    }
  }
  return template;
}

// Walks data-i18n*-tagged elements under `root` and applies the current
// language -- called once, early, in every page's main() (mirrors
// renderVersion(config)'s existing "called identically in every
// entrypoint" convention). Also updates <html lang> for accessibility.
export function applyStaticTranslations(root = document) {
  document.documentElement.lang = getLanguage();
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-aria-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAriaLabel));
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
  });
}
