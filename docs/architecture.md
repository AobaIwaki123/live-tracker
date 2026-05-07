# アーキテクチャ図 — idol-live-tracker

## 1. 全体像（スクレイピング ＆ Web フロントエンド）

本システムは、情報収集を行う **CLI バッチ層** と、収集した情報を表示する **Web フロントエンド層** の 2 つで構成されます。

```mermaid
flowchart LR
    subgraph BatchLayer["CLI バッチ層 (Python)"]
        A1[analyze コマンド\n設定自動生成]
        S1[scrape コマンド\n情報収集]
        N1[Notion/Discord\n同期・通知]
        A1 -->|設定| S1
        S1 -->|保存| DB[(SQLite: events.db)]
        S1 -->|同期| N1
    end

    subgraph WebLayer["Web フロントエンド層"]
        API[FastAPI\nREST API]
        UI[React SPA\n(Vite/TanStack/shadcn)]
        DB -->|JSON提供| API
        API -->|Fetch| UI
        UI -->|閲覧| User((ユーザー))
    end
```

---

## 2. Navigation タイプ判定フロー（analyze フェーズ）

```mermaid
flowchart TD
    START([base_url 受取]) --> FETCH[Playwright でページ取得\nフル HTML + XHR/Fetch ネットワークキャプチャ]
    FETCH --> SNIPPET[BeautifulSoup で\nイベント要素スニペット抽出\n出現回数順・大型コンテナ除外]

    SNIPPET --> TURN1[Turn 1\nHTML先頭20000字 + スニペット + ネットワークログ\n→ AI 初期設定生成]

    TURN1 --> CHECK{完全性チェック\n_check_completeness}
    CHECK -->|不足フィールドあり| FOLLOWUP[フォローアップターン\n不足フィールドを指摘して補完要求\n最大 2 回]
    FOLLOWUP --> CHECK
    CHECK -->|全フィールド揃った| VALIDATE

    VALIDATE[バリデーション\n実 URL をフェッチして event_list\nセレクタで要素数を確認]
    VALIDATE -->|1件以上| YAML_OUT
    VALIDATE -->|0件| VFEEDBACK[バリデーションフォローアップ\n実ページ HTML スニペットを渡して再修正\n最大 2 回]
    VFEEDBACK --> VALIDATE

    YAML_OUT([YAML 設定ファイルへ書き戻し])
```

詳細な設計・工夫点は [analyze-loop-design.md](./analyze-loop-design.md) を参照。

---

## 3. Navigation タイプ別 URL/リクエスト生成（scrape フェーズ）

```mermaid
flowchart LR
    CONFIG[artists.yaml\nnavigation.type] --> UG[URLGenerator]

    UG -->|single_page| URL1["[base_url]"]
    UG -->|query_param| URL2["[base_url?d=2026-05-01,\n base_url?d=2026-06-01, ...]"]
    UG -->|path_segment| URL3["[base_url/2026/05,\n base_url/2026/06, ...]"]
    UG -->|pagination_links| URL4["[base_url]\n→ next リンクを追跡"]
    UG -->|api_endpoint| REQ["[POST /api/schedule/get\n {start:..., end:...} × N ヶ月]"]

    URL1 & URL2 & URL3 & URL4 --> HTML_SCRAPER[HTML スクレイパー\nCSSセレクタで抽出]
    REQ --> API_CLIENT[API クライアント\nJSON レスポンス解釈]

    HTML_SCRAPER --> EVENT[LiveEvent list]
    API_CLIENT --> EVENT
```

---

## 4. シーケンス図 — analyze コマンド（3 フェーズ自己修正ループ）

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py analyze
    participant Playwright
    participant Site as アーティスト公式サイト
    participant BS4 as BeautifulSoup
    participant AI as ChatSession (Claude/Gemini)
    participant Fetcher as Scrapling Fetcher
    participant Config as artists.yaml

    User->>CLI: python main.py analyze --artist X
    CLI->>Playwright: capture_page(base_url)
    Playwright->>Site: ブラウザ起動・networkidle 待機
    Site-->>Playwright: フル HTML + XHR ログ
    Playwright-->>CLI: (full_html, network_logs)

    CLI->>BS4: _extract_event_snippets(full_html)
    Note over BS4: クラス名キーワードで要素抽出<br/>出現回数順ソート・大型コンテナ除外
    BS4-->>CLI: event_snippets

    CLI->>AI: chat_session.send(HTML先頭20000字 + snippets + logs)
    Note over AI: Phase 1: 初期 SiteConfig 生成
    AI-->>CLI: SiteConfig (JSON)

    loop Phase 2: 完全性チェック (最大 2 回)
        CLI->>CLI: _check_completeness(config)
        alt 不足フィールドあり
            CLI->>AI: chat_session.send("X が不足しています")
            AI-->>CLI: 補完した SiteConfig (JSON)
        end
    end

    loop Phase 3: バリデーション (最大 2 回)
        CLI->>Fetcher: fetch(_build_validation_url(config))
        Fetcher->>Site: HTTP GET
        Site-->>Fetcher: HTML
        Fetcher-->>CLI: page
        CLI->>CLI: page.css(event_list_selector)
        alt 0 件
            CLI->>BS4: _extract_event_snippets(page.html)
            BS4-->>CLI: val_snippets
            CLI->>AI: chat_session.send("0件でした + val_snippets")
            AI-->>CLI: 修正した SiteConfig (JSON)
        end
    end

    CLI->>Config: write_site_config(yaml_path, name, config)
    CLI->>User: 完了メッセージ
