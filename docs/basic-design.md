# 基本設計書 — idol-live-tracker

## 1. システム構成

```
idol-live-tracker/
├── docs/
├── src/
│   ├── ai/
│   │   ├── __init__.py
│   │   └── provider.py         # AI Provider 抽象クライアント（Claude / Gemini 切り替え）
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── site_analyzer.py    # ネットワークキャプチャ + AI サイト構造解析
│   │   └── config_writer.py    # 解析結果を YAML へ書き戻す
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py             # 抽象基底クラス
│   │   ├── url_generator.py    # navigation 設定 → URL リスト生成
│   │   └── generic.py          # 汎用スクレイパー（設定ドリブン）
│   ├── notion/
│   │   ├── __init__.py
│   │   └── client.py           # Notion API ラッパー
│   ├── notifier/
│   │   ├── __init__.py
│   │   ├── discord.py          # Discord Webhook 通知（新規・更新イベント）
│   │   └── weekly_summary.py   # Discord 週次サマリー送信
│   ├── enricher/
│   │   ├── __init__.py
│   │   └── enricher.py         # AI エンリッチメント（opt-in）
│   ├── models/
│   │   ├── __init__.py
│   │   └── event.py            # LiveEvent dataclass
│   ├── store/
│   │   ├── __init__.py
│   │   └── local_store.py      # ローカル SQLite イベントキャッシュ
│   └── main.py                 # CLI エントリーポイント
├── config/
│   └── artists.yaml
├── data/
│   └── events.db               # ローカル SQLite（.gitignore 対象）
├── logs/                        # 定期実行ログ
│   └── .gitkeep
├── .env.example
└── pyproject.toml
```

---

## 2. YAML 設定ファイル設計（config/artists.yaml）

```yaml
artists:
  - name: avam-fc                          # アーティスト識別子
    base_url: https://avam-fc.com/schedule # 人間が指定する唯一の入力

    # ---- 以下は analyze コマンドが自動生成 ----
    analyzed_at: "2026-05-04"             # 解析日（再解析は --force 時のみ）

    fetch:
      dynamic: true                        # JS レンダリング要否

    navigation:
      type: api_endpoint                   # single_page | query_param | path_segment
                                           # | pagination_links | api_endpoint
      endpoint: /api/schedule/get          # api_endpoint 専用
      method: POST
      body_template:                       # {month_start}/{month_end} は実行時に展開
        start: "{month_start}"
        end: "{month_end}"
      range_months: 3                      # 何ヶ月先まで収集するか（全タイプ共通）

    response:                              # api_endpoint タイプ時のレスポンス解釈
      format: json_array                   # json_array | json_object_with_array
      array_path: ""                       # ルートが配列なら空文字
      mapping:
        id: id
        title: title
        date: reception_date
        date_format: "%Y-%m-%d"

    detail:                                # 詳細ページから追加情報を取得する場合
      enabled: true
      url_pattern: "{base_url}/detail/{id}?d={date}"
      selectors:
        venue: ".venue-name"
        start_time: ".start-time"
        ticket_url: "a.ticket::attr(href)"
        other_artists: ".performers"
        poster_url: "img.poster::attr(src)"

  - name: artist-b
    base_url: https://example-b.com/live

    analyzed_at: "2026-05-04"

    fetch:
      dynamic: false

    navigation:
      type: query_param                    # クエリパラメータ型
      param: d
      value_format: "%Y-%m-%d"            # strftime 形式
      granularity: monthly                 # monthly | weekly
      range_months: 3

    selectors:                             # HTML スクレイピング型共通セレクタ
      event_list: ".schedule-item"
      title: ".title"
      date: ".date"
      venue: ".venue"
      ticket_url: "a.ticket::attr(href)"

  - name: artist-c
    base_url: https://example-c.com/schedule

    analyzed_at: "2026-05-04"

    fetch:
      dynamic: false

    navigation:
      type: path_segment                   # パスセグメント型
      pattern: "{base_url}/{year}/{month:02d}"
      range_months: 3

    selectors:
      event_list: "li.event"
      title: "h2.event-title"
      date: "time::attr(datetime)"
      venue: ".location"
      ticket_url: ""
```

---

## 3. Navigation タイプ別 URL 生成ロジック

### URLGenerator（src/scrapers/url_generator.py）

```python
def generate_targets(config: ArtistConfig) -> list[ScrapeTarget]:
    nav = config.navigation
    months = [today + relativedelta(months=i) for i in range(nav.range_months)]

    match nav.type:
        case "single_page":
            return [ScrapeTarget(url=config.base_url)]

        case "query_param":
            return [ScrapeTarget(
                url=f"{config.base_url}?{nav.param}={m.strftime(nav.value_format)}"
            ) for m in months]

        case "path_segment":
            return [ScrapeTarget(
                url=nav.pattern.format(base_url=config.base_url,
                                       year=m.year, month=m.month)
            ) for m in months]

        case "pagination_links":
            # 最初の URL のみ返し、GenericScraper 側で next リンクを辿る
            return [ScrapeTarget(url=config.base_url, follow_next=True)]

        case "api_endpoint":
            return [ScrapeTarget(
                api=ApiRequest(
                    url=f"{config.base_url_origin}{nav.endpoint}",
                    method=nav.method,
                    body={k: expand(v, month=m) for k, v in nav.body_template.items()}
                )
            ) for m in months]
```

---

## 4. モジュール設計

### 4-0. AIProvider（src/ai/provider.py）

```
AIProvider (ABC)
  └─ complete(system: str, user: str) -> str

ClaudeProvider(AIProvider)
  └─ model: claude-sonnet-4-6

GeminiProvider(AIProvider)
  └─ model: gemini-2.0-flash

get_ai_provider() -> AIProvider
  # 環境変数 AI_PROVIDER (claude|gemini|auto) に応じてインスタンスを返す
  # auto の場合: ANTHROPIC_API_KEY → Claude、GEMINI_API_KEY → Gemini の順に検出
```

**環境変数設定例（.env）:**
```
AI_PROVIDER=claude      # claude | gemini | auto（省略時 auto）
ANTHROPIC_API_KEY=sk-ant-xxxxx
GEMINI_API_KEY=AIzaxxx  # どちらか一方でも動作する
```

### 4-1. SiteAnalyzer（src/analyzer/site_analyzer.py）

```
capture_page(base_url) -> (html, list[NetworkLog])
  └─ DynamicFetcher でページ取得 + XHR/Fetch キャプチャ

analyze_site(base_url, html, network_logs) -> SiteConfig
  ├─ _build_prompt(html, network_log, base_url) -> str
  └─ get_ai_provider().complete(ANALYSIS_SYSTEM_PROMPT, prompt) -> JSON
```

**AI へ渡す解析プロンプトの要点:**
1. ページ HTML（先頭 20,000 字）
2. キャプチャした XHR/Fetch リクエスト一覧（URL・メソッド・ボディ）
3. 現在の URL
4. 出力フォーマット（JSON Schema）の厳密な指定
5. 優先順位: `api_endpoint` > `query_param` > `path_segment` > `pagination_links` > `single_page`

**AI 出力の JSON Schema（抜粋）:**
```json
{
  "fetch": { "dynamic": true },
  "navigation": {
    "type": "api_endpoint",
    "endpoint": "/api/schedule/get",
    "method": "POST",
    "body_template": { "start": "{month_start}", "end": "{month_end}" },
    "range_months": 3
  },
  "response": {
    "format": "json_array",
    "mapping": { "title": "title", "date": "reception_date", "date_format": "%Y-%m-%d" }
  },
  "detail": { "enabled": false }
}
```

### 4-2. GenericScraper（src/scrapers/generic.py）

```
GenericScraper
  ├─ scrape(artist_config) -> list[LiveEvent]
  │    ├─ URLGenerator.generate_targets(config) -> list[ScrapeTarget]
  │    └─ for target in targets:
  │         ├─ [api_endpoint] → _call_api(target) → _map_api_response()
  │         ├─ [html types]   → _fetch_html(target) → _parse_html()
  │         └─ [pagination]   → _follow_next_links()
  └─ detail_scraper: DetailScraper（任意）
```

### 4-3. LocalStore（src/store/local_store.py）

```
LocalStore
  ├─ upsert(event: LiveEvent) -> None          # 新規作成 or 差分フィールド上書き
  ├─ get_upcoming(days: int) -> list[LiveEvent] # 今日から N 日以内のイベントを返す
  └─ get_all() -> list[LiveEvent]
```

scrape コマンドが常に書き込む。Notion は任意の追加出力先として扱う。

### 4-3b. NotionClient（src/notion/client.py）

```
NotionClient
  ├─ fetch_all() -> dict[tuple[str,str,date], NotionRecord]  # (artist,title,date) → レコード
  ├─ create(event: LiveEvent) -> str                          # page_id を返す
  ├─ update(page_id: str, diff: dict[str, Any]) -> None      # 差分フィールドのみ上書き
  └─ upsert_events(events: list[LiveEvent])
       -> tuple[list[LiveEvent], list[tuple[LiveEvent, dict]]]  # (新規, 更新済み)
```

スクレイプデータを正とし、差分フィールドのみ上書きする。通知トリガーとなる新規・更新リストを返す。

### 4-4c. WeeklySummaryNotifier（src/notifier/weekly_summary.py）

```
WeeklySummaryNotifier
  └─ send(events: list[LiveEvent]) -> None
       # events を日付・週でグルーピングし
       # docs/discord-summary-format.md のフォーマットで Discord に送信
       # 2000 文字超の場合は週単位で分割して複数メッセージ送信
```

### 4-5. CLI（src/main.py）

| コマンド | 動作 |
|---|---|
| `python main.py analyze [--artist NAME] [--force]` | base_url を解析して YAML を更新 |
| `python main.py scrape [--artist NAME] [--dry-run]` | スクレイピング → SQLite 保存 → Notion 転記（任意）→ Discord 通知 |
| `python main.py enrich [--artist NAME]` | 欠損フィールドを AI で補完（opt-in） |
| `python main.py summary` | 直近 2 週間のサマリーを Discord へ即時送信（cron からも呼ぶ） |

---

## 5. データモデル

### LiveEvent（src/models/event.py）

| フィールド | 型 | 取得元 |
|---|---|---|
| title | str | Tier 1: メインページ |
| artist | str | config |
| date | date \| None | Tier 1: メインページ |
| start_time | str | Tier 1〜2 |
| venue | str | Tier 1〜2 |
| prefecture | str | Tier 2〜3（会場から導出） |
| ticket_url | str | Tier 1〜2 |
| ticket_price | str | Tier 3: チケットサイト |
| other_artists | str | Tier 2〜3 |
| poster_url | str | Tier 2: 詳細ページ |
| source_url | str | config + Tier 1 |
| fetch_status | str | `完全取得` / `一部未取得` / `タイトル・日付のみ` |

重複判定キー: `(artist, title, date)`

---

## 6. エラーハンドリング方針

| 状況 | 対応 |
|---|---|
| AI 解析で不明な構造 | `type: unknown` として YAML に書き、ログに警告。手動編集を促す |
| スクレイピング失敗 | ログ出力してそのアーティストをスキップ |
| セレクタで要素未検出 | フィールドを空文字として処理を継続 |
| Notion API エラー | ログ出力してリトライなしでスキップ |
| 日付パース失敗 | `date=None` として登録 |