```

---

## 5. シーケンス図 — scrape コマンド

```mermaid
sequenceDiagram
    actor User
    participant CLI as main.py scrape
    participant UG as URLGenerator
    participant Scraper as GenericScraper
    participant Site as アーティスト公式サイト
    participant Notion as NotionClient
    participant DB as Notion Database

    User->>CLI: python main.py scrape [--artist X] [--dry-run]

    loop 各アーティスト
        CLI->>UG: generate_targets(artist_config)
        UG-->>CLI: list[ScrapeTarget]

        loop 各ターゲット（月ごと）
            CLI->>Scraper: scrape_target(target)
            Scraper->>Site: HTTP / API Request
            Site-->>Scraper: HTML / JSON
            Scraper-->>CLI: list[LiveEvent]
        end

        alt --dry-run
            CLI->>User: ターミナル出力
        else 通常実行
            CLI->>Notion: append_events(events)
            Notion->>DB: 既存キー取得
            DB-->>Notion: existing_keys
            Notion->>Notion: 差分フィルタリング
            Notion->>DB: 新規イベント書き込み
            Notion-->>CLI: 書き込み件数
        end
    end

    CLI->>User: 実行サマリ出力
```

---

## 6. ディレクトリ構造

```
idol-live-tracker/
├── docs/
│   ├── requirements.md           ← 要件定義書
│   ├── basic-design.md           ← 基本設計書
│   ├── architecture.md           ← 本ファイル（アーキテクチャ図）
│   └── discord-summary-format.md ← 週次サマリーフォーマット仕様
├── src/
│   ├── ai/
│   │   ├── __init__.py
│   │   └── provider.py           ← AIProvider ABC + ClaudeProvider + GeminiProvider
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── site_analyzer.py      ← AI サイト解析（HTML + ネットワークキャプチャ）
│   │   └── config_writer.py      ← 解析結果を YAML へ書き戻す
│   ├── enricher/
│   │   ├── __init__.py
│   │   └── enricher.py           ← チケットサイト検索 + AI 補完（opt-in）
│   ├── models/
│   │   ├── __init__.py
│   │   └── event.py              ← LiveEvent dataclass
│   ├── notion/
│   │   ├── __init__.py
│   │   └── client.py             ← NotionClient（差分 upsert）
│   ├── notifier/
│   │   ├── __init__.py
│   │   ├── discord.py            ← イベント単位 Discord 通知
│   │   └── weekly_summary.py     ← 週次サマリー送信
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py               ← BaseScraper (ABC)
│   │   ├── url_generator.py      ← navigation config → URL/リクエスト生成
│   │   └── generic.py            ← GenericScraper（全 Navigation タイプ対応）
│   ├── store/
│   │   ├── __init__.py
│   │   └── local_store.py        ← SQLite イベントキャッシュ
│   ├── config.py                 ← load_config(), ArtistConfig, AppConfig
│   └── main.py                   ← CLI エントリーポイント（analyze/scrape/enrich/summary）
├── config/
│   └── artists.yaml              ← base_url のみ記載して analyze で自動補完
├── data/                         ← events.db（.gitignore 対象）
├── logs/                         ← 実行ログ（.gitignore 対象）
├── .env.example
└── pyproject.toml
```

---

## 7. 技術スタック

| レイヤー | 採用技術 | 理由 |
|---|---|---|
| サイト解析 | Claude API (claude-sonnet-4-6) | HTML + ネットワークログから構造を推論 |
| スクレイピング（静的） | Scrapling Fetcher | 軽量・TLS フィンガープリント偽装 |
| スクレイピング（動的） | Scrapling DynamicFetcher | Playwright ベース、JS レンダリング対応 |
| Notion 連携 | notion-client (公式 SDK) | 公式サポート、型安全 |
| 設定管理 | PyYAML + python-dotenv | 設定とシークレットを分離 |
| 実行言語 | Python 3.10+ | Scrapling / match 文の最低要件 |
